"""email verification + unit capacity

Revision ID: c3f5a7b91d02
Revises: b7c4e9a12f0e
Create Date: 2026-08-21 07:30:00.000000

Онбординг пользователей:
- user.is_verified / verified_at — подтверждение e-mail при самрегистрации.
  Легаси-пользователи (созданные до этой миграции) бэкфиллятся как verified,
  чтобы существующие аккаунты не оказались заблокированы.
- unit.max_residents — вместимость квартиры (сколько человек может
  зарегистрироваться; запас ×2). Существующие квартиры получают 2.
- email_verification — одноразовые токены подтверждения e-mail.
"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op


revision: str = 'c3f5a7b91d02'
down_revision: Union[str, None] = 'b7c4e9a12f0e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- user: подтверждение e-mail --------------------------------------- #
    # Добавляем с server_default=TRUE, чтобы существующие (легаси) строки
    # автоматически стали verified и вход не заблокировался. Затем меняем
    # дефолт на FALSE, чтобы будущие записи по умолчанию были неподтверждёнными.
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('is_verified', sa.Boolean(), nullable=False,
                      server_default=sa.true())
        )
        batch_op.add_column(
            sa.Column('verified_at', sa.DateTime(), nullable=True)
        )
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('is_verified', server_default=sa.false())

    # --- unit: вместимость ------------------------------------------------- #
    with op.batch_alter_table('unit', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('max_residents', sa.Integer(), nullable=False,
                      server_default=sa.text('2'))
        )

    # --- таблица токенов подтверждения ------------------------------------ #
    op.create_table(
        'email_verification',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('purpose', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_email_verification_token'),
                    'email_verification', ['token'], unique=True)
    op.create_index(op.f('ix_email_verification_user_id'),
                    'email_verification', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_email_verification_user_id'),
                  table_name='email_verification')
    op.drop_index(op.f('ix_email_verification_token'),
                  table_name='email_verification')
    op.drop_table('email_verification')
    with op.batch_alter_table('unit', schema=None) as batch_op:
        batch_op.drop_column('max_residents')
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('verified_at')
        batch_op.drop_column('is_verified')
