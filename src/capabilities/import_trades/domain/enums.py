"""Domain enums for the import_trades capability."""

from __future__ import annotations

from enum import Enum


class TradeTable(str, Enum):
    """Target PostgreSQL table for each B3 file type.

    Attributes
    ----------
    MOVIMENTACAO : str
        B3 movement/trade history table.
    NEGOCIACAO : str
        B3 negotiation/execution table.
    POSICAO_ACOES : str
        B3 year-end equity position table.
    POSICAO_EMPRESTIMOS : str
        B3 year-end lending position table.
    PROVENTOS_RECEBIDOS : str
        B3 received dividends and income table.
    REEMBOLSO_EMPRESTIMOS : str
        B3 lending reimbursement table.
    BONIFICACAO_ACOES : str
        B3 bonus share table (enriched via scraper).
    """

    MOVIMENTACAO = "b3_movimentacao"
    NEGOCIACAO = "b3_negociacao"
    POSICAO_ACOES = "b3_posicao_acoes"
    POSICAO_EMPRESTIMOS = "b3_posicao_emprestimos"
    PROVENTOS_RECEBIDOS = "b3_proventos_recebidos"
    REEMBOLSO_EMPRESTIMOS = "b3_reembolso_emprestimos"
    BONIFICACAO_ACOES = "b3_bonificacao_acoes"
