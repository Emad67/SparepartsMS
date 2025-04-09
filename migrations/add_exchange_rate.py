"""Add exchange rate to financial transactions

Revision ID: add_exchange_rate
Revises: <previous_revision_id>
Create Date: 2024-XX-XX
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add exchange_rate column to financial_transaction table
    op.add_column('financial_transaction', sa.Column('exchange_rate', sa.Float))
    
    # Update existing records to use default exchange rate (15.0)
    op.execute("UPDATE financial_transaction SET exchange_rate = 15.0")

    op.add_column('credit_purchase', sa.Column('warehouse_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_credit_purchase_warehouse_id', 
        'credit_purchase', 'warehouse',
        ['warehouse_id'], ['id']
    )

def downgrade():
    # Remove exchange_rate column from financial_transaction table
    op.drop_column('financial_transaction', 'exchange_rate')

    op.drop_constraint('fk_credit_purchase_warehouse_id', 'credit_purchase', type_='foreignkey')
    op.drop_column('credit_purchase', 'warehouse_id') 