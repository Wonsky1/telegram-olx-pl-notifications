"""Rename flat to item and update monitoring tasks

Revision ID: 98f85d0154fb
Revises: 001_initial_schema
Create Date: 2025-07-15 18:17:39.201024

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '98f85d0154fb'
down_revision: Union[str, Sequence[str], None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table('flat_records', 'item_records')
    with op.batch_alter_table('item_records', schema=None) as batch_op:
        batch_op.alter_column('flat_url', new_name='item_url')

    with op.batch_alter_table('monitoring_tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_got_item', sa.DateTime(), nullable=True))
        batch_op.drop_column('last_got_flat')


def downgrade() -> None:
    """Downgrade schema."""
    op.rename_table('item_records', 'flat_records')
    with op.batch_alter_table('flat_records', schema=None) as batch_op:
        batch_op.alter_column('item_url', new_name='flat_url')

    with op.batch_alter_table('monitoring_tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_got_flat', sa.DATETIME(), nullable=True))
        batch_op.drop_column('last_got_item')
