"""add_unique_constraints_annual_report_tables

Revision ID: 26dad2ebb1dc
Revises: aca0f615197b
Create Date: 2026-05-25 17:24:23.094691

Deduplicate existing rows in the four UUID-keyed annual-report tables, then
add unique constraints so subsequent imports are idempotent via INSERT OR IGNORE.

Natural keys chosen:
  b3_posicao_acoes      → (codigo_negociacao, data_pregao, instituicao, conta)
  b3_posicao_emprestimos → (num_contrato, data_pregao)
  b3_proventos_recebidos → (produto, tipo_evento, data_pregao)
  b3_reembolso_emprestimos → (produto, tipo_evento, data_pregao)
"""

from typing import Sequence, Union

from alembic import op


revision: str = "26dad2ebb1dc"
down_revision: Union[str, None] = "aca0f615197b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- b3_posicao_acoes -------------------------------------------------------
    op.execute("""
        DELETE FROM b3_posicao_acoes
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM b3_posicao_acoes
            GROUP BY codigo_negociacao, data_pregao, instituicao, conta
        )
    """)
    op.execute("""
        ALTER TABLE b3_posicao_acoes
        ADD CONSTRAINT uq_posicao_acoes
        UNIQUE (codigo_negociacao, data_pregao, instituicao, conta)
    """)

    # -- b3_posicao_emprestimos -------------------------------------------------
    op.execute("""
        DELETE FROM b3_posicao_emprestimos
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM b3_posicao_emprestimos
            GROUP BY num_contrato, data_pregao
        )
    """)
    op.execute("""
        ALTER TABLE b3_posicao_emprestimos
        ADD CONSTRAINT uq_posicao_emprestimos
        UNIQUE (num_contrato, data_pregao)
    """)

    # -- b3_proventos_recebidos -------------------------------------------------
    op.execute("""
        DELETE FROM b3_proventos_recebidos
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM b3_proventos_recebidos
            GROUP BY produto, tipo_evento, data_pregao
        )
    """)
    op.execute("""
        ALTER TABLE b3_proventos_recebidos
        ADD CONSTRAINT uq_proventos_recebidos
        UNIQUE (produto, tipo_evento, data_pregao)
    """)

    # -- b3_reembolso_emprestimos -----------------------------------------------
    op.execute("""
        DELETE FROM b3_reembolso_emprestimos
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM b3_reembolso_emprestimos
            GROUP BY produto, tipo_evento, data_pregao
        )
    """)
    op.execute("""
        ALTER TABLE b3_reembolso_emprestimos
        ADD CONSTRAINT uq_reembolso_emprestimos
        UNIQUE (produto, tipo_evento, data_pregao)
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE b3_reembolso_emprestimos DROP CONSTRAINT IF EXISTS uq_reembolso_emprestimos")
    op.execute("ALTER TABLE b3_proventos_recebidos DROP CONSTRAINT IF EXISTS uq_proventos_recebidos")
    op.execute("ALTER TABLE b3_posicao_emprestimos DROP CONSTRAINT IF EXISTS uq_posicao_emprestimos")
    op.execute("ALTER TABLE b3_posicao_acoes DROP CONSTRAINT IF EXISTS uq_posicao_acoes")
