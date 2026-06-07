"""Real schema migration.

Revision ID: 002
Revises: 001
Create Date: 2026-06-05
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'projects',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('style_pack_id', sa.String(36), nullable=True),
        sa.Column('aspect_ratio', sa.String(10), default='16:9'),
        sa.Column('resolution', sa.String(10), default='1080p'),
        sa.Column('target_duration_sec', sa.Integer, default=60),
        sa.Column('preview_mode', sa.Boolean, default=False),
        sa.Column('routing_profile', sa.String(50), default='hybrid'),
        sa.Column('budget_usd', sa.Float, default=1.00),
        sa.Column('tokens_used_input', sa.Integer, default=0),
        sa.Column('tokens_used_output', sa.Integer, default=0),
        sa.Column('tokens_used_cached', sa.Integer, default=0),
    )

    op.create_table(
        'source_docs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('kind', sa.String(10), nullable=False),
        sa.Column('raw_path', sa.String(512), nullable=False),
        sa.Column('normalized_path', sa.String(512), nullable=False),
        sa.Column('embedding_id', sa.String(36), nullable=True),
        sa.Column('extracted_text', sa.String(10000), nullable=True),
        sa.Column('word_count', sa.Integer, default=0),
    )

    op.create_table(
        'treatments',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('json', sa.JSON, default=dict),
        sa.Column('llm_model', sa.String(100), nullable=False),
        sa.Column('token_usage', sa.JSON, default=dict),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )

    op.create_table(
        'shots',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('order_index', sa.Integer, nullable=False),
        sa.Column('duration_sec', sa.Integer, nullable=False),
        sa.Column('tier', sa.String(20), default='standard'),
        sa.Column('continuity', sa.JSON, default=dict),
        sa.Column('prompt_text', sa.String(2000), default=''),
        sa.Column('prompt_hash', sa.String(64), default=''),
        sa.Column('ref_image_paths', sa.JSON, default=list),
        sa.Column('bridge_strategy', sa.String(30), default='hard_cut'),
        sa.Column('preferred_bridge', sa.String(30), default='hard_cut'),
        sa.Column('clip_path', sa.String(512), nullable=True),
        sa.Column('last_frame_path', sa.String(512), nullable=True),
        sa.Column('status', sa.String(20), default='draft'),
        sa.Column('error', sa.String(2000), nullable=True),
        sa.Column('cost_usd', sa.Float, default=0.0),
        sa.Column('provider_id', sa.String(100), nullable=True),
        sa.Column('render_started_at', sa.DateTime, nullable=True),
        sa.Column('render_finished_at', sa.DateTime, nullable=True),
    )

    op.create_table(
        'style_packs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('yaml_path', sa.String(512), nullable=False),
        sa.Column('embedding_id', sa.String(36), nullable=True),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('is_builtin', sa.Boolean, default=False),
    )

    op.create_table(
        'render_jobs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('started_at', sa.DateTime, default=sa.func.now()),
        sa.Column('finished_at', sa.DateTime, nullable=True),
        sa.Column('output_path', sa.String(512), nullable=True),
        sa.Column('timeline_json', sa.JSON, default=dict),
        sa.Column('status', sa.String(20), default='running'),
        sa.Column('error', sa.String(2000), nullable=True),
        sa.Column('total_cost_usd', sa.Float, default=0.0),
    )

    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('api_key_hash', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('users')
    op.drop_table('render_jobs')
    op.drop_table('style_packs')
    op.drop_table('shots')
    op.drop_table('treatments')
    op.drop_table('source_docs')
    op.drop_table('projects')
