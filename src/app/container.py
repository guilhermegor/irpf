"""Composition root: wire infrastructure to application factories."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import os
from pathlib import Path
from typing import Callable

from stpstone.utils.calendars.calendar_br import DatesBRAnbima

from src.capabilities.declaration_rv.application.use_cases import GenerateDeclaration
from src.capabilities.declaration_rv.domain.dto import DeclarationReportDTO
from src.capabilities.declaration_rv.infrastructure.repositories import (
    PostgresDeclarationRepository,
)
from src.capabilities.import_trades.application.use_cases import ImportTrades
from src.capabilities.import_trades.domain.dto import ImportResultDTO
from src.capabilities.import_trades.domain.entities import TradeImportJob
from src.capabilities.import_trades.infrastructure.repositories import (
    PostgresTradeImportRepository,
)
from src.chassis.db_schema.infrastructure.base import DatabaseSession
import src.chassis.db_schema.infrastructure.models  # noqa: F401 — registers view models with Base
from src.config.startup import TAXPAYER, YAML_INPUTS


_cls_dates = DatesBRAnbima()


@dataclass(frozen=True)
class AppContainer:
    """Pre-wired application entry points.

    Attributes
    ----------
    fn_import_trades : Callable[[list[TradeImportJob]], list[ImportResultDTO]]
        Run all B3 Excel import jobs.
    fn_generate_declaration : Callable[[], DeclarationReportDTO]
        Generate the IRPF declaration report for the configured base year.
    """

    fn_import_trades: Callable[[list[TradeImportJob]], list[ImportResultDTO]]
    fn_generate_declaration: Callable[[], DeclarationReportDTO]


def build_jobs(str_taxpayer: str = TAXPAYER) -> list[TradeImportJob]:
    """Build the ordered list of B3 import jobs from config.

    Parameters
    ----------
    str_taxpayer : str
        Taxpayer identifier prefix used in B3 file names (from ``TAXPAYER`` env var).

    Returns
    -------
    list[TradeImportJob]
        One job per B3 table, in insertion order.
    """
    int_year_ref = _cls_dates.year_number(_cls_dates.curr_date())
    dt_date_ref: date = _cls_dates.build_date(int_year_ref, 1, 1)
    int_year_prev = int_year_ref - 1

    return [
        TradeImportJob(
            file_name_like=f"{str_taxpayer}-movimentacao-{int_year_ref}*.xlsx",
            dict_dtypes={
                "entrada_saida": str,
                "data_pregao": "date",
                "movimentacao": str,
                "produto": str,
                "instituicao": str,
                "quantidade": float,
                "preco_unitario": float,
                "valor_operacao": float,
            },
            table_name="b3_movimentacao",
            dt_date_ref=dt_date_ref,
        ),
        TradeImportJob(
            file_name_like=f"{str_taxpayer}-negociacao-{int_year_ref}*.xlsx",
            dict_dtypes={
                "data_negocio": "date",
                "tipo_movimentacao": str,
                "mercado": str,
                "prazo_vencimento": "date",
                "instituicao": str,
                "ticker": str,
                "quantidade": int,
                "preco": float,
                "valor": float,
            },
            table_name="b3_negociacao",
            dt_date_ref=dt_date_ref,
        ),
        TradeImportJob(
            file_name_like=f"{str_taxpayer}-relatorio-consolidado-anual-{int_year_prev}.xlsx",
            dict_dtypes={
                "produto": str,
                "instituicao": str,
                "conta": int,
                "codigo_negociacao": str,
                "cnpj": str,
                "codigo_isin": str,
                "tipo": str,
                "escriturador": str,
                "quantidade": int,
                "quantidade_disp": int,
                "quantidade_indisp": int,
                "motivo": str,
                "preco_fechamento": float,
                "valor_atualizado": float,
                "data_pregao": "date",
            },
            table_name="b3_posicao_acoes",
            dt_date_ref=_cls_dates.build_date(int_year_prev, 12, 31),
        ),
        TradeImportJob(
            file_name_like=f"{str_taxpayer}-relatorio-consolidado-anual-{int_year_prev}.xlsx",
            dict_dtypes={
                "produto": str,
                "instituicao": str,
                "natureza": str,
                "num_contrato": str,
                "modalidade": str,
                "opa": str,
                "liquidacao_antecipada": str,
                "taxa": float,
                "comissao": float,
                "data_registro": "date",
                "data_vencimento": "date",
                "quantidade": int,
                "preco_fechamento": float,
                "valor_atualizado": float,
                "data_pregao": "date",
            },
            table_name="b3_posicao_emprestimos",
            dt_date_ref=_cls_dates.build_date(int_year_prev, 12, 31),
        ),
        TradeImportJob(
            file_name_like=f"{str_taxpayer}-relatorio-consolidado-anual-{int_year_prev}.xlsx",
            dict_dtypes={
                "produto": str,
                "tipo_evento": str,
                "valor_liquido": float,
                "data_pregao": "date",
            },
            table_name="b3_proventos_recebidos",
            dt_date_ref=_cls_dates.build_date(int_year_prev, 12, 31),
        ),
        TradeImportJob(
            file_name_like=f"{str_taxpayer}-relatorio-consolidado-anual-{int_year_prev}.xlsx",
            dict_dtypes={
                "produto": str,
                "tipo_evento": str,
                "valor_liquido": float,
                "data_pregao": "date",
            },
            table_name="b3_reembolso_emprestimos",
            dt_date_ref=_cls_dates.build_date(int_year_prev, 12, 31),
        ),
        TradeImportJob(
            file_name_like=f"{str_taxpayer}-movimentacao-{int_year_ref}*.xlsx",
            dict_dtypes={
                "entrada_saida": str,
                "data_pregao": "date",
                "movimentacao": str,
                "produto": str,
                "instituicao": str,
                "quantidade": float,
                "preco_unitario": float,
                "valor_operacao": float,
            },
            table_name="b3_bonificacao_acoes",
            dt_date_ref=dt_date_ref,
        ),
    ]


def build() -> AppContainer:
    """Instantiate infrastructure and bind to application factories.

    Credentials are read from environment variables (loaded via ``.env``).

    Returns
    -------
    AppContainer
        Fully wired container.
    """
    str_host = os.environ["DB_HOST"]
    int_port = int(os.environ["DB_PORT"])
    str_dbname = os.environ["DB_NAME"]
    str_user = os.environ["DB_USER"]
    str_password = os.environ["DB_PASSWORD"]

    str_data_path = str(
        Path(YAML_INPUTS["import_trades"]["data_path"]).expanduser()
        / str(_cls_dates.curr_date())
    )

    cls_import_repo = PostgresTradeImportRepository(
        str_data_path=str_data_path,
        str_host=str_host,
        int_port=int_port,
        str_dbname=str_dbname,
        str_user=str_user,
        str_password=str_password,
        str_schema=TAXPAYER,
    )
    str_dsn = (
        f"postgresql+psycopg://{str_user}:{str_password}"
        f"@{str_host}:{int_port}/{str_dbname}"
        f"?options=-c%20search_path%3D{TAXPAYER}"
    )
    cls_db_session = DatabaseSession(str_dsn)
    cls_decl_repo = PostgresDeclarationRepository(
        cls_session=cls_db_session.session(),
    )

    int_year_decl = (
        _cls_dates.year_number(_cls_dates.curr_date())
        - YAML_INPUTS["declaration_rv"]["base_year_offset"]
    )
    dict_decl_cfg = YAML_INPUTS["declaration_rv"]

    return AppContainer(
        fn_import_trades=lambda list_jobs: ImportTrades(cls_import_repo).execute(list_jobs),
        fn_generate_declaration=lambda: GenerateDeclaration(cls_decl_repo, dict_decl_cfg).execute(
            int_year_decl
        ),
    )
