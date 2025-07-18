"""Add status to transaction

Revision ID: add_status_to_transaction
Revises: add_voided_to_purchase
Create Date: 2024-04-18 19:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_status_to_transaction'
down_revision = 'add_voided_to_purchase'
branch_labels = None
depends_on = None

def upgrade():
    # Add status column with default value 'active'
    op.add_column('transaction', sa.Column('status', sa.String(20), nullable=True, server_default='active'))
    
    # Update existing records to have 'active' status
    op.execute("UPDATE transaction SET status = 'active' WHERE status IS NULL")

def downgrade():
    # Remove the status column
    op.drop_column('transaction', 'status')