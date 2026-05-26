"""create_irpf_views

Revision ID: 8ef63ada69a6
Revises: 7b98ce6f574f
Create Date: 2026-05-25 14:54:38.209254

"""
from typing import Sequence, Union

from alembic import op


revision: str = "8ef63ada69a6"
down_revision: Union[str, None] = "7b98ce6f574f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE VIEW b3_vw_bonificacoes AS
        SELECT
            EXTRACT(YEAR FROM b.data_pregao)::int       AS ano_base,
            SPLIT_PART(b.produto, ' - ', 1)             AS ticker,
            COALESCE(pa.cnpj, '')                       AS cnpj,
            SPLIT_PART(b.produto, ' - ', 2)             AS nome_compania,
            SUM(b.valor_operacao)                       AS valor_operacao
        FROM b3_bonificacao_acoes b
        LEFT JOIN (
            SELECT DISTINCT ON (codigo_negociacao)
                codigo_negociacao, cnpj
            FROM b3_posicao_acoes
            ORDER BY codigo_negociacao, data_pregao DESC
        ) pa ON SPLIT_PART(b.produto, ' - ', 1) = pa.codigo_negociacao
        WHERE b.movimentacao = 'Bonificação em Ativos'
        GROUP BY 1, 2, 3, 4
        ORDER BY ticker, ano_base DESC
    """)

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

    op.execute("""
        CREATE OR REPLACE VIEW b3_vw_pm_patr AS
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


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS b3_vw_pm_patr")
    op.execute("DROP VIEW IF EXISTS b3_vw_proventos")
    op.execute("DROP VIEW IF EXISTS b3_vw_bonificacoes")
