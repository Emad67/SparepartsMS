"""Add void-related columns to FinancialTransaction

Revision ID: 2f5df713eedb
Revises: ae7c494077c5
Create Date: 2024-03-05 17:49:26.123456

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2f5df713eedb'
down_revision = 'ae7c494077c5'
branch_labels = None
depends_on = None


def upgrade():
    # Add void-related columns to financial_transaction table
    with op.batch_alter_table('financial_transaction') as batch_op:
        batch_op.add_column(sa.Column('voided', sa.Boolean(), nullable=True, default=False))
        batch_op.add_column(sa.Column('void_reason', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('voided_by_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('voided_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('void_reference_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_voided_by', 'user', ['voided_by_id'], ['id'])
        batch_op.create_foreign_key('fk_void_reference', 'financial_transaction', ['void_reference_id'], ['id'])


def downgrade():
    # Remove void-related columns from financial_transaction table
    with op.batch_alter_table('financial_transaction') as batch_op:
        batch_op.drop_constraint('fk_void_reference', type_='foreignkey')
        batch_op.drop_constraint('fk_voided_by', type_='foreignkey')
        batch_op.drop_column('void_reference_id')
        batch_op.drop_column('voided_at')
        batch_op.drop_column('voided_by_id')
        batch_op.drop_column('void_reason')
        batch_op.drop_column('voided')
