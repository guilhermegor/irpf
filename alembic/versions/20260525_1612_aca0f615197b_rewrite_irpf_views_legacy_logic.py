"""rewrite_irpf_views_legacy_logic

Revision ID: aca0f615197b
Revises: 86053cd8b1f8
Create Date: 2026-05-25 16:12:32.751840

"""

from typing import Sequence, Union

from alembic import op


revision: str = "aca0f615197b"
down_revision: Union[str, None] = "86053cd8b1f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # b3_vw_proventos: source from b3_movimentacao (matches legacy VW_PROVENTOS logic).
    # The previous version incorrectly sourced from b3_proventos_recebidos /
    # b3_reembolso_emprestimos (annual-report tabs), which do not contain lending,
    # reimbursement, fraction-auction, or rendimento events.
    op.execute("""
        CREATE OR REPLACE VIEW b3_vw_proventos AS
        SELECT
            EXTRACT(YEAR FROM m.data_pregao)::int       AS ano_base,
            SPLIT_PART(m.produto, ' - ', 1)             AS ticker,
            COALESCE(pa.cnpj, '')                       AS cnpj,
            SPLIT_PART(m.produto, ' - ', 2)             AS nome_compania,
            m.movimentacao,
            SUM(m.valor_operacao)                       AS valor_operacao
        FROM b3_movimentacao m
        LEFT JOIN (
            SELECT DISTINCT ON (codigo_negociacao)
                codigo_negociacao, cnpj
            FROM b3_posicao_acoes
            ORDER BY codigo_negociacao, data_pregao DESC
        ) pa ON SPLIT_PART(m.produto, ' - ', 1) = pa.codigo_negociacao
        WHERE m.movimentacao IN (
            'Rendimento',
            'Empréstimo',
            'Leilão de Fração',
            'Dividendo',
            'Dividendo - Transferido',
            'Juros Sobre Capital Próprio',
            'Juros Sobre Capital Próprio - Transferido',
            'Reembolso'
        )
        GROUP BY 1, 2, 3, 4, 5
        HAVING SUM(m.valor_operacao) <> 0
        ORDER BY 1 DESC, 2, 3
    """)

    # b3_vw_pm_patr: rewritten to match legacy VW_PM_PATR.
    # Adds splits/inplits adjustment (Desdobro events from b3_movimentacao) and
    # bonus-share cost allocation per trade (bon_por_negocio CTE from
    # b3_bonificacao_acoes), both of which were absent from the previous version.
    # DROP required first: CREATE OR REPLACE cannot change column types (bigint → numeric).
    op.execute("DROP VIEW IF EXISTS b3_vw_pm_patr")
    op.execute("""
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
        ct_splits_por_venda AS (
            SELECT
                s.ticker,
                s.qtd_lado / NULLIF(COUNT(n.instrumento), 0) AS qtd_lado,
                s.qtd_lado                                    AS qtd_lado_orig
            FROM ct_splits s
            LEFT JOIN neg_com_instrumento n
                ON s.ticker = n.instrumento
                AND n.tipo_movimentacao = 'Venda'
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
    """)


def downgrade() -> None:
    # Restore previous (incorrect) versions so rollback is a clean inverse.
    op.execute("""
        CREATE OR REPLACE VIEW b3_vw_proventos AS
        SELECT
            EXTRACT(YEAR FROM pr.data_pregao)::int  AS ano_base,
            SPLIT_PART(pr.produto, ' - ', 1)        AS ticker,
            COALESCE(pa.cnpj, '')                   AS cnpj,
            SPLIT_PART(pr.produto, ' - ', 2)        AS nome_compania,
            pr.tipo_evento                          AS movimentacao,
            SUM(pr.valor_liquido)                   AS valor_operacao
        FROM b3_proventos_recebidos pr
        LEFT JOIN (
            SELECT DISTINCT ON (codigo_negociacao)
                codigo_negociacao, cnpj
            FROM b3_posicao_acoes
            ORDER BY codigo_negociacao, data_pregao DESC
        ) pa ON SPLIT_PART(pr.produto, ' - ', 1) = pa.codigo_negociacao
        GROUP BY 1, 2, 3, 4, 5
        HAVING SUM(pr.valor_liquido) <> 0
        UNION ALL
        SELECT
            EXTRACT(YEAR FROM re.data_pregao)::int  AS ano_base,
            SPLIT_PART(re.produto, ' - ', 1)        AS ticker,
            COALESCE(pa.cnpj, '')                   AS cnpj,
            SPLIT_PART(re.produto, ' - ', 2)        AS nome_compania,
            re.tipo_evento                          AS movimentacao,
            SUM(re.valor_liquido)                   AS valor_operacao
        FROM b3_reembolso_emprestimos re
        LEFT JOIN (
            SELECT DISTINCT ON (codigo_negociacao)
                codigo_negociacao, cnpj
            FROM b3_posicao_acoes
            ORDER BY codigo_negociacao, data_pregao DESC
        ) pa ON SPLIT_PART(re.produto, ' - ', 1) = pa.codigo_negociacao
        GROUP BY 1, 2, 3, 4, 5
        HAVING SUM(re.valor_liquido) <> 0
    """)

    op.execute("DROP VIEW IF EXISTS b3_vw_pm_patr")
    op.execute("""
        CREATE VIEW b3_vw_pm_patr AS
        WITH buy_totals AS (
            SELECT
                CASE
                    WHEN RIGHT(ticker, 1) = 'F'
                    THEN LEFT(ticker, CHAR_LENGTH(ticker) - 1)
                    ELSE ticker
                END                                                                AS instrumento,
                SUM(CASE WHEN tipo_movimentacao = 'Compra' THEN quantidade ELSE 0 END)
                                                                                   AS total_bought,
                SUM(CASE WHEN tipo_movimentacao = 'Compra' THEN quantidade * preco ELSE 0 END)
                                                                                   AS total_cost,
                SUM(CASE WHEN tipo_movimentacao = 'Compra' THEN quantidade ELSE 0 END)
                    - SUM(CASE WHEN tipo_movimentacao = 'Venda' THEN quantidade ELSE 0 END)
                                                                                   AS qtd_lado
            FROM b3_negociacao
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
            bt.instrumento,
            CASE WHEN bt.total_bought > 0 THEN bt.total_cost / bt.total_bought
                 ELSE 0 END                                                        AS preco_medio_compra,
            bt.qtd_lado,
            bt.qtd_lado * CASE WHEN bt.total_bought > 0
                               THEN bt.total_cost / bt.total_bought ELSE 0 END    AS posicao_fin,
            COALESCE(lp.cnpj, '')                                                  AS cnpj,
            COALESCE(lp.nome_compania, bt.instrumento)                             AS nome_compania
        FROM buy_totals bt
        LEFT JOIN last_position lp ON bt.instrumento = lp.codigo_negociacao
        WHERE bt.qtd_lado > 0
    """)
