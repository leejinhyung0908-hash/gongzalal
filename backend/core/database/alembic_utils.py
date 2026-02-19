"""
Alembic 유틸리티 함수
main.py에서 사용하여 자동으로 마이그레이션 적용
"""
import asyncio
import subprocess
import sys
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def run_alembic_upgrade():
    """Alembic upgrade head 실행 (동기) - Python API 직접 사용"""
    try:
        # 프로젝트 루트로 이동
        project_root = Path(__file__).parent.parent.parent.parent
        original_cwd = os.getcwd()
        os.chdir(project_root)

        # 환경 변수 설정 (인코딩 문제 해결)
        os.environ['PYTHONIOENCODING'] = 'utf-8'

        try:
            # Python API로 직접 실행 (인코딩 문제 우회)
            from alembic import command
            from alembic.config import Config

            alembic_cfg = Config(str(project_root / "alembic.ini"))
            command.upgrade(alembic_cfg, "head")

            logger.info("Alembic 마이그레이션 적용 완료")
            return True
        finally:
            os.chdir(original_cwd)

    except Exception as e:
        logger.error(f"Alembic 마이그레이션 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def run_alembic_upgrade_async():
    """Alembic upgrade head 실행 (비동기 래퍼)"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, run_alembic_upgrade)

