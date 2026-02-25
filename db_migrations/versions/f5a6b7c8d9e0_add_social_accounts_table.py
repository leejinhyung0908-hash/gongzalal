"""add_social_accounts_table

소셜 계정 연동 테이블 추가.
한 사용자가 여러 소셜 계정(카카오, 네이버, 구글)을 연결할 수 있도록
social_accounts 테이블을 생성합니다.

기존 users 테이블의 social_id/provider 데이터를 social_accounts로 마이그레이션합니다.

- social_accounts: (user_id FK, provider, social_id, email) — UNIQUE(provider, social_id)
- users 테이블의 social_id UNIQUE 제약 제거 (더 이상 직접 사용하지 않음)
- users 테이블에 email 컬럼 추가

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-02-20 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


# revision identifiers, used by Alembic.
revision: str = 'f5a6b7c8d9e0'
down_revision: Union[str, None] = 'e4f5a6b7c8d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. social_accounts 테이블 생성
    op.create_table(
        'social_accounts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(20), nullable=False),
        sa.Column('social_id', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('linked_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('provider', 'social_id', name='uq_social_accounts_provider_social_id'),
    )

    # 2. users 테이블에 email 컬럼 추가
    op.add_column('users', sa.Column('email', sa.String(255), nullable=True))

    # 3. 기존 users.social_id + provider 데이터를 social_accounts로 마이그레이션
    op.execute(text("""
        INSERT INTO social_accounts (user_id, provider, social_id, linked_at)
        SELECT id, provider, social_id, registration_date
        FROM users
        WHERE social_id IS NOT NULL AND provider IS NOT NULL
        ON CONFLICT (provider, social_id) DO NOTHING
    """))

    # 4. users.social_id의 UNIQUE 제약 제거
    #    (social_accounts가 이제 주 테이블이므로)
    try:
        op.drop_constraint('users_social_id_key', 'users', type_='unique')
    except Exception:
        # 제약 이름이 다를 수 있음
        try:
            op.drop_index('ix_users_social_id', table_name='users')
        except Exception:
            pass  # 이미 없으면 무시


def downgrade() -> None:
    # social_accounts 테이블 삭제
    op.drop_table('social_accounts')

    # email 컬럼 삭제
    op.drop_column('users', 'email')

    # social_id UNIQUE 제약 복원
    op.create_unique_constraint('users_social_id_key', 'users', ['social_id'])

