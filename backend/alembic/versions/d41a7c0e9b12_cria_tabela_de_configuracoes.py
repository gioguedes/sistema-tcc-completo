"""cria tabela de configuracoes

Revision ID: d41a7c0e9b12
Revises: b27bf3423478
Create Date: 2026-11-04 22:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd41a7c0e9b12'
down_revision: Union[str, Sequence[str], None] = 'b27bf3423478'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "configuracoes",
        sa.Column("chave", sa.String(length=80), primary_key=True),
        sa.Column("valor", sa.Text(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("configuracoes")
