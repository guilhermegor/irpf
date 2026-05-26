"""Infrastructure repository for the declaration_rv capability."""

from __future__ import annotations

from decimal import Decimal
import re

from sqlalchemy import func, select, union
from sqlalchemy.orm import Session

from src.capabilities.declaration_rv.domain.entities import (
    DeclarationData,
    PortfolioPosition,
    TaxEvent,
)
from src.chassis.db_schema.infrastructure.models import (
    PosicaoAcoesModel,
    PosicaoEmprestimosModel,
    VwBonificacoesModel,
    VwPmPatrModel,
    VwProventosModel,
)


# CNPJs for tickers whose CNPJ is absent from b3_posicao_acoes (delisted or missing in B3 report).
_DELISTED_CNPJ: dict[str, str] = {
    "CPFE3":  "02.429.144/0001-93",  # CPFL Energia S.A.
    "BBSE3":  "17.344.597/0001-94",  # BB Seguridade Participações S.A.
    "KLBN11": "89.637.490/0001-45",  # Klabin S.A.
    "SANB11": "90.400.888/0001-42",  # Banco Santander (Brasil) S.A.
    "SAPR11": "76.484.013/0001-45",  # Companhia de Saneamento do Paraná
    "TAEE11": "07.859.971/0001-30",  # Transmissora Aliança de Energia Elétrica S.A.
}

_DIVIDENDO = "Dividendo"
_DIVIDENDO_TRANSFERIDO = "Dividendo - Transferido"
_JCP = "Juros Sobre Capital Próprio"
_JCP_TRANSFERIDO = "Juros Sobre Capital Próprio - Transferido"
_RENDIMENTO = "Rendimento"
_LEILAO_FRACAO = "Leilão de Fração"
_EMPRESTIMO = "Empréstimo"
_REEMBOLSO = "Reembolso"


class PostgresDeclarationRepository:
    """Fetch IRPF declaration data from PostgreSQL views using SQLAlchemy ORM.

    Parameters
    ----------
    cls_session : Session
        SQLAlchemy session scoped to the taxpayer schema.
    """

    def __init__(self, cls_session: Session) -> None:
        """Initialise with an injected SQLAlchemy session.

        Parameters
        ----------
        cls_session : Session
            SQLAlchemy session bound to the taxpayer schema.
        """
        self._cls_session = cls_session

    def fetch(self, int_year: int) -> DeclarationData:
        """Query all views and return a DeclarationData entity.

        Parameters
        ----------
        int_year : int
            IRPF base year to query.

        Returns
        -------
        DeclarationData
            Aggregated positions and income events for ``int_year``.
        """
        list_tickers = self._active_tickers(int_year)
        dict_portfolio = {row.instrumento: row for row in self._portfolio()}

        list_positions: list[PortfolioPosition] = []
        for str_ticker in list_tickers:
            row = dict_portfolio.get(str_ticker)
            if row is None:
                continue
            list_positions.append(
                PortfolioPosition(
                    str_ticker=str_ticker,
                    str_cnpj=_resolve_cnpj(str_ticker, row.cnpj),
                    str_company_name=row.nome_compania or "",
                    int_quantity=int(row.qtd_lado or 0),
                    decimal_avg_buy_price=Decimal(str(row.preco_medio_compra or 0)),
                    decimal_financial_position=Decimal(str(row.posicao_fin or 0)),
                )
            )

        dict_dividends = _index_proventos(
            self._proventos(int_year, [_DIVIDENDO, _DIVIDENDO_TRANSFERIDO])
        )
        dict_jcp = _index_proventos(self._proventos(int_year, [_JCP, _JCP_TRANSFERIDO]))
        dict_monetary = _index_proventos(self._proventos(int_year, [_RENDIMENTO]))
        dict_fraction = _index_proventos(self._proventos(int_year, [_LEILAO_FRACAO]))
        dict_bonus = {row.ticker: row for row in self._bonificacoes(int_year)}

        def _evt_proventos(
            dict_rows: dict[str, VwProventosModel], str_ticker: str
        ) -> TaxEvent | None:
            """Build a TaxEvent from a proventos index entry, or None if absent.

            Parameters
            ----------
            dict_rows : dict[str, VwProventosModel]
                Ticker-indexed proventos query result.
            str_ticker : str
                Ticker to look up.

            Returns
            -------
            TaxEvent | None
                Income event entity, or ``None`` when the ticker has no matching event.
            """
            row = dict_rows.get(str_ticker)
            if row is None:
                return None
            return TaxEvent(
                str_ticker=str_ticker,
                str_cnpj=_resolve_cnpj(str_ticker, row.cnpj),
                str_company_name=row.nome_compania or "",
                str_event_type=row.movimentacao,
                decimal_amount=Decimal(str(row.valor_operacao or 0)),
            )

        def _evt_bonus(str_ticker: str) -> TaxEvent | None:
            """Build a bonus-share TaxEvent for a ticker, or None if absent.

            Parameters
            ----------
            str_ticker : str
                Ticker to look up.

            Returns
            -------
            TaxEvent | None
                Bonus share event entity, or ``None`` when the ticker has no bonus.
            """
            row = dict_bonus.get(str_ticker)
            if row is None:
                return None
            return TaxEvent(
                str_ticker=str_ticker,
                str_cnpj=_resolve_cnpj(str_ticker, row.cnpj),
                str_company_name=row.nome_compania or "",
                str_event_type="Bonificação em Ativos",
                decimal_amount=Decimal(str(row.valor_operacao or 0)),
            )

        return DeclarationData(
            int_year=int_year,
            list_positions=list_positions,
            list_exempt_dividends=[
                e for t in list_tickers if (e := _evt_proventos(dict_dividends, t))
            ],
            list_taxable_jcp=[
                e for t in list_tickers if (e := _evt_proventos(dict_jcp, t))
            ],
            list_taxable_monetary_update=[
                e for t in list_tickers if (e := _evt_proventos(dict_monetary, t))
            ],
            decimal_lending_income=self._scalar_proventos(int_year, _EMPRESTIMO),
            decimal_reimbursement=self._scalar_proventos(int_year, _REEMBOLSO),
            list_fraction_auction=[
                e for t in list_tickers if (e := _evt_proventos(dict_fraction, t))
            ],
            list_bonus_shares=[e for t in list_tickers if (e := _evt_bonus(t))],
        )

    def _active_tickers(self, int_year: int) -> list[str]:
        """Return all tickers active in a given year.

        Parameters
        ----------
        int_year : int
            Base year to filter by.

        Returns
        -------
        list[str]
            Sorted, deduplicated list of ticker strings.
        """
        stmt_acoes = select(PosicaoAcoesModel.codigo_negociacao.label("ticker")).where(
            func.extract("year", PosicaoAcoesModel.data_pregao) == int_year,
            PosicaoAcoesModel.codigo_negociacao.isnot(None),
        )
        stmt_emprestimos = select(
            func.split_part(PosicaoEmprestimosModel.produto, " - ", 1).label("ticker")
        ).where(
            func.extract("year", PosicaoEmprestimosModel.data_pregao) == int_year,
            PosicaoEmprestimosModel.produto.isnot(None),
        )
        stmt = union(stmt_acoes, stmt_emprestimos)
        list_rows = self._cls_session.execute(stmt).fetchall()
        return sorted({row.ticker for row in list_rows if row.ticker})

    def _portfolio(self) -> list[VwPmPatrModel]:
        """Return all rows from the average-price portfolio view.

        Returns
        -------
        list[VwPmPatrModel]
            All active positions with average price and financial value.
        """
        return list(self._cls_session.execute(select(VwPmPatrModel)).scalars().all())

    def _proventos(
        self, int_year: int, list_movimentacoes: list[str]
    ) -> list[VwProventosModel]:
        """Return income events of the given types for a base year.

        Parameters
        ----------
        int_year : int
            Base year to filter by.
        list_movimentacoes : list[str]
            Movement types to include.

        Returns
        -------
        list[VwProventosModel]
            Matching income event rows.
        """
        return list(
            self._cls_session.execute(
                select(VwProventosModel).where(
                    VwProventosModel.ano_base == int_year,
                    VwProventosModel.movimentacao.in_(list_movimentacoes),
                )
            )
            .scalars()
            .all()
        )

    def _scalar_proventos(self, int_year: int, str_movimentacao: str) -> Decimal:
        """Return the sum of valor_operacao for a single movement type.

        Parameters
        ----------
        int_year : int
            Base year to filter by.
        str_movimentacao : str
            Exact movement type string.

        Returns
        -------
        Decimal
            Aggregated value, or ``Decimal("0")`` when no rows match.
        """
        result = self._cls_session.execute(
            select(func.sum(VwProventosModel.valor_operacao)).where(
                VwProventosModel.ano_base == int_year,
                VwProventosModel.movimentacao == str_movimentacao,
            )
        ).scalar()
        return Decimal(str(result)) if result is not None else Decimal("0")

    def _bonificacoes(self, int_year: int) -> list[VwBonificacoesModel]:
        """Return bonus share events for a base year.

        Parameters
        ----------
        int_year : int
            Base year to filter by.

        Returns
        -------
        list[VwBonificacoesModel]
            Matching bonus share rows.
        """
        return list(
            self._cls_session.execute(
                select(VwBonificacoesModel).where(
                    VwBonificacoesModel.ano_base == int_year
                )
            )
            .scalars()
            .all()
        )


def _clean_cnpj(str_cnpj: str) -> str:
    """Normalise a raw CNPJ string to the formatted XX.XXX.XXX/XXXX-XX form.

    Parameters
    ----------
    str_cnpj : str
        Raw CNPJ — may be a bare integer string ("191"), a float string
        ("191.0" from Excel numeric coercion), or already formatted.

    Returns
    -------
    str
        Formatted CNPJ, or ``""`` when the input is empty.
    """
    if str_cnpj.endswith(".0"):
        str_cnpj = str_cnpj[:-2]
    str_digits = re.sub(r"\D", "", str_cnpj)
    if not str_digits:
        return ""
    str_padded = str_digits.zfill(14)
    return (
        f"{str_padded[:2]}.{str_padded[2:5]}.{str_padded[5:8]}"
        f"/{str_padded[8:12]}-{str_padded[12:]}"
    )


def _resolve_cnpj(str_ticker: str, str_raw: str | None) -> str:
    """Return a formatted CNPJ, falling back to the delisted-ticker registry.

    Parameters
    ----------
    str_ticker : str
        B3 ticker symbol (used for the fallback lookup).
    str_raw : str | None
        Raw CNPJ from the database, or ``None`` when absent.

    Returns
    -------
    str
        Formatted CNPJ string, or ``""`` when unknown.
    """
    return _clean_cnpj(str_raw or "") or _DELISTED_CNPJ.get(str_ticker, "")


def _index_proventos(
    list_rows: list[VwProventosModel],
) -> dict[str, VwProventosModel]:
    """Index a proventos result list by ticker.

    Parameters
    ----------
    list_rows : list[VwProventosModel]
        Raw query result.

    Returns
    -------
    dict[str, VwProventosModel]
        Ticker to row mapping (view already aggregates per ticker/year/movimentacao).
    """
    return {row.ticker: row for row in list_rows}
