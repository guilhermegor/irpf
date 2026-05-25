"""Infrastructure repository for the declaration_rv capability."""

from __future__ import annotations

from decimal import Decimal

import pandas as pd
from stpstone.utils.connections.databases.sql.postgresql_db import PostgreSQLDB

from src.capabilities.declaration_rv.domain.entities import (
    DeclarationData,
    PortfolioPosition,
    TaxEvent,
)


class PostgresDeclarationRepository:
    """Fetch IRPF declaration data from PostgreSQL views.

    Parameters
    ----------
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
    dict_cfg : dict
        The ``db`` key from ``inputs.yaml`` (column names and SQL queries).
    """

    def __init__(
        self,
        str_host: str,
        int_port: int,
        str_dbname: str,
        str_user: str,
        str_password: str,
        dict_cfg: dict,
        str_schema: str = "public",
    ) -> None:
        """Initialise with database credentials and column/query configuration.

        Parameters
        ----------
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
        dict_cfg : dict
            The ``db`` key from ``inputs.yaml``.
        str_schema : str
            PostgreSQL schema (taxpayer identifier, set via ``TAXPAYER`` env var).
        """
        self._str_host = str_host
        self._int_port = int_port
        self._str_dbname = str_dbname
        self._str_user = str_user
        self._str_password = str_password
        self._dict_cfg = dict_cfg
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

    def _read(self, str_query: str) -> pd.DataFrame:
        """Execute a SQL query and return the result as a DataFrame.

        Parameters
        ----------
        str_query : str
            SQL query string.

        Returns
        -------
        pd.DataFrame
            Query result.
        """
        return self._db().read(str_query)

    def fetch(self, int_year: int) -> DeclarationData:
        """Query all PostgreSQL views and return a DeclarationData entity.

        Parameters
        ----------
        int_year : int
            IRPF base year to query.

        Returns
        -------
        DeclarationData
            Aggregated positions and income events for ``int_year``.
        """
        dict_q = self._dict_cfg
        str_col_op = dict_q["col_operation_value"]
        str_col_ticker = dict_q["col_ticker"]
        str_col_inst = dict_q["col_instrument"]
        str_col_cnpj = dict_q["col_cnpj"]
        str_col_company = dict_q["col_company_name"]
        str_col_qty = dict_q["col_position_side"]
        str_col_avg = dict_q["col_avg_buy_price"]
        str_col_fin = dict_q["col_financial_position"]
        str_col_mov = dict_q["col_movement_type"]

        df_active = self._read(
            dict_q["query_active_tickers_base_year"].format(int_year, int_year)
        )
        df_avg_price = self._read(dict_q["query_avg_price_portfolio"])
        df_exempt_div = self._read(dict_q["query_exempt_dividends"].format(int_year))
        df_taxable_jcp = self._read(dict_q["query_taxable_jcp"].format(int_year))
        df_monetary = self._read(dict_q["query_monetary_update_income"].format(int_year))
        df_lending = self._read(dict_q["query_stock_lending_income"].format(int_year))
        df_reimbursement = self._read(dict_q["query_lending_reimbursement"].format(int_year))
        df_fraction = self._read(dict_q["query_fraction_auction"].format(int_year))
        df_bonus = self._read(dict_q["query_bonus_shares"].format(int_year))

        list_tickers = df_active[str_col_ticker].dropna().unique().tolist()

        list_positions: list[PortfolioPosition] = []
        for str_ticker in list_tickers:
            df_row = df_avg_price[df_avg_price[str_col_inst] == str_ticker]
            if df_row.empty:
                continue
            row = df_row.iloc[0]
            list_positions.append(
                PortfolioPosition(
                    str_ticker=str_ticker,
                    str_cnpj=_clean_cnpj(str(row[str_col_cnpj])),
                    str_company_name=str(row[str_col_company]),
                    int_quantity=int(row[str_col_qty]),
                    decimal_avg_buy_price=Decimal(str(row[str_col_avg])),
                    decimal_financial_position=Decimal(str(row[str_col_fin])),
                )
            )

        def _evt(df_: pd.DataFrame, str_ticker: str) -> TaxEvent | None:
            """Build a TaxEvent from the first matching row, or None if absent.

            Parameters
            ----------
            df_ : pd.DataFrame
                Query result DataFrame containing ticker and financial columns.
            str_ticker : str
                Ticker to look up.
            """
            if df_.empty or str_col_ticker not in df_.columns:
                return None
            df_row = df_[df_[str_col_ticker] == str_ticker]
            if df_row.empty:
                return None
            row = df_row.iloc[0]
            return TaxEvent(
                str_ticker=str_ticker,
                str_cnpj=_clean_cnpj(str(row[str_col_cnpj])),
                str_company_name=str(row[str_col_company]),
                str_event_type=str(row.get(str_col_mov, "")),
                decimal_amount=Decimal(str(row[str_col_op])),
            )

        list_exempt_dividends = [e for t in list_tickers if (e := _evt(df_exempt_div, t))]
        list_taxable_jcp = [e for t in list_tickers if (e := _evt(df_taxable_jcp, t))]
        list_monetary = [e for t in list_tickers if (e := _evt(df_monetary, t))]
        list_fraction = [e for t in list_tickers if (e := _evt(df_fraction, t))]
        list_bonus = [e for t in list_tickers if (e := _evt(df_bonus, t))]

        decimal_lending = (
            Decimal(str(df_lending[str_col_op].iloc[0]))
            if not df_lending.empty and pd.notna(df_lending[str_col_op].iloc[0])
            else Decimal("0")
        )
        decimal_reimbursement = (
            Decimal(str(df_reimbursement[str_col_op].iloc[0]))
            if not df_reimbursement.empty and pd.notna(df_reimbursement[str_col_op].iloc[0])
            else Decimal("0")
        )

        return DeclarationData(
            int_year=int_year,
            list_positions=list_positions,
            list_exempt_dividends=list_exempt_dividends,
            list_taxable_jcp=list_taxable_jcp,
            list_taxable_monetary_update=list_monetary,
            decimal_lending_income=decimal_lending,
            decimal_reimbursement=decimal_reimbursement,
            list_fraction_auction=list_fraction,
            list_bonus_shares=list_bonus,
        )


def _clean_cnpj(str_cnpj: str) -> str:
    """Strip trailing '.0' from CNPJ strings produced by Excel float parsing.

    Parameters
    ----------
    str_cnpj : str
        Raw CNPJ string, possibly with a trailing '.0' from float coercion.

    Returns
    -------
    str
        CNPJ string with any trailing '.0' removed.
    """
    return str_cnpj[:-2] if str_cnpj.endswith(".0") else str_cnpj
