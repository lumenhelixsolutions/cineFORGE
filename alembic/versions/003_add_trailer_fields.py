"""Add trailer fields to projects.

Revision ID: 003
Revises: 002
Create Date: 2026-06-07
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('trailer_task_id', sa.String(36), nullable=True))
    op.add_column('projects', sa.Column('trailer_url', sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column('projects', 'trailer_url')
    op.drop_column('projects', 'trailer_task_id')
