"""add org_id to api_keys, make project_id nullable

Revision ID: a3f1d8e92c47
Revises: cb79acd3a51e
Create Date: 2026-06-02 18:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a3f1d8e92c47'
down_revision: Union[str, None] = 'cb79acd3a51e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use batch mode for SQLite compatibility (requires table recreation)
    with op.batch_alter_table('api_keys', recreate='always') as batch_op:
        # Add org_id — populated from projects.org_id for existing rows via default
        batch_op.add_column(
            sa.Column('org_id', sa.Uuid(), nullable=True)
        )
        # Make project_id nullable (was NOT NULL)
        batch_op.alter_column('project_id', existing_type=sa.Uuid(), nullable=True)

    # Backfill org_id from the project's org for any existing rows
    op.execute(
        """
        UPDATE api_keys
        SET org_id = (
            SELECT org_id FROM projects WHERE projects.id = api_keys.project_id
        )
        WHERE project_id IS NOT NULL
        """
    )

    # Now make org_id NOT NULL and add FK + index
    with op.batch_alter_table('api_keys', recreate='always') as batch_op:
        batch_op.alter_column('org_id', existing_type=sa.Uuid(), nullable=False)
        batch_op.create_foreign_key('fk_api_keys_org_id', 'organizations', ['org_id'], ['id'])
        batch_op.create_index('ix_api_keys_org_id', ['org_id'])


def downgrade() -> None:
    with op.batch_alter_table('api_keys', recreate='always') as batch_op:
        batch_op.drop_index('ix_api_keys_org_id')
        batch_op.drop_constraint('fk_api_keys_org_id', type_='foreignkey')
        batch_op.drop_column('org_id')
        batch_op.alter_column('project_id', existing_type=sa.Uuid(), nullable=False)
