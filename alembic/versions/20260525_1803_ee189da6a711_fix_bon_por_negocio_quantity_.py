"""fix_bon_por_negocio_quantity_multiplication_in_pm_patr_view

Revision ID: ee189da6a711
Revises: 26dad2ebb1dc
Create Date: 2026-05-25 18:03:39.939908

Bug: bon_por_negocio computed SUM(b.quantidade) after a LEFT JOIN against
neg_com_instrumento.  The cross-product multiplied each bonification row by
the number of negociação rows for the same ticker, so both:

  • ct_qtd_liquida.MAX(bon.quantidade)  – total bonus shares added to the
    portfolio (e.g. ITSA4: 1 322 correct → 13 224 wrong)
  • pm_compra denominator (qtd_bon_por_neg per purchase row) – slightly
    inflated, making the average price slightly lower than the truth

Fix: split bon_por_negocio into two CTEs:
  1. bon_agg        – SUM bonification qty/val PER TICKER (no join).
  2. bon_n_compras  – COUNT purchase rows PER TICKER from neg_com_instrumento.
  3. bon_por_negocio – joins the two, giving correct totals and correct
                       per-trade allocations.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "ee189da6a711"
down_revision: Union[str, None] = "26dad2ebb1dc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_VIEW_CORRECT = """
    CREATE VIEW b3_vw_pm_patr AS
    WITH
    neg_com_instrumento AS (
        SELECT
            *,
            CASE
                WHEN RIGHT(ticker, 1) = 'F'
                THEN LEFT(ticker, CHAR_LENGTH(ticker) - 1)
                ELSE ticker
            END AS instrumento
        FROM b3_negociacao
    ),
    ct_splits AS (
        SELECT
            SPLIT_PART(produto, ' - ', 1) AS ticker,
            SUM(
                CASE WHEN entrada_saida = 'Credito' THEN quantidade
                     ELSE -quantidade END
            ) AS qtd_lado
        FROM b3_movimentacao
        WHERE movimentacao = 'Desdobro'
        GROUP BY 1
    ),
    ct_splits_por_compra AS (
        SELECT
            s.ticker,
            s.qtd_lado / NULLIF(COUNT(n.instrumento), 0) AS qtd_lado,
            s.qtd_lado                                    AS qtd_lado_orig
        FROM ct_splits s
        LEFT JOIN neg_com_instrumento n
            ON s.ticker = n.instrumento
            AND n.tipo_movimentacao = 'Compra'
        GROUP BY s.ticker, s.qtd_lado
    ),
    neg_com_splits_c AS (
        SELECT
            n.*,
            n.quantidade + COALESCE(s.qtd_lado, 0) AS quantidade_net
        FROM neg_com_instrumento n
        LEFT JOIN ct_splits_por_compra s ON n.instrumento = s.ticker
    ),
    -- Pre-aggregate bonifications per ticker BEFORE joining with negociação
    -- so SUM(b.quantidade) is never multiplied by the number of trade rows.
    bon_agg AS (
        SELECT
            SPLIT_PART(b.produto, ' - ', 1) AS ticker,
            SUM(b.quantidade)               AS quantidade,
            SUM(b.valor_operacao)           AS valor_operacao
        FROM b3_bonificacao_acoes b
        WHERE b.movimentacao = 'Bonificação em Ativos'
        GROUP BY 1
    ),
    -- Count how many purchase rows exist per ticker so bonus shares can be
    -- spread proportionally across each purchase for the PM calculation.
    bon_n_compras AS (
        SELECT instrumento AS ticker, COUNT(*) AS n_compras
        FROM neg_com_instrumento
        WHERE tipo_movimentacao = 'Compra'
        GROUP BY 1
    ),
    bon_por_negocio AS (
        SELECT
            a.ticker,
            a.quantidade,
            a.valor_operacao,
            a.valor_operacao / NULLIF(c.n_compras, 0) AS valor_bon_por_neg,
            a.quantidade     / NULLIF(c.n_compras, 0) AS qtd_bon_por_neg
        FROM bon_agg a
        LEFT JOIN bon_n_compras c ON a.ticker = c.ticker
    ),
    pm_compra AS (
        SELECT
            n.instrumento,
            SUM(n.quantidade * n.preco + COALESCE(bon.valor_bon_por_neg, 0))
                / NULLIF(SUM(n.quantidade_net + COALESCE(bon.qtd_bon_por_neg, 0)), 0)
                AS preco_medio_compra
        FROM neg_com_splits_c n
        LEFT JOIN bon_por_negocio bon ON n.instrumento = bon.ticker
        WHERE n.tipo_movimentacao = 'Compra'
        GROUP BY 1
    ),
    ct_qtd_liquida AS (
        SELECT
            n.instrumento,
            SUM(CASE WHEN n.tipo_movimentacao = 'Compra'
                     THEN n.quantidade ELSE -n.quantidade END)
                + COALESCE(MAX(spl.qtd_lado_orig), 0)
                + COALESCE(MAX(bon.quantidade), 0)   AS qtd_lado
        FROM neg_com_instrumento n
        LEFT JOIN ct_splits_por_compra spl ON n.instrumento = spl.ticker
        LEFT JOIN bon_por_negocio bon       ON n.instrumento = bon.ticker
        GROUP BY 1
    ),
    last_position AS (
        SELECT DISTINCT ON (codigo_negociacao)
            codigo_negociacao,
            cnpj,
            SPLIT_PART(produto, ' - ', 2) AS nome_compania
        FROM b3_posicao_acoes
        ORDER BY codigo_negociacao, data_pregao DESC
    )
    SELECT
        pmc.instrumento,
        pmc.preco_medio_compra,
        qtl.qtd_lado,
        qtl.qtd_lado * pmc.preco_medio_compra       AS posicao_fin,
        COALESCE(lp.cnpj, '')                        AS cnpj,
        COALESCE(lp.nome_compania, pmc.instrumento)  AS nome_compania
    FROM pm_compra pmc
    LEFT JOIN ct_qtd_liquida qtl ON pmc.instrumento = qtl.instrumento
    LEFT JOIN last_position lp   ON pmc.instrumento = lp.codigo_negociacao
    WHERE qtl.qtd_lado > 0
    ORDER BY pmc.instrumento
"""

# Buggy version (before this fix) — restored on downgrade.
_VIEW_BUGGY = """
    CREATE VIEW b3_vw_pm_patr AS
    WITH
    neg_com_instrumento AS (
        SELECT
            *,
            CASE
                WHEN RIGHT(ticker, 1) = 'F'
                THEN LEFT(ticker, CHAR_LENGTH(ticker) - 1)
                ELSE ticker
            END AS instrumento
        FROM b3_negociacao
    ),
    ct_splits AS (
        SELECT
            SPLIT_PART(produto, ' - ', 1) AS ticker,
            SUM(
                CASE WHEN entrada_saida = 'Credito' THEN quantidade
                     ELSE -quantidade END
            ) AS qtd_lado
        FROM b3_movimentacao
        WHERE movimentacao = 'Desdobro'
        GROUP BY 1
    ),
    ct_splits_por_compra AS (
        SELECT
            s.ticker,
            s.qtd_lado / NULLIF(COUNT(n.instrumento), 0) AS qtd_lado,
            s.qtd_lado                                    AS qtd_lado_orig
        FROM ct_splits s
        LEFT JOIN neg_com_instrumento n
            ON s.ticker = n.instrumento
            AND n.tipo_movimentacao = 'Compra'
        GROUP BY s.ticker, s.qtd_lado
    ),
    neg_com_splits_c AS (
        SELECT
            n.*,
            n.quantidade + COALESCE(s.qtd_lado, 0) AS quantidade_net
        FROM neg_com_instrumento n
        LEFT JOIN ct_splits_por_compra s ON n.instrumento = s.ticker
    ),
    bon_por_negocio AS (
        SELECT
            SPLIT_PART(b.produto, ' - ', 1)                           AS ticker,
            SUM(b.quantidade)                                          AS quantidade,
            SUM(b.valor_operacao)                                      AS valor_operacao,
            SUM(b.valor_operacao) / NULLIF(COUNT(n.instrumento), 0)   AS valor_bon_por_neg,
            SUM(b.quantidade)     / NULLIF(COUNT(n.instrumento), 0)   AS qtd_bon_por_neg
        FROM b3_bonificacao_acoes b
        LEFT JOIN neg_com_instrumento n
            ON SPLIT_PART(b.produto, ' - ', 1) = n.instrumento
        WHERE b.movimentacao = 'Bonificação em Ativos'
        GROUP BY 1
    ),
    pm_compra AS (
        SELECT
            n.instrumento,
            SUM(n.quantidade * n.preco + COALESCE(bon.valor_bon_por_neg, 0))
                / NULLIF(SUM(n.quantidade_net + COALESCE(bon.qtd_bon_por_neg, 0)), 0)
                AS preco_medio_compra
        FROM neg_com_splits_c n
        LEFT JOIN bon_por_negocio bon ON n.instrumento = bon.ticker
        WHERE n.tipo_movimentacao = 'Compra'
        GROUP BY 1
    ),
    ct_qtd_liquida AS (
        SELECT
            n.instrumento,
            SUM(CASE WHEN n.tipo_movimentacao = 'Compra'
                     THEN n.quantidade ELSE -n.quantidade END)
                + COALESCE(MAX(spl.qtd_lado_orig), 0)
                + COALESCE(MAX(bon.quantidade), 0)   AS qtd_lado
        FROM neg_com_instrumento n
        LEFT JOIN ct_splits_por_compra spl ON n.instrumento = spl.ticker
        LEFT JOIN bon_por_negocio bon       ON n.instrumento = bon.ticker
        GROUP BY 1
    ),
    last_position AS (
        SELECT DISTINCT ON (codigo_negociacao)
            codigo_negociacao,
            cnpj,
            SPLIT_PART(produto, ' - ', 2) AS nome_compania
        FROM b3_posicao_acoes
        ORDER BY codigo_negociacao, data_pregao DESC
    )
    SELECT
        pmc.instrumento,
        pmc.preco_medio_compra,
        qtl.qtd_lado,
        qtl.qtd_lado * pmc.preco_medio_compra       AS posicao_fin,
        COALESCE(lp.cnpj, '')                        AS cnpj,
        COALESCE(lp.nome_compania, pmc.instrumento)  AS nome_compania
    FROM pm_compra pmc
    LEFT JOIN ct_qtd_liquida qtl ON pmc.instrumento = qtl.instrumento
    LEFT JOIN last_position lp   ON pmc.instrumento = lp.codigo_negociacao
    WHERE qtl.qtd_lado > 0
    ORDER BY pmc.instrumento
"""


def upgrade() -> None:
    op.execute("DROP VIEW IF EXISTS b3_vw_pm_patr")
    op.execute(_VIEW_CORRECT)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS b3_vw_pm_patr")
    op.execute(_VIEW_BUGGY)
