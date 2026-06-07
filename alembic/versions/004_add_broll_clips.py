"""Add broll_clips table.

Revision ID: 004
Revises: 003
Create Date: 2026-06-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'broll_clips',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('shot_id', sa.String(36), sa.ForeignKey('shots.id'), nullable=False),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('prompt_text', sa.String(2000), default=''),
        sa.Column('clip_path', sa.String(512), nullable=True),
        sa.Column('thumbnail_path', sa.String(512), nullable=True),
        sa.Column('status', sa.String(20), default='draft'),
        sa.Column('error', sa.String(2000), nullable=True),
        sa.Column('cost_usd', sa.Float, default=0.0),
        sa.Column('provider_id', sa.String(100), nullable=True),
        sa.Column('duration_sec', sa.Float, default=0.0),
        sa.Column('clip_meta', SQLiteJSON, default=dict),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('broll_clips')
