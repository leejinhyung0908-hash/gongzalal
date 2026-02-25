"""add_user_profile_fields

Users 테이블에 초시여부, 목표직렬, 취약과목, 강점과목 컬럼을 추가합니다.

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-02-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 초시 여부 (첫 시험 응시)
    op.add_column('users', sa.Column('is_first_timer', sa.Boolean(), nullable=True))
    # 목표 직렬 (일반행정, 세무, 교육행정 등)
    op.add_column('users', sa.Column('target_position', sa.String(length=50), nullable=True))
    # 취약 과목 (쉼표 구분)
    op.add_column('users', sa.Column('weak_subjects', sa.Text(), nullable=True))
    # 강점 과목 (쉼표 구분)
    op.add_column('users', sa.Column('strong_subjects', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'strong_subjects')
    op.drop_column('users', 'weak_subjects')
    op.drop_column('users', 'target_position')
    op.drop_column('users', 'is_first_timer')

