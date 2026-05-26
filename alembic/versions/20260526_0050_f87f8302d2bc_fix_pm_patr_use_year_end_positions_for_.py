"""fix_pm_patr_use_year_end_positions_for_qty

Revision ID: f87f8302d2bc
Revises: ee189da6a711
Create Date: 2026-05-26 00:50:06.660577

Problem: b3_vw_pm_patr previously derived both average buy price AND quantity
from b3_negociacao.  This caused two classes of error:

  1. Missing trades  — years with no negociacao file produced zero quantity for
     those tickers (e.g. 2018/2019 data never exported).
  2. Donations / off-market transfers — shares given away are not recorded as
     sells in negociacao, so net quantity from trades overestimates the true
     position.

Fix: quantity is now taken from the most-recent year-end B3 custody position
(b3_posicao_acoes) plus the most-recent year-end loan position
(b3_posicao_emprestimos).  Average buy price (pm_compra CTE) is unchanged —
it still comes from negociacao history.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "f87f8302d2bc"
down_revision: Union[str, None] = "ee189da6a711"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_VIEW_NEW = """
    CREATE VIEW b3_vw_pm_patr AS
    WITH

    -- Normalise fraction-share tickers (e.g. BBAS3F → BBAS3).
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

    -- Net desdobro (split) quantity per ticker.
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

    -- Spread split shares proportionally across purchase rows for PM calc.
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

    -- Pre-aggregate bonifications per ticker before joining with negociacao
    -- to avoid cross-product multiplication.
    bon_agg AS (
        SELECT
            SPLIT_PART(b.produto, ' - ', 1) AS ticker,
            SUM(b.quantidade)               AS quantidade,
            SUM(b.valor_operacao)           AS valor_operacao
        FROM b3_bonificacao_acoes b
        WHERE b.movimentacao = 'Bonificação em Ativos'
        GROUP BY 1
    ),

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

    -- Weighted-average buy price per instrument from negociacao history.
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

    -- Authoritative year-end custody from the annual consolidated B3 report.
    year_end_custody_date AS (
        SELECT MAX(data_pregao) AS dt FROM b3_posicao_acoes
    ),

    year_end_custody AS (
        SELECT
            p.codigo_negociacao                  AS ticker,
            p.cnpj,
            SPLIT_PART(p.produto, ' - ', 2)      AS nome_compania,
            SUM(p.quantidade)                    AS quantidade
        FROM b3_posicao_acoes p, year_end_custody_date d
        WHERE p.data_pregao = d.dt
        GROUP BY 1, 2, 3
    ),

    -- Loaned shares at the most-recent year-end (B3 BTC positions).
    year_end_loans_date AS (
        SELECT MAX(data_pregao) AS dt FROM b3_posicao_emprestimos
    ),

    year_end_loans AS (
        SELECT
            SPLIT_PART(p.produto, ' - ', 1)      AS ticker,
            MAX(SPLIT_PART(p.produto, ' - ', 2)) AS nome_compania,
            SUM(p.quantidade)                    AS quantidade
        FROM b3_posicao_emprestimos p, year_end_loans_date d
        WHERE p.data_pregao = d.dt
        GROUP BY SPLIT_PART(p.produto, ' - ', 1)
    ),

    -- Total position = available custody + loaned shares.
    year_end_pos AS (
        SELECT
            COALESCE(c.ticker, l.ticker)                            AS ticker,
            COALESCE(c.quantidade, 0) + COALESCE(l.quantidade, 0)  AS qtd_lado,
            c.cnpj,
            COALESCE(c.nome_compania, l.nome_compania)              AS nome_compania
        FROM year_end_custody c
        FULL OUTER JOIN year_end_loans l ON c.ticker = l.ticker
    )

    SELECT
        yep.ticker                                   AS instrumento,
        pmc.preco_medio_compra,
        yep.qtd_lado,
        yep.qtd_lado * pmc.preco_medio_compra        AS posicao_fin,
        COALESCE(yep.cnpj, '')                        AS cnpj,
        COALESCE(yep.nome_compania, yep.ticker)       AS nome_compania
    FROM year_end_pos yep
    LEFT JOIN pm_compra pmc ON yep.ticker = pmc.instrumento
    WHERE yep.qtd_lado > 0
    ORDER BY yep.ticker
"""

# Restore the previous view on downgrade.
_VIEW_PREV = """
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
    bon_agg AS (
        SELECT
            SPLIT_PART(b.produto, ' - ', 1) AS ticker,
            SUM(b.quantidade)               AS quantidade,
            SUM(b.valor_operacao)           AS valor_operacao
        FROM b3_bonificacao_acoes b
        WHERE b.movimentacao = 'Bonificação em Ativos'
        GROUP BY 1
    ),
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


def upgrade() -> None:
    op.execute("DROP VIEW IF EXISTS b3_vw_pm_patr")
    op.execute(_VIEW_NEW)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS b3_vw_pm_patr")
    op.execute(_VIEW_PREV)
