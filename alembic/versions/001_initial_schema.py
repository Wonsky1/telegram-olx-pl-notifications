"""Initial schema creation

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-07-05 14:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Get connection to check existing tables
    connection = op.get_bind()
    
    # Check if flat_records table exists
    result = connection.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'flat_records'
        );
    """))
    flat_records_exists = result.scalar()
    
    # Check if monitoring_tasks table exists
    result = connection.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'monitoring_tasks'
        );
    """))
    monitoring_tasks_exists = result.scalar()
    
    # Create flat_records table if it doesn't exist
    if not flat_records_exists:
        op.create_table('flat_records',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('flat_url', sa.String(), nullable=True),
            sa.Column('source_url', sa.String(), nullable=False),
            sa.Column('title', sa.String(), nullable=True),
            sa.Column('price', sa.String(), nullable=True),
            sa.Column('location', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('created_at_pretty', sa.String(), nullable=True),
            sa.Column('image_url', sa.String(), nullable=True),
            sa.Column('description', sa.String(), nullable=True),
            sa.Column('first_seen', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_flat_records_flat_url'), 'flat_records', ['flat_url'], unique=True)
        op.create_index(op.f('ix_flat_records_id'), 'flat_records', ['id'], unique=False)
        op.create_index(op.f('ix_flat_records_source_url'), 'flat_records', ['source_url'], unique=False)
    else:
        # Table exists, check if source_url column exists
        result = connection.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'flat_records' AND column_name = 'source_url'
            );
        """))
        source_url_exists = result.scalar()
        
        if not source_url_exists:
            # Add source_url column if it doesn't exist
            op.add_column('flat_records', sa.Column('source_url', sa.String(), nullable=True))
            
            # Update existing records to set source_url to flat_url as a fallback
            connection.execute(text("UPDATE flat_records SET source_url = flat_url WHERE source_url IS NULL"))
            
            # Now make the column non-nullable
            op.alter_column('flat_records', 'source_url', nullable=False)
            
            # Create index for source_url
            op.create_index(op.f('ix_flat_records_source_url'), 'flat_records', ['source_url'], unique=False)
    
    # Create monitoring_tasks table if it doesn't exist
    if not monitoring_tasks_exists:
        op.create_table('monitoring_tasks',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('url', sa.String(), nullable=True),
            sa.Column('chat_id', sa.Integer(), nullable=True),
            sa.Column('last_got_flat', sa.DateTime(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_monitoring_tasks_chat_id'), 'monitoring_tasks', ['chat_id'], unique=False)
        op.create_index(op.f('ix_monitoring_tasks_id'), 'monitoring_tasks', ['id'], unique=False)
        op.create_index(op.f('ix_monitoring_tasks_url'), 'monitoring_tasks', ['url'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Get connection to check existing tables
    connection = op.get_bind()
    
    # Check if source_url column exists in flat_records
    result = connection.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_name = 'flat_records' AND column_name = 'source_url'
        );
    """))
    source_url_exists = result.scalar()
    
    if source_url_exists:
        # Drop source_url column and its index
        op.drop_index(op.f('ix_flat_records_source_url'), table_name='flat_records')
        op.drop_column('flat_records', 'source_url')
    
    # Note: We don't drop the tables in downgrade since they might have been created by the worker
    # This is a conservative approach to avoid data loss 