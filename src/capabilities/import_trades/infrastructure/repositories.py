"""Infrastructure repository for the import_trades capability."""

from __future__ import annotations

from datetime import date
from numbers import Number
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
from stpstone.utils.calendars.calendar_br import DatesBRAnbima
from stpstone.utils.connections.databases.sql.postgresql_db import PostgreSQLDB
from stpstone.utils.parsers.folders import DirFilesManagement

from src.capabilities.import_trades.domain.dto import ImportResultDTO
from src.capabilities.import_trades.domain.entities import TradeImportJob
from src.capabilities.import_trades.infrastructure.bonus_shares_scraper import fetch_bonus_shares


_cls_dates = DatesBRAnbima()
_cls_dir = DirFilesManagement()

_ANNUAL_REPORT_SHEET_MAP = {
    "b3_posicao_acoes": "Posição - Ações",
    "b3_posicao_emprestimos": "Posição - Empréstimos",
    "b3_proventos_recebidos": "Proventos Recebidos",
    "b3_reembolso_emprestimos": "Reembolsos de Empréstimo",
}


class PostgresTradeImportRepository:
    """Reads B3 Excel files and inserts their rows into PostgreSQL.

    Parameters
    ----------
    str_data_path : str
        Directory containing B3 Excel files (``~`` expanded cross-platform).
    str_host : str
        PostgreSQL host.
    int_port : int
        PostgreSQL port.
    str_dbname : str
        PostgreSQL database name.
    str_user : str
        PostgreSQL username.
    str_password : str
        PostgreSQL password.
    """

    def __init__(
        self,
        str_data_path: str,
        str_host: str,
        int_port: int,
        str_dbname: str,
        str_user: str,
        str_password: str,
        str_schema: str = "public",
    ) -> None:
        """Initialise with database credentials and data directory.

        Parameters
        ----------
        str_data_path : str
            Directory containing B3 Excel files.
        str_host : str
            PostgreSQL host.
        int_port : int
            PostgreSQL port.
        str_dbname : str
            PostgreSQL database name.
        str_user : str
            PostgreSQL username.
        str_password : str
            PostgreSQL password.
        str_schema : str
            PostgreSQL schema (taxpayer identifier, set via ``TAXPAYER`` env var).
        """
        self._path_data = Path(str_data_path).expanduser()
        self._str_host = str_host
        self._int_port = int_port
        self._str_dbname = str_dbname
        self._str_user = str_user
        self._str_password = str_password
        self._str_schema = str_schema

    def _db(self) -> PostgreSQLDB:
        """Create a new PostgreSQLDB connection with schema-scoped search_path."""
        return PostgreSQLDB(
            dbname=self._str_dbname,
            user=self._str_user,
            password=self._str_password,
            host=self._str_host,
            port=self._int_port,
            str_schema=self._str_schema,
        )

    def _fetch_excel(
        self,
        str_file_name_like: str,
        dict_dtypes: dict[str, Any],
        str_table_name: str,
        dt_date_ref: date | None,
    ) -> pd.DataFrame:
        """Read and normalise one B3 Excel file into a DataFrame ready for DB insertion.

        Parameters
        ----------
        str_file_name_like : str
            Glob-style pattern used to find the most-recently saved matching file.
        dict_dtypes : dict[str, Any]
            Mapping of column name → target dtype (or ``"date"`` for date columns).
        str_table_name : str
            Target DB table name; used to select the correct sheet for annual reports.
        dt_date_ref : date | None
            Reference date injected into annual-report rows that have no date column.

        Raises
        ------
        FileNotFoundError
            If no file matching ``str_file_name_like`` is found in ``self._path_data``.
        ValueError
            If ``str_table_name`` is unknown for an annual consolidated report file.
        """
        str_path_file = _cls_dir.choose_last_saved_file_w_rule(
            str(self._path_data), str_file_name_like
        )
        if not str_path_file:
            raise FileNotFoundError(
                f"No file matching '{str_file_name_like}' found in '{self._path_data}'. "
                "Download the B3 report and place it in that directory."
            )
        list_cols_dt = [k for k, v in dict_dtypes.items() if v == "date"]
        dict_load_dtypes = {k: v if str(v) != "date" else str for k, v in dict_dtypes.items()}

        bool_annual = "relatorio-consolidado-anual" in str_file_name_like
        if bool_annual:
            str_sheet: int | str = _ANNUAL_REPORT_SHEET_MAP.get(str_table_name, "")
            if not str_sheet:
                raise ValueError(f"Unknown table for annual report: {str_table_name}")
        else:
            str_sheet = 0

        try:
            df_ = pd.read_excel(
                str_path_file,
                skiprows=0,
                names=list(dict_dtypes.keys()),
                sheet_name=str_sheet,
                thousands=".",
                decimal=",",
            )
        except ValueError:
            df_ = pd.read_excel(
                str_path_file,
                skiprows=0,
                names=list(dict_dtypes.keys())[:-1],
                sheet_name=str_sheet,
                thousands=".",
                decimal=",",
                engine="openpyxl",
            )

        df_ = _drop_sparse_rows(df_)

        if bool_annual and dt_date_ref is not None:
            df_["data_pregao"] = dt_date_ref.strftime("%d/%m/%Y")

        for str_col, dtype in dict_load_dtypes.items():
            if issubclass(type(dtype), type) and issubclass(dtype, Number):
                df_[str_col] = [0.0 if x == "-" else x for x in df_[str_col]]
            elif dtype is str:
                df_[str_col] = [str(x).strip() for x in df_[str_col]]
            elif dtype in (float, int):
                df_[str_col] = [0 if x == "-" else x for x in df_[str_col]]
            df_[str_col] = df_[str_col].astype(dtype)

        for str_col in list_cols_dt:
            df_[str_col] = ["01/01/2100" if x == "-" else x for x in df_[str_col]]
            df_[str_col] = [
                _cls_dates.str_date_to_date(d, "DD/MM/YYYY") for d in df_[str_col]
            ]

        if "cnpj" in df_.columns:
            df_["cnpj"] = df_["cnpj"].astype(str).str.replace(r"\.0$", "", regex=True)

        df_ = _add_pk(df_, str_table_name)
        return df_

    def _fetch_bonus_shares(
        self,
        str_file_name_like: str,
        dict_dtypes: dict[str, Any],
        dt_date_ref: date | None,
    ) -> pd.DataFrame:
        """Enrich bonus-share movements with per-share base values from StatusInvest.

        Parameters
        ----------
        str_file_name_like : str
            Glob-style pattern to locate the movements Excel file.
        dict_dtypes : dict[str, Any]
            Column → dtype mapping passed through to ``_fetch_excel``.
        dt_date_ref : date | None
            Reference date injected when the source file has no date column.
        """
        df_mov = self._fetch_excel(
            str_file_name_like, dict_dtypes, "b3_movimentacao", dt_date_ref
        )
        list_original_cols = list(df_mov.columns)
        df_mov["ano_ref"] = [_cls_dates.year_number(d) for d in df_mov["data_pregao"]]
        df_mov = df_mov[df_mov["movimentacao"] == "Bonificação em Ativos"]
        df_mov["TICKER"] = [str(x.split("-")[0]).strip() for x in df_mov["produto"]]

        list_ser: list[dict] = []
        for str_ticker in df_mov["TICKER"].unique():
            df_bonif = fetch_bonus_shares(str_ticker)
            list_ser.extend(df_bonif.to_dict(orient="records"))

        df_bonif_all = pd.DataFrame(list_ser)
        df_mov = df_mov.merge(
            df_bonif_all, how="left", on=["TICKER", "ano_ref"], suffixes=("", "_")
        )
        df_mov["valor_operacao"] = (
            df_mov["quantidade"].astype(float) * df_mov["valor_base"].astype(float)
        )
        list_keep = [c for c in list_original_cols if c != "preco_unitario"] + ["valor_base"]
        df_mov = df_mov[list_keep].rename(columns={"valor_base": "preco_unitario"})
        return df_mov

    def import_job(self, cls_job: TradeImportJob) -> ImportResultDTO:
        """Fetch the Excel file and insert rows into PostgreSQL.

        Parameters
        ----------
        cls_job : TradeImportJob
            Describes the source file and target table.

        Returns
        -------
        ImportResultDTO
            Rows processed and status.
        """
        if cls_job.table_name == "b3_bonificacao_acoes":
            df_ = self._fetch_bonus_shares(
                cls_job.file_name_like, cls_job.dict_dtypes, cls_job.dt_date_ref
            )
        else:
            df_ = self._fetch_excel(
                cls_job.file_name_like,
                cls_job.dict_dtypes,
                cls_job.table_name,
                cls_job.dt_date_ref,
            )

        list_records = df_.to_dict("records")
        self._db().insert(list_records, cls_job.table_name, bool_insert_or_ignore=True)
        return ImportResultDTO(
            table_name=cls_job.table_name,
            rows_processed=len(list_records),
            status="ok",
        )


def _drop_sparse_rows(df_: pd.DataFrame, int_max_missing: int = 3) -> pd.DataFrame:
    """Drop rows that have more than int_max_missing missing values.

    Parameters
    ----------
    df_ : pd.DataFrame
        Input DataFrame.
    int_max_missing : int
        Maximum allowed missing values per row before it's dropped.

    Returns
    -------
    pd.DataFrame
        Filtered DataFrame with sparse rows removed.
    """
    bool_missing = df_.isna() | (df_ == "-") | (df_ == "") | (df_ == " ")
    int_threshold = min(int(0.5 * len(df_.columns)), int_max_missing)
    return df_[bool_missing.sum(axis=1) <= int_threshold].copy()


def _add_pk(df_: pd.DataFrame, str_table_name: str) -> pd.DataFrame:
    """Add a composite primary key column to the DataFrame.

    Parameters
    ----------
    df_ : pd.DataFrame
        Input DataFrame.
    str_table_name : str
        Target table name, used to determine which key columns to concatenate.

    Returns
    -------
    pd.DataFrame
        DataFrame with the primary key column added.
    """
    if str_table_name in ("b3_movimentacao", "b3_bonificacao_acoes"):
        df_["pk_movimentacao"] = (
            df_["entrada_saida"].astype(str)
            + df_["data_pregao"].apply(
                lambda d: d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else str(d)
            )
            + df_["movimentacao"].astype(str)
            + df_["produto"].astype(str)
            + df_["quantidade"].astype(str).str.replace(".", ",", regex=False)
            + df_["preco_unitario"].astype(str).str.replace(".", ",", regex=False)
            + df_["valor_operacao"].astype(str).str.replace(".", ",", regex=False)
        )
    elif str_table_name == "b3_negociacao":
        df_["pk_negociacao"] = (
            df_["data_negocio"].apply(
                lambda d: d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else str(d)
            )
            + df_["tipo_movimentacao"].astype(str)
            + df_["ticker"].astype(str)
            + df_["quantidade"].astype(str).str.replace(".", ",", regex=False)
            + df_["preco"].astype(str).str.replace(".", ",", regex=False)
        )
    elif str_table_name in (
        "b3_posicao_acoes",
        "b3_posicao_emprestimos",
        "b3_proventos_recebidos",
        "b3_reembolso_emprestimos",
    ):
        df_["id"] = [str(uuid4()) for _ in range(len(df_))]
    return df_
