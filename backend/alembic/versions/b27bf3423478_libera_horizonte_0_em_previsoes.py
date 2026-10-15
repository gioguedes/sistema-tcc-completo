"""libera horizonte 0 em previsoes

Revision ID: b27bf3423478
Revises: 0a1560429f38
Create Date: 2026-09-30 22:28:42.535193

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b27bf3423478'
down_revision: Union[str, Sequence[str], None] = '0a1560429f38'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint("ck_prev_horiz", "previsoes", type_="check")
    op.create_check_constraint("ck_prev_horiz", "previsoes", "horizonte_h IN (0,1,2,3)")


def downgrade() -> None:
    """Downgrade schema."""
    # sem apagar as linhas h=0 o CHECK antigo nao pode ser recriado
    op.execute("DELETE FROM previsoes WHERE horizonte_h = 0")
    op.drop_constraint("ck_prev_horiz", "previsoes", type_="check")
    op.create_check_constraint("ck_prev_horiz", "previsoes", "horizonte_h IN (1,2,3)")
