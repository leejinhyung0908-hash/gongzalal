"""
초기 마이그레이션 파일 생성 스크립트
인코딩 문제를 우회하여 직접 마이그레이션 파일을 생성합니다.
"""
import os
from datetime import datetime
from pathlib import Path

# 프로젝트 루트
project_root = Path(__file__).parent
alembic_versions = project_root / "alembic" / "versions"
alembic_versions.mkdir(parents=True, exist_ok=True)

# 마이그레이션 파일명 생성
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
revision_id = "001"
migration_file = alembic_versions / f"{revision_id}_initialize_database_schema.py"

# 마이그레이션 파일 내용
migration_content = '''"""Initialize database schema

Revision ID: 001
Revises:
Create Date: {date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # pgvector extension 활성화
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # users 테이블 생성
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('external_id', sa.Text(), nullable=False),
        sa.Column('nickname', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_id', name='uq_users_external_id')
    )

    # exam_questions 테이블 생성
    op.create_table(
        'exam_questions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('exam_type', sa.Text(), nullable=False),
        sa.Column('job_series', sa.Text(), nullable=False),
        sa.Column('grade', sa.Text(), nullable=False, server_default='9급'),
        sa.Column('exam_name', sa.Text(), nullable=False, server_default='지방공무원 공개경쟁임용'),
        sa.Column('subject', sa.Text(), nullable=False),
        sa.Column('question_no', sa.SmallInteger(), nullable=False),
        sa.Column('source_md', sa.Text(), nullable=True),
        sa.Column('source_pdf', sa.Text(), nullable=True),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('answer_key', sa.Text(), nullable=False),
        sa.Column('extra_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{{}}'),
        sa.Column('embedding', postgresql.ARRAY(sa.REAL()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('year', 'exam_type', 'job_series', 'grade', 'subject', 'question_no', name='uq_exam_questions_key'),
        sa.CheckConstraint('question_no >= 1 AND question_no <= 200', name='ck_question_no_range')
    )

    # commentaries 테이블 생성
    op.create_table(
        'commentaries',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('exam_question_id', sa.BigInteger(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('selected', sa.Text(), nullable=True),
        sa.Column('is_correct', sa.Boolean(), nullable=True),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('confidence', sa.SmallInteger(), nullable=True),
        sa.Column('bookmarked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('extra_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{{}}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['exam_question_id'], ['exam_questions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'exam_question_id', name='uq_commentary_user_exam')
    )


def downgrade() -> None:
    op.drop_table('commentaries')
    op.drop_table('exam_questions')
    op.drop_table('users')
    op.execute('DROP EXTENSION IF EXISTS vector')
'''.format(date=datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3])

# 파일 작성
with open(migration_file, 'w', encoding='utf-8') as f:
    f.write(migration_content)

print(f"[OK] 초기 마이그레이션 파일 생성 완료: {migration_file}")
print(f"[INFO] 이제 'python -m alembic upgrade head' 명령어로 테이블을 생성할 수 있습니다.")

