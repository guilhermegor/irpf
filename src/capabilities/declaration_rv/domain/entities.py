"""Domain entities for the declaration_rv capability."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class PortfolioPosition:
    """Year-end position for a single ticker — used in IRPF assets-and-rights section.

    Attributes
    ----------
    str_ticker : str
        B3 ticker symbol (e.g. ``"PETR4"``).
    str_cnpj : str
        Company CNPJ formatted as a string.
    str_company_name : str
        Full legal company name.
    int_quantity : int
        Number of shares held at year end.
    decimal_avg_buy_price : Decimal
        Average cost per share (weighted by purchase quantity).
    decimal_financial_position : Decimal
        Total position value = ``int_quantity * decimal_avg_buy_price``.
    """

    str_ticker: str
    str_cnpj: str
    str_company_name: str
    int_quantity: int
    decimal_avg_buy_price: Decimal
    decimal_financial_position: Decimal


@dataclass
class TaxEvent:
    """Single taxable or exempt income event.

    Attributes
    ----------
    str_ticker : str
        B3 ticker symbol.
    str_cnpj : str
        Payer CNPJ.
    str_company_name : str
        Payer company name.
    str_event_type : str
        Event label as returned by the DB view (e.g. ``"Dividendo"``).
    decimal_amount : Decimal
        Gross amount received.
    """

    str_ticker: str
    str_cnpj: str
    str_company_name: str
    str_event_type: str
    decimal_amount: Decimal


@dataclass
class DeclarationData:
    """Aggregated data for one IRPF declaration year.

    Attributes
    ----------
    int_year : int
        IRPF base year (e.g. 2024).
    list_positions : list[PortfolioPosition]
        Year-end portfolio positions.
    list_exempt_dividends : list[TaxEvent]
        Exempt dividend income events.
    list_taxable_jcp : list[TaxEvent]
        Taxable JCP (interest on equity) income events.
    list_taxable_monetary_update : list[TaxEvent]
        Taxable monetary-update income events.
    decimal_lending_income : Decimal
        Total stock-lending income (taxable).
    decimal_reimbursement : Decimal
        Total lending-reimbursement income (exempt).
    list_fraction_auction : list[TaxEvent]
        Exempt fraction-auction income events.
    list_bonus_shares : list[TaxEvent]
        Exempt bonus-share income events.
    """

    int_year: int
    list_positions: list[PortfolioPosition] = field(default_factory=list)
    list_exempt_dividends: list[TaxEvent] = field(default_factory=list)
    list_taxable_jcp: list[TaxEvent] = field(default_factory=list)
    list_taxable_monetary_update: list[TaxEvent] = field(default_factory=list)
    decimal_lending_income: Decimal = field(default=Decimal("0"))
    decimal_reimbursement: Decimal = field(default=Decimal("0"))
    list_fraction_auction: list[TaxEvent] = field(default_factory=list)
    list_bonus_shares: list[TaxEvent] = field(default_factory=list)
