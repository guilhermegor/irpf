"""Use cases for the declaration_rv capability."""

from __future__ import annotations

from decimal import ROUND_DOWN, Decimal

from src.capabilities.declaration_rv.domain.dto import DeclarationReportDTO
from src.capabilities.declaration_rv.domain.entities import (
    DeclarationData,
    PortfolioPosition,
    TaxEvent,
)
from src.capabilities.declaration_rv.domain.ports import DeclarationRepository


class GenerateDeclaration:
    """Build IRPF declaration report text from PostgreSQL data.

    Parameters
    ----------
    cls_repo : DeclarationRepository
        Data-fetching port.
    dict_cfg : dict
        Declaration config from ``inputs.yaml`` (the ``declaration_rv`` key).
    """

    def __init__(self, cls_repo: DeclarationRepository, dict_cfg: dict) -> None:
        """Initialise with a data repository and declaration configuration.

        Parameters
        ----------
        cls_repo : DeclarationRepository
            Data-fetching port.
        dict_cfg : dict
            Declaration config from ``inputs.yaml``.
        """
        self._cls_repo = cls_repo
        self._dict_cfg = dict_cfg

    def execute(self, int_year: int) -> DeclarationReportDTO:
        """Generate the declaration report for the given base year.

        Parameters
        ----------
        int_year : int
            IRPF base year (e.g. 2024).

        Returns
        -------
        DeclarationReportDTO
            Dict with ``int_year`` and ``str_report``.
        """
        cls_data = self._cls_repo.fetch(int_year)
        str_report = _build_report(cls_data, self._dict_cfg)
        return DeclarationReportDTO(int_year=int_year, str_report=str_report)


def _fmt_decimal(decimal_val: Decimal, int_places: int = 2) -> str:
    """Format a Decimal as a Brazilian currency string (comma as decimal separator).

    Parameters
    ----------
    decimal_val : Decimal
        Value to format.
    int_places : int
        Number of decimal places (truncated, not rounded).

    Returns
    -------
    str
        Formatted string with comma separator, e.g. ``"1234,56"``.
    """
    str_quantize = "0." + "0" * int_places
    return str(decimal_val.quantize(Decimal(str_quantize), rounding=ROUND_DOWN)).replace(".", ",")


def _build_report(cls_data: DeclarationData, dict_cfg: dict) -> str:
    """Assemble all declaration sections into a single string.

    Parameters
    ----------
    cls_data : DeclarationData
        Aggregated data for the declaration year.
    dict_cfg : dict
        Full ``declaration_rv`` config block from ``inputs.yaml``.

    Returns
    -------
    str
        Multi-section declaration text.
    """
    int_places = dict_cfg.get("decimal_places", 2)
    dict_contrib = dict_cfg["contributor"]

    str_out = "**************** 0. CONTRIBUTOR DATA ****************\n\n"
    str_out += f"Full Name: {dict_contrib['full_name']}\n"
    str_out += f"CPF: {dict_contrib['cpf']}\n\n"

    str_out += "**************** 1. ASSETS AND RIGHTS ****************\n\n"
    for cls_pos in cls_data.list_positions:
        str_out += _section_position(cls_pos, cls_data.int_year, dict_cfg, int_places)

    str_out += "\n\n**************** 2. DIVIDENDS — EXEMPT NON-TAXABLE INCOME ****************\n\n"
    for cls_evt in cls_data.list_exempt_dividends:
        str_out += _section_income_event(
            cls_evt, dict_cfg["exempt_non_taxable_income"], int_places
        )

    str_out += "\n\n**************** 3. JCP — TAXABLE INCOME ****************\n\n"
    for cls_evt in cls_data.list_taxable_jcp:
        str_out += _section_income_event(cls_evt, dict_cfg["taxable_income_jcp"], int_places)

    str_out += (
        "\n\n**************** 4. FRACTION AUCTION — EXEMPT NON-TAXABLE INCOME"
        " ****************\n\n"
    )
    for cls_evt in cls_data.list_fraction_auction:
        str_out += _section_fraction_auction(
            cls_evt, dict_cfg["exempt_non_taxable_fraction_auction"], int_places
        )

    str_out += (
        "\n\n**************** 5. BONUS SHARES — EXEMPT NON-TAXABLE INCOME ****************\n\n"
    )
    for cls_evt in cls_data.list_bonus_shares:
        str_out += _section_income_event(
            cls_evt, dict_cfg["exempt_non_taxable_bonus_shares"], int_places
        )

    str_out += "\n\n**************** 6. MONETARY UPDATE INCOME — TAXABLE ****************\n\n"
    for cls_evt in cls_data.list_taxable_monetary_update:
        str_out += _section_income_event(
            cls_evt, dict_cfg["taxable_income_monetary_update"], int_places
        )

    str_out += "\n\n**************** 7. STOCK LENDING INCOME — TAXABLE ****************\n\n"
    str_out += _section_scalar(
        cls_data.decimal_lending_income, dict_cfg["taxable_income_stock_lending"], int_places
    )

    str_out += "\n\n**************** 8. LENDING REIMBURSEMENT — EXEMPT ****************\n\n"
    str_out += _section_reimbursement(
        cls_data.decimal_reimbursement,
        dict_cfg["exempt_non_taxable_reimbursement"],
        int_places,
    )

    return str_out


def _section_position(
    cls_pos: PortfolioPosition,
    int_year: int,
    dict_cfg: dict,
    int_places: int,
) -> str:
    """Render one assets-and-rights entry for a portfolio position.

    Parameters
    ----------
    cls_pos : PortfolioPosition
        Portfolio position entity.
    int_year : int
        IRPF base year (used to label the year-end balance line).
    dict_cfg : dict
        Full ``declaration_rv`` config block.
    int_places : int
        Decimal places for formatted amounts.

    Returns
    -------
    str
        Formatted section text.
    """
    dict_c = dict_cfg["assets_and_rights"]
    str_out = f"\\\\ TICKER: {cls_pos.str_ticker}\n"
    str_out += f"{dict_c['group']['key']}{dict_c['group']['value']}\n"
    str_out += f"{dict_c['code']['key']}{dict_c['code']['value']}\n"
    str_out += f"{dict_c['location']['key']}{dict_c['location']['value']}\n"
    str_out += f"{dict_c['cnpj']['key']}{cls_pos.str_cnpj}\n"
    str_out += (
        f"{dict_c['description']['key']}"
        + dict_c["description"]["value"].format(
            cls_pos.str_ticker,
            cls_pos.int_quantity,
            _fmt_decimal(cls_pos.decimal_avg_buy_price, int_places),
        )
        + "\n"
    )
    str_out += f"{dict_c['traded_on_exchange']['key']}{dict_c['traded_on_exchange']['value']}\n"
    str_out += f"{dict_c['trading_code']['key']}{cls_pos.str_ticker}\n"
    str_out += (
        f"{dict_c['year_end_balance']['key'].format(f'31/12/{int_year}')}"
        f"{_fmt_decimal(cls_pos.decimal_financial_position, int_places)}\n\n"
    )
    return str_out


def _section_income_event(cls_evt: TaxEvent, dict_c: dict, int_places: int) -> str:
    """Render one income event (dividend, JCP, bonus shares, etc.).

    Parameters
    ----------
    cls_evt : TaxEvent
        Income event entity.
    dict_c : dict
        Config sub-dict for this income category.
    int_places : int
        Decimal places for formatted amounts.

    Returns
    -------
    str
        Formatted section text.
    """
    str_out = f"\\\\ TICKER: {cls_evt.str_ticker}\n"
    str_out += f"{dict_c['income_type']['key']}{dict_c['income_type']['value']}\n"
    str_out += f"{dict_c['payer_cnpj']['key']}{cls_evt.str_cnpj}\n"
    str_out += f"{dict_c['payer_name']['key']}{cls_evt.str_company_name}\n"
    str_out += f"{dict_c['amount']['key']}{_fmt_decimal(cls_evt.decimal_amount, int_places)}\n\n"
    return str_out


def _section_fraction_auction(cls_evt: TaxEvent, dict_c: dict, int_places: int) -> str:
    """Render a fraction-auction income event (adds a description line).

    Parameters
    ----------
    cls_evt : TaxEvent
        Fraction-auction income event entity.
    dict_c : dict
        Config sub-dict for the fraction-auction category.
    int_places : int
        Decimal places for formatted amounts.

    Returns
    -------
    str
        Formatted section text.
    """
    str_out = _section_income_event(cls_evt, dict_c, int_places)
    str_desc = (
        f"{dict_c['description']['key']}"
        f"{dict_c['description']['value'].format(cls_evt.str_ticker.upper())}\n"
    )
    str_out = str_out.replace(
        f"{dict_c['amount']['key']}", str_desc + f"{dict_c['amount']['key']}"
    )
    return str_out


def _section_scalar(decimal_val: Decimal, dict_c: dict, int_places: int) -> str:
    """Render a scalar income section (single amount, fixed payer).

    Parameters
    ----------
    decimal_val : Decimal
        Total income amount.
    dict_c : dict
        Config sub-dict for this income category.
    int_places : int
        Decimal places for formatted amounts.

    Returns
    -------
    str
        Formatted section text.
    """
    str_out = f"{dict_c['income_type']['key']}{dict_c['income_type']['value']}\n"
    str_out += f"{dict_c['payer_cnpj']['key']}{dict_c['payer_cnpj']['value']}\n"
    str_out += f"{dict_c['payer_name']['key']}{dict_c['payer_name']['value']}\n"
    str_out += f"{dict_c['amount']['key']}{_fmt_decimal(decimal_val, int_places)}\n\n"
    return str_out


def _section_reimbursement(decimal_val: Decimal, dict_c: dict, int_places: int) -> str:
    """Render the stock-lending reimbursement section (adds a description line).

    Parameters
    ----------
    decimal_val : Decimal
        Total reimbursement amount.
    dict_c : dict
        Config sub-dict for the reimbursement category.
    int_places : int
        Decimal places for formatted amounts.

    Returns
    -------
    str
        Formatted section text.
    """
    str_out = _section_scalar(decimal_val, dict_c, int_places)
    str_desc = f"{dict_c['description']['key']}{dict_c['description']['value']}\n"
    str_out = str_out.replace(
        f"{dict_c['amount']['key']}", str_desc + f"{dict_c['amount']['key']}"
    )
    return str_out
