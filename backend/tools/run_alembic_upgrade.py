"""
Alembic upgrade를 Python으로 직접 실행
인코딩 문제를 우회합니다.
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 환경 변수 설정
os.environ['PYTHONIOENCODING'] = 'utf-8'

from alembic import command
from alembic.config import Config

# alembic.ini 경로
alembic_cfg = Config(str(project_root / "alembic.ini"))

# upgrade head 실행
print("[INFO] Alembic 마이그레이션 실행 중...")
try:
    command.upgrade(alembic_cfg, "head")
    print("[OK] Alembic 마이그레이션 완료!")
except Exception as e:
    print(f"[ERROR] 마이그레이션 실패: {e}")
    sys.exit(1)

