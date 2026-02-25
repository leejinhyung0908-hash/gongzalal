"""rename target_date to study_duration

기존 target_date (Date 타입, 목표 시험일)를
study_duration (VARCHAR(50), 목표 수험 기간)으로 변경.

Revision ID: g6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-02-23
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "g6b7c8d9e0f1"
down_revision = "f5a6b7c8d9e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """target_date (Date) → study_duration (VARCHAR(50)) 변환."""
    # 1. 새 컬럼 추가
    op.add_column("users", sa.Column("study_duration", sa.String(50), nullable=True))

    # 2. 기존 target_date 데이터가 있으면 텍스트로 마이그레이션
    # (예: '2026-06-01' → 날짜 기반이라 자동 변환이 어렵지만, 기존 값 보존)
    op.execute(
        """
        UPDATE users
        SET study_duration = target_date::text
        WHERE target_date IS NOT NULL
        """
    )

    # 3. 기존 target_date 컬럼 삭제
    op.drop_column("users", "target_date")


def downgrade() -> None:
    """study_duration → target_date 롤백."""
    op.add_column("users", sa.Column("target_date", sa.Date(), nullable=True))
    # study_duration은 텍스트이므로 Date로 역변환이 불가한 경우가 대부분
    # (예: '6개월' → Date 변환 불가)
    op.drop_column("users", "study_duration")

