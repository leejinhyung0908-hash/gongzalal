"""FastAPI 메인 애플리케이션."""
import logging
import os
import sys

# NOTE:
# `python backend/main.py --server` 처럼 "파일 경로 실행"을 하면,
# sys.path[0]가 `backend/`로 잡혀 `import backend.xxx`가 실패할 수 있습니다.
# 로컬 개발 편의를 위해 프로젝트 루트를 sys.path에 보강합니다.
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.dependencies import connect_db, get_global_db_connection, setup_schema
import backend.dependencies as deps
from backend.core.database.alembic_utils import run_alembic_upgrade_async

# 환경 변수 로드
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# 비동기 컨텍스트 매니저, 데이터베이스 초기화
@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리."""
    # 시작 시
    logger.info("[FastAPI] 서버 시작 중...")

    try:
        deps._db_conn = connect_db(settings.DATABASE_URL)
        setup_schema(deps._db_conn)

        # Alembic 마이그레이션 자동 적용
        logger.info("[FastAPI] Alembic 마이그레이션 적용 중...")
        migration_success = await run_alembic_upgrade_async()
        if migration_success:
            logger.info("[FastAPI] Alembic 마이그레이션 적용 완료")
        else:
            logger.warning("[FastAPI] Alembic 마이그레이션 적용 실패 (계속 진행)")

        logger.info("[FastAPI] DB 연결 및 스키마 초기화 완료")

        # LLM 모델 레지스트리 등록
        try:
            from backend.core.llm.register_models import register_all_models
            register_all_models()
            logger.info("[FastAPI] LLM 모델 레지스트리 등록 완료")
        except Exception as e:
            logger.warning(f"[FastAPI] LLM 모델 레지스트리 등록 실패 (계속 진행): {e}")

        # 중앙 MCP 서버 초기화
        try:
            from backend.domain.admin.hub.mcp import get_central_mcp_server

            central_mcp = get_central_mcp_server()

            if central_mcp:
                logger.info("[FastAPI] 중앙 MCP 서버 초기화 완료 (KoELECTRA + EXAONE)")
        except Exception as e:
            logger.warning(f"[FastAPI] 중앙 MCP 서버 초기화 실패 (계속 진행): {e}")

        # Redis 및 임베딩 워커 초기화
        logger.info("[FastAPI] Redis 및 워커 초기화 시작...")
        print("[FastAPI] Redis 및 워커 초기화 시작...", flush=True)
        try:
            from backend.api.v1.shared.redis import setup_redis, init_redis
            from backend.core.workers.embedding_worker import start_embedding_worker

            # Redis 연결 설정
            logger.info("[FastAPI] Redis 연결 시도 중...")
            print("[FastAPI] Redis 연결 시도 중...", flush=True)
            try:
                redis_result = setup_redis()
                if redis_result:
                    logger.info("[FastAPI] Redis 연결 완료")
                    print("[FastAPI] Redis 연결 완료", flush=True)

                    # 임베딩 워커 시작 (백그라운드 태스크)
                    logger.info("[FastAPI] 워커 시작 시도 중...")
                    print("[FastAPI] 워커 시작 시도 중...", flush=True)
                    try:
                        worker_task = start_embedding_worker()
                        logger.info("[FastAPI] 임베딩 워커 시작 완료")
                        print("[FastAPI] 임베딩 워커 시작 완료", flush=True)
                    except Exception as worker_error:
                        logger.error(f"[FastAPI] 워커 시작 실패 (계속 진행): {worker_error}")
                        print(f"[FastAPI] 워커 시작 실패: {worker_error}", flush=True)
                        import traceback
                        traceback.print_exc()
                else:
                    logger.warning("[FastAPI] Redis 연결 실패 (임베딩 워커 미시작)")
                    print("[FastAPI] Redis 연결 실패 (임베딩 워커 미시작)", flush=True)
            except ValueError as ve:
                # 환경 변수 미설정 등의 경우
                logger.warning(f"[FastAPI] Redis 설정 오류 (임베딩 기능 비활성화): {ve}")
                print(f"[FastAPI] Redis 설정 오류: {ve}", flush=True)
            except Exception as redis_error:
                logger.warning(f"[FastAPI] Redis 연결 오류 (임베딩 기능 비활성화): {redis_error}")
                print(f"[FastAPI] Redis 연결 오류: {redis_error}", flush=True)
                import traceback
                traceback.print_exc()
        except Exception as e:
            logger.error(f"[FastAPI] Redis/워커 초기화 실패 (계속 진행): {e}")
            print(f"[FastAPI] Redis/워커 초기화 실패: {e}", flush=True)
            import traceback
            traceback.print_exc()
            import traceback
            logger.debug(traceback.format_exc())

    except Exception as exc:
        logger.error(f"[FastAPI] DB 초기화 실패: {exc}")
        raise

    yield

    # 종료 시
    # 임베딩 워커 중지
    try:
        from backend.core.workers.embedding_worker import stop_embedding_worker
        stop_embedding_worker()
        logger.info("[FastAPI] 임베딩 워커 중지 완료")
    except Exception as e:
        logger.warning(f"[FastAPI] 워커 중지 실패: {e}")

    # DB 연결 종료
    conn = get_global_db_connection()
    if conn and not conn.closed:
        conn.close()
        logger.info("[FastAPI] DB 연결 종료")


# FastAPI 인스턴스 생성
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    lifespan=lifespan,
)

# 미들웨어 설정 (CORS, 로깅, 에러 처리)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 라우터 등록 (API 엔드포인트 정의)
# 주의:
# - /api/chat → chat_router (종합 라우터, 프론트엔드가 사용하는 엔드포인트)
# - /api/v1/admin/... → 기타 admin용 엔드포인트
api_prefix = "/api/v1/admin"

from backend.api.v1.admin import chat_router, exam_router, mcp_router, user_router, commentary_router, question_router, solving_log_router, mentoring_knowledge_router, study_plan_router, audio_note_router, auth_router

# auth_router는 /api/auth/... 경로를 직접 정의 → prefix 없이 등록
app.include_router(auth_router.router, prefix="")

# chat_router는 내부 prefix("/api")를 그대로 사용 → 최종 경로: /api/chat
app.include_router(chat_router.router, prefix="")

# 기타 admin 라우터들은 /api/v1/admin/... 하위에 위치
app.include_router(exam_router.router, prefix=api_prefix + "/exam")
app.include_router(mcp_router.router, prefix=api_prefix + "/mcp")
app.include_router(user_router.router, prefix=api_prefix + "/users")
app.include_router(commentary_router.router, prefix=api_prefix + "/commentaries")
app.include_router(question_router.router, prefix=api_prefix + "/questions")
app.include_router(solving_log_router.router, prefix=api_prefix + "/solving-logs")
app.include_router(mentoring_knowledge_router.router, prefix=api_prefix + "/mentoring-knowledge")
app.include_router(study_plan_router.router, prefix=api_prefix + "/study-plans")
app.include_router(audio_note_router.router, prefix=api_prefix + "/audio-notes")

# 중앙 MCP 서버를 FastAPI 앱에 마운트
try:
    from backend.domain.admin.hub.mcp import get_central_mcp_server

    central_mcp = get_central_mcp_server()

    if central_mcp:
        # FastMCP 서버는 일반적으로 .app 속성 또는 서버 자체가 ASGI 앱
        # FastMCP의 실제 구조에 따라 조정 필요
        try:
            mcp_server = central_mcp.get_mcp_server()
            # FastMCP 서버가 ASGI 앱을 반환하는 경우
            if hasattr(mcp_server, 'app'):
                app.mount("/mcp/central", mcp_server.app)
            else:
                # 서버 자체가 ASGI 앱인 경우
                app.mount("/mcp/central", mcp_server)
            logger.info("[FastAPI] 중앙 MCP 서버를 /mcp/central에 마운트했습니다.")
        except Exception as e:
            logger.warning(f"[FastAPI] 중앙 MCP 서버 마운트 실패: {e}")

except Exception as e:
    logger.warning(f"[FastAPI] 중앙 MCP 서버 마운트 실패 (계속 진행): {e}")


def main() -> None:
    """앱 진입점."""
    if "--server" in sys.argv:
        # FastAPI 서버 모드
        import uvicorn

        # uvicorn 환경변수 로드 (환경변수가 있으면 우선 사용, 없으면 settings 기본값)
        uvicorn_host = os.getenv("UVICORN_HOST", os.getenv("HOST", settings.HOST))
        uvicorn_port = int(os.getenv("UVICORN_PORT", os.getenv("PORT", str(settings.PORT))))
        uvicorn_log_level = os.getenv("UVICORN_LOG_LEVEL", "info")
        uvicorn_reload = os.getenv("UVICORN_RELOAD", "false").lower() in ("true", "1", "yes")

        logger.info("[FastAPI] 서버 모드로 시작합니다.")
        logger.info(
            f"[FastAPI] uvicorn 설정: host={uvicorn_host}, port={uvicorn_port}, "
            f"log_level={uvicorn_log_level}, reload={uvicorn_reload}"
        )
        uvicorn.run(
            "backend.main:app",
            host=uvicorn_host,
            port=uvicorn_port,
            log_level=uvicorn_log_level,
            reload=uvicorn_reload,
        )


if __name__ == "__main__":
    main()


