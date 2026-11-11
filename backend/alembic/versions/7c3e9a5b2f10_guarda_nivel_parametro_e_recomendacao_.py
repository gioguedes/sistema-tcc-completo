"""guarda nivel, parametro e recomendacao do alerta

Revision ID: 7c3e9a5b2f10
Revises: d41a7c0e9b12
Create Date: 2026-11-10 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c3e9a5b2f10'
down_revision: Union[str, Sequence[str], None] = 'd41a7c0e9b12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("alertas", sa.Column("nivel_risco", sa.String(length=20), nullable=True))
    op.add_column("alertas", sa.Column("parametro", sa.String(length=30), nullable=True))
    op.add_column("alertas", sa.Column("recomendacao", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_alert_nivel", "alertas", "nivel_risco IS NULL OR nivel_risco IN ('otimo','atencao','critico')"
    )
    op.create_check_constraint(
        "ck_alert_param", "alertas", "parametro IS NULL OR parametro IN ('ph','temperatura','turbidez','od')"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_alert_param", "alertas", type_="check")
    op.drop_constraint("ck_alert_nivel", "alertas", type_="check")
    op.drop_column("alertas", "recomendacao")
    op.drop_column("alertas", "parametro")
    op.drop_column("alertas", "nivel_risco")
