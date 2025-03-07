"""Add cost_price to Part model

Revision ID: add_cost_price_to_part
Revises: 2f5df713eedb
Create Date: 2024-03-06 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_cost_price_to_part'
down_revision = '2f5df713eedb'
branch_labels = None
depends_on = None

def upgrade():
    # Add cost_price column to part table
    with op.batch_alter_table('part') as batch_op:
        batch_op.add_column(sa.Column('cost_price', sa.Float(), nullable=True))

def downgrade():
    # Remove cost_price column from part table
    with op.batch_alter_table('part') as batch_op:
        batch_op.drop_column('cost_price') 