"""Unit tests for GenerateDeclaration use case."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

from src.capabilities.declaration_rv.application.use_cases import GenerateDeclaration
from src.capabilities.declaration_rv.domain.entities import (
    DeclarationData,
    PortfolioPosition,
    TaxEvent,
)


_MOCK_CFG = {
    "decimal_places": 2,
    "contributor": {
        "full_name": "Test User",
        "full_name_key": "Nome Completo Contribuinte: ",
        "cpf": "000.000.000-00",
        "cpf_key": "CPF Contribuinte: ",
    },
    "assets_and_rights": {
        "group": {"key": "Group: ", "value": "03"},
        "code": {"key": "Code: ", "value": "01"},
        "location": {"key": "Location: ", "value": "105"},
        "cnpj": {"key": "CNPJ: "},
        "description": {"key": "Desc: ", "value": "{} {} {} shares"},
        "traded_on_exchange": {"key": "Exchange: ", "value": "Yes"},
        "trading_code": {"key": "Code: "},
        "year_end_balance": {"key": "Balance {}: "},
    },
    "exempt_non_taxable_income": {
        "income_type": {"key": "Type: ", "value": "09"},
        "payer_cnpj": {"key": "CNPJ: "},
        "payer_name": {"key": "Name: "},
        "amount": {"key": "Amount: "},
    },
    "taxable_income_jcp": {
        "income_type": {"key": "Type: ", "value": "10"},
        "payer_cnpj": {"key": "CNPJ: "},
        "payer_name": {"key": "Name: "},
        "amount": {"key": "Amount: "},
    },
    "taxable_income_monetary_update": {
        "income_type": {"key": "Type: ", "value": "06"},
        "payer_cnpj": {"key": "CNPJ: "},
        "payer_name": {"key": "Name: "},
        "amount": {"key": "Amount: "},
    },
    "taxable_income_stock_lending": {
        "income_type": {"key": "Type: ", "value": "06"},
        "payer_cnpj": {"key": "CNPJ: ", "value": "09346601000125"},
        "payer_name": {"key": "Name: ", "value": "B3 S.A."},
        "amount": {"key": "Amount: "},
    },
    "exempt_non_taxable_reimbursement": {
        "income_type": {"key": "Type: ", "value": "99"},
        "payer_cnpj": {"key": "CNPJ: ", "value": "09346601000125"},
        "payer_name": {"key": "Name: ", "value": "B3 S.A."},
        "description": {"key": "Desc: ", "value": "REIMBURSEMENT"},
        "amount": {"key": "Amount: "},
    },
    "exempt_non_taxable_fraction_auction": {
        "income_type": {"key": "Type: ", "value": "99"},
        "payer_cnpj": {"key": "CNPJ: "},
        "payer_name": {"key": "Name: "},
        "description": {"key": "Desc: ", "value": "AUCTION - {}"},
        "amount": {"key": "Amount: "},
    },
    "exempt_non_taxable_bonus_shares": {
        "income_type": {"key": "Type: ", "value": "18"},
        "payer_cnpj": {"key": "CNPJ: "},
        "payer_name": {"key": "Name: "},
        "amount": {"key": "Amount: "},
    },
}


def test_generate_declaration_contains_contributor_name() -> None:
    """Report text must include the contributor's full name and a known ticker."""
    cls_repo = MagicMock()
    cls_repo.fetch.return_value = DeclarationData(
        int_year=2024,
        list_positions=[
            PortfolioPosition(
                str_ticker="PETR4",
                str_cnpj="33000167000101",
                str_company_name="PETROBRAS",
                int_quantity=100,
                decimal_avg_buy_price=Decimal("30.00"),
                decimal_financial_position=Decimal("3000.00"),
            )
        ],
        decimal_lending_income=Decimal("50.00"),
        decimal_reimbursement=Decimal("10.00"),
    )
    cls_use_case = GenerateDeclaration(cls_repo, _MOCK_CFG)
    dict_result = cls_use_case.execute(2024)
    assert "Test User" in dict_result["str_report"]
    assert "PETR4" in dict_result["str_report"]


def test_generate_declaration_year_is_returned() -> None:
    """execute() must echo the requested year in the returned DTO."""
    cls_repo = MagicMock()
    cls_repo.fetch.return_value = DeclarationData(int_year=2023)
    cls_use_case = GenerateDeclaration(cls_repo, _MOCK_CFG)
    dict_result = cls_use_case.execute(2023)
    assert dict_result["int_year"] == 2023


def test_generate_declaration_income_events_appear_in_report() -> None:
    """Income events (dividend, JCP) must appear in the corresponding sections."""
    cls_repo = MagicMock()
    cls_repo.fetch.return_value = DeclarationData(
        int_year=2024,
        list_exempt_dividends=[
            TaxEvent(
                str_ticker="ITUB4",
                str_cnpj="60872504000123",
                str_company_name="ITAU UNIBANCO",
                str_event_type="Dividendo",
                decimal_amount=Decimal("150.00"),
            )
        ],
        list_taxable_jcp=[
            TaxEvent(
                str_ticker="BBAS3",
                str_cnpj="00000000000191",
                str_company_name="BANCO DO BRASIL",
                str_event_type="Juros Sobre Capital Próprio",
                decimal_amount=Decimal("75.50"),
            )
        ],
    )
    cls_use_case = GenerateDeclaration(cls_repo, _MOCK_CFG)
    dict_result = cls_use_case.execute(2024)
    assert "ITUB4" in dict_result["str_report"]
    assert "BBAS3" in dict_result["str_report"]
    assert "150,00" in dict_result["str_report"]
    assert "75,50" in dict_result["str_report"]
