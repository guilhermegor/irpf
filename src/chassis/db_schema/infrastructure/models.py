"""SQLAlchemy ORM models for the example Record entity and B3 trade data."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, generate_uuid


class RecordModel(Base):
    """SQLAlchemy model for a generic Record entity.

    This is an example model demonstrating SQLAlchemy ORM patterns.
    Replace or extend this model based on your domain requirements.

    Attributes
    ----------
    id : str
        Primary key, auto-generated UUID.
    data : str
        JSON-serialized payload or text content.
    created_at : datetime
        Timestamp when the record was created.
    updated_at : datetime
        Timestamp when the record was last updated.
    """

    __tablename__ = "records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<RecordModel(id={self.id!r}, created_at={self.created_at})>"

    def to_dict(self) -> dict:
        """Convert model to dictionary representation.

        Returns
        -------
        dict
            Dictionary with all model fields.
        """
        return {
            "id": self.id,
            "data": self.data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class MovimentacaoModel(Base):
    """ORM model for B3 trade movement records.

    Attributes
    ----------
    pk_movimentacao : str
        Composite primary key (concatenated fields).
    entrada_saida : str, optional
        Direction: entry or exit.
    data_pregao : date, optional
        Trading date.
    movimentacao : str, optional
        Movement type description.
    produto : str, optional
        Product description (ticker + company name).
    instituicao : str, optional
        Brokerage institution name.
    quantidade : float, optional
        Trade quantity.
    preco_unitario : float, optional
        Unit price.
    valor_operacao : float, optional
        Total operation value.
    """

    __tablename__ = "b3_movimentacao"

    pk_movimentacao: Mapped[str] = mapped_column(String(600), primary_key=True)
    entrada_saida: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    data_pregao: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    movimentacao: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    produto: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    instituicao: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    quantidade: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    preco_unitario: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    valor_operacao: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)


class NegociacaoModel(Base):
    """ORM model for B3 trade negotiation records.

    Attributes
    ----------
    pk_negociacao : str
        Composite primary key (concatenated fields).
    data_negocio : date, optional
        Trade date.
    tipo_movimentacao : str, optional
        Trade type (buy/sell).
    mercado : str, optional
        Market segment.
    prazo_vencimento : date, optional
        Expiry date (derivatives).
    instituicao : str, optional
        Brokerage institution name.
    ticker : str, optional
        B3 ticker symbol.
    quantidade : int, optional
        Trade quantity.
    preco : float, optional
        Unit price.
    valor : float, optional
        Total trade value.
    """

    __tablename__ = "b3_negociacao"

    pk_negociacao: Mapped[str] = mapped_column(String(600), primary_key=True)
    data_negocio: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    tipo_movimentacao: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    mercado: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    prazo_vencimento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    instituicao: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    ticker: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    quantidade: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    preco: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    valor: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)


class PosicaoAcoesModel(Base):
    """ORM model for B3 year-end stock positions.

    Attributes
    ----------
    id : str
        Auto-generated UUID primary key.
    produto : str, optional
        Product description.
    instituicao : str, optional
        Custodian institution.
    conta : int, optional
        Account number.
    codigo_negociacao : str, optional
        B3 ticker / trading code.
    cnpj : str, optional
        Company CNPJ (tax ID).
    codigo_isin : str, optional
        ISIN code.
    tipo : str, optional
        Asset type.
    escriturador : str, optional
        Transfer agent name.
    quantidade : int, optional
        Total quantity held.
    quantidade_disp : int, optional
        Available quantity.
    quantidade_indisp : int, optional
        Unavailable quantity.
    motivo : str, optional
        Reason for unavailability.
    preco_fechamento : float, optional
        Closing price.
    valor_atualizado : float, optional
        Updated market value.
    data_pregao : date, optional
        Position reference date (year-end).
    """

    __tablename__ = "b3_posicao_acoes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    produto: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    instituicao: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    conta: Mapped[Optional[float]] = mapped_column(Numeric(18, 0), nullable=True)
    codigo_negociacao: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    cnpj: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    codigo_isin: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    tipo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    escriturador: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    quantidade: Mapped[Optional[float]] = mapped_column(Numeric(18, 0), nullable=True)
    quantidade_disp: Mapped[Optional[float]] = mapped_column(Numeric(18, 0), nullable=True)
    quantidade_indisp: Mapped[Optional[float]] = mapped_column(Numeric(18, 0), nullable=True)
    motivo: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    preco_fechamento: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    valor_atualizado: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)
    data_pregao: Mapped[Optional[date]] = mapped_column(Date, nullable=True)


class PosicaoEmprestimosModel(Base):
    """ORM model for B3 year-end lending positions.

    Attributes
    ----------
    id : str
        Auto-generated UUID primary key.
    produto : str, optional
        Product description.
    instituicao : str, optional
        Custodian institution.
    natureza : str, optional
        Lending nature (doador/tomador).
    num_contrato : str, optional
        Contract number.
    modalidade : str, optional
        Lending modality.
    opa : str, optional
        OPA flag.
    liquidacao_antecipada : str, optional
        Early settlement flag.
    taxa : float, optional
        Lending rate.
    comissao : float, optional
        Commission rate.
    data_registro : date, optional
        Contract registration date.
    data_vencimento : date, optional
        Contract expiry date.
    quantidade : int, optional
        Quantity of shares lent.
    preco_fechamento : float, optional
        Closing price.
    valor_atualizado : float, optional
        Updated market value.
    data_pregao : date, optional
        Position reference date (year-end).
    """

    __tablename__ = "b3_posicao_emprestimos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    produto: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    instituicao: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    natureza: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    num_contrato: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    modalidade: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    opa: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    liquidacao_antecipada: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    taxa: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)
    comissao: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)
    data_registro: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    data_vencimento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    quantidade: Mapped[Optional[float]] = mapped_column(Numeric(18, 0), nullable=True)
    preco_fechamento: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    valor_atualizado: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)
    data_pregao: Mapped[Optional[date]] = mapped_column(Date, nullable=True)


class ProventosRecebidosModel(Base):
    """ORM model for B3 received dividends and income.

    Attributes
    ----------
    id : str
        Auto-generated UUID primary key.
    produto : str, optional
        Product description (ticker + company name).
    tipo_evento : str, optional
        Event type (dividendo, JCP, rendimento, etc.).
    valor_liquido : float, optional
        Net payment value.
    data_pregao : date, optional
        Payment reference date.
    """

    __tablename__ = "b3_proventos_recebidos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    produto: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tipo_evento: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    valor_liquido: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)
    data_pregao: Mapped[Optional[date]] = mapped_column(Date, nullable=True)


class ReembolsoEmprestimosModel(Base):
    """ORM model for B3 lending reimbursement records.

    Attributes
    ----------
    id : str
        Auto-generated UUID primary key.
    produto : str, optional
        Product description.
    tipo_evento : str, optional
        Reimbursement event type.
    valor_liquido : float, optional
        Net reimbursement value.
    data_pregao : date, optional
        Reimbursement reference date.
    """

    __tablename__ = "b3_reembolso_emprestimos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    produto: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tipo_evento: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    valor_liquido: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)
    data_pregao: Mapped[Optional[date]] = mapped_column(Date, nullable=True)


class BonificacaoAcoesModel(Base):
    """ORM model for B3 bonus share records.

    Attributes
    ----------
    pk_movimentacao : str
        Composite primary key (concatenated fields).
    entrada_saida : str, optional
        Direction: entry or exit.
    data_pregao : date, optional
        Trading date.
    movimentacao : str, optional
        Movement type description.
    produto : str, optional
        Product description (ticker + company name).
    instituicao : str, optional
        Brokerage institution name.
    quantidade : float, optional
        Bonus share quantity.
    preco_unitario : float, optional
        Unit price (from StatusInvest scraper).
    valor_operacao : float, optional
        Total value (quantidade * preco_unitario).
    """

    __tablename__ = "b3_bonificacao_acoes"

    pk_movimentacao: Mapped[str] = mapped_column(String(600), primary_key=True)
    entrada_saida: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    data_pregao: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    movimentacao: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    produto: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    instituicao: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    quantidade: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    preco_unitario: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    valor_operacao: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)


# ---------------------------------------------------------------------------
# Read-only view models — never passed to session.add()
# ---------------------------------------------------------------------------


class VwProventosModel(Base):
    """Read-only ORM model for the b3_vw_proventos view.

    Attributes
    ----------
    ano_base : int
        Base year extracted from data_pregao.
    ticker : str
        B3 ticker symbol.
    cnpj : str, optional
        Company CNPJ (tax ID).
    nome_compania : str, optional
        Company name.
    movimentacao : str
        Income event type (Dividendo, Juros Sobre Capital Proprio, etc.).
    valor_operacao : float, optional
        Aggregated net value for the year.
    """

    __tablename__ = "b3_vw_proventos"

    ano_base: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), primary_key=True)
    cnpj: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    nome_compania: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    movimentacao: Mapped[str] = mapped_column(String(200), primary_key=True)
    valor_operacao: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)


class VwPmPatrModel(Base):
    """Read-only ORM model for the b3_vw_pm_patr view.

    Attributes
    ----------
    instrumento : str
        B3 ticker symbol (primary key).
    preco_medio_compra : float, optional
        Weighted average buy price.
    qtd_lado : float, optional
        Net quantity held (buys minus sells).
    posicao_fin : float, optional
        Financial position (qtd_lado * preco_medio_compra).
    cnpj : str, optional
        Company CNPJ from the most recent position record.
    nome_compania : str, optional
        Company name from the most recent position record.
    """

    __tablename__ = "b3_vw_pm_patr"

    instrumento: Mapped[str] = mapped_column(String(20), primary_key=True)
    preco_medio_compra: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    qtd_lado: Mapped[Optional[float]] = mapped_column(Numeric(18, 0), nullable=True)
    posicao_fin: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)
    cnpj: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    nome_compania: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


class VwBonificacoesModel(Base):
    """Read-only ORM model for the b3_vw_bonificacoes view.

    Attributes
    ----------
    ano_base : int
        Base year extracted from data_pregao.
    ticker : str
        B3 ticker symbol.
    cnpj : str, optional
        Company CNPJ (tax ID).
    nome_compania : str, optional
        Company name.
    valor_operacao : float, optional
        Total bonus share value for the year.
    """

    __tablename__ = "b3_vw_bonificacoes"

    ano_base: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), primary_key=True)
    cnpj: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    nome_compania: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    valor_operacao: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)
