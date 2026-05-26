"""Domain enums for the declaration_rv capability."""

from __future__ import annotations

from enum import Enum


class IncomeCategory(str, Enum):
    """Category of income event for IRPF declaration purposes."""

    EXEMPT_DIVIDEND = "exempt_dividend"
    TAXABLE_JCP = "taxable_jcp"
    TAXABLE_MONETARY_UPDATE = "taxable_monetary_update"
    TAXABLE_LENDING = "taxable_lending"
    EXEMPT_REIMBURSEMENT = "exempt_reimbursement"
    EXEMPT_FRACTION_AUCTION = "exempt_fraction_auction"
    EXEMPT_BONUS_SHARES = "exempt_bonus_shares"
