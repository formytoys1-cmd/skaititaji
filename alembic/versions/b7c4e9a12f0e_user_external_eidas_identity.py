"""user external eidas identity

Revision ID: b7c4e9a12f0e
Revises: f21d22a66b1d
Create Date: 2026-08-20 16:50:00.000000

AUTH-001: связь User с внешней (eIDAS) личностью — external_provider и
external_subject (национальный персональный код). Локальный вход не затронут:
поля nullable и не заполняются для email+пароль.
"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op


revision: str = 'b7c4e9a12f0e'
down_revision: Union[str, None] = 'f21d22a66b1d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('external_provider', sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('external_subject', sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )
        batch_op.create_index(
            batch_op.f('ix_user_external_provider'), ['external_provider'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_user_external_subject'), ['external_subject'], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_user_external_subject'))
        batch_op.drop_index(batch_op.f('ix_user_external_provider'))
        batch_op.drop_column('external_subject')
        batch_op.drop_column('external_provider')
