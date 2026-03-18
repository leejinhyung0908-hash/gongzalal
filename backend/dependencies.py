"""FastAPI 의존성 주입."""
import time
from typing import Generator

import psycopg
from fastapi import HTTPException
from pgvector.psycopg import register_vector
from langchain_postgres import PGEngine

from backend.config import settings

# 전역 DB 연결
_db_conn: psycopg.Connection | None = None
_pg_engine: PGEngine | None = None


def connect_db(
    database_url: str, *, retries: int = 20, delay: float = 0.5
) -> psycopg.Connection:
    """Postgres에 접속한다. 아직 기동 중이면 재시도한다."""

    dsn = database_url.replace("postgresql+psycopg://", "postgresql://")

    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            conn = psycopg.connect(
                dsn,
                autocommit=True,
                # TCP keepalive: LLM 생성(60s+) 동안 Neon DB idle timeout 방지
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5,
            )
            return conn
        except psycopg.OperationalError as exc:
            last_err = exc
            print(
                f"[DB] 연결 실패 (시도 {attempt}/{retries}): {exc}. "
                f"{delay}초 후 재시도합니다.",
                flush=True,
            )
            time.sleep(delay)

    msg = "[DB] 최대 재시도 횟수 초과로 Postgres에 접속하지 못했습니다."
    print(msg, flush=True)
    if last_err is not None:
        raise last_err
    raise RuntimeError(msg)


def setup_schema(conn: psycopg.Connection) -> None:
    """스키마 자동 생성(DDL)을 하지 않는다.

    요구사항: 쿼리문 없이 “자동완성 시스템”을 구축하기 위해,
    애플리케이션 코드에서 CREATE/ALTER 같은 DDL 실행을 제거했다.

    주의: 아래 테이블/확장은 DB(Neon)에서 미리 생성되어 있어야 한다.
    - EXTENSION: vector
    - TABLES: documents, exam_questions, users, commentaries, user_exam
    """

    # pgvector Python 어댑터 등록(선택). DDL 없이도 수행 가능.
    try:
        register_vector(conn)
    except Exception as exc:
        print(f"[DB] pgvector register_vector 실패(무시): {exc}", flush=True)
        return


def get_db_connection() -> psycopg.Connection:
    """전역 DB 연결을 반환하거나 새로 생성한다.

    LLM 생성처럼 장시간 처리 후 Neon DB가 SSL 연결을 끊을 수 있으므로
    SELECT 1로 연결 상태를 확인하고 죽어있으면 재연결한다.
    """
    global _db_conn

    def _reconnect() -> None:
        global _db_conn
        _db_conn = connect_db(settings.DATABASE_URL)
        setup_schema(_db_conn)

    if _db_conn is None or _db_conn.closed:
        try:
            _reconnect()
        except Exception as exc:
            print(f"[DB] 연결 오류: {exc}", flush=True)
            raise HTTPException(
                status_code=503, detail=f"데이터베이스 연결 실패: {str(exc)}"
            )
    else:
        # 연결이 살아있는지 확인 (Neon idle timeout 대응)
        try:
            with _db_conn.cursor() as cur:
                cur.execute("SELECT 1")
        except Exception as exc:
            print(f"[DB] 연결 유효성 실패, 재연결: {exc}", flush=True)
            try:
                _reconnect()
            except Exception as exc2:
                raise HTTPException(
                    status_code=503, detail=f"데이터베이스 재연결 실패: {str(exc2)}"
                )
    return _db_conn


def get_global_db_connection() -> psycopg.Connection | None:
    """전역 DB 연결을 반환 (헬스 체크용)."""
    global _db_conn
    return _db_conn


def get_pg_engine() -> PGEngine:
    """LangChain PGEngine 인스턴스를 반환한다.

    환경 변수 `PGENGINE_URL` (또는 기본값)을 사용해
    `postgresql+asyncpg://USER:PASSWORD@HOST:5432/DBNAME`
    형식의 연결 문자열로 초기화한다.
    """
    global _pg_engine
    if _pg_engine is None:
        try:
            _pg_engine = PGEngine.from_connection_string(url=settings.PGENGINE_URL)
        except Exception as exc:
            print(f"[PGEngine] 초기화 오류: {exc}", flush=True)
            raise HTTPException(
                status_code=503, detail=f"PGEngine 초기화 실패: {str(exc)}"
            )
    return _pg_engine


# LLM 의존성 주입
def get_llm(
    model_name: str | None = None,
    model_type: str | None = None,
):
    """LLM 인스턴스를 반환하는 의존성 함수.

    Args:
        model_name: 모델 이름 (기본값: 설정에서 가져옴)
        model_type: 모델 타입 (기본값: 설정에서 가져옴)

    Returns:
        LLM 인스턴스
    """
    from backend.config import settings
    from backend.core.llm.loader import get_loader

    loader = get_loader()
    model_name = model_name or settings.DEFAULT_MODEL_NAME
    model_type = model_type or settings.DEFAULT_MODEL_TYPE

    if not model_name:
        raise ValueError("모델 이름이 지정되지 않았습니다.")

    return loader.load_model(model_name=model_name, model_type=model_type)


# QLoRA 서비스 전역 인스턴스
_qlora_service: "QLoRAChatService | None" = None


def get_qlora_service() -> "QLoRAChatService":
    """QLoRA 채팅 서비스 인스턴스를 반환하는 의존성 함수.

    전역 싱글톤으로 관리하여 모델을 한 번만 로드합니다.

    Returns:
        QLoRAChatService 인스턴스
    """
    global _qlora_service
    if _qlora_service is None:
        from backend.domain.admin.agents.conversation import QLoRAChatService
        import os

        # 환경 변수에서 설정 가져오기
        lora_adapter_path = os.getenv("LORA_ADAPTER_PATH", None)

        # 양자화 설정: 환경 변수가 명시적으로 설정되어 있으면 우선 사용, 없으면 기본값 true
        import platform
        is_windows = platform.system() == "Windows"

        # 환경 변수가 명시적으로 설정되어 있는지 확인
        load_in_4bit_env = os.getenv("LOAD_IN_4BIT")
        load_in_8bit_env = os.getenv("LOAD_IN_8BIT")

        if load_in_4bit_env is not None:
            # 환경 변수가 명시적으로 설정된 경우
            load_in_4bit = load_in_4bit_env.lower() == "true"
        else:
            # 환경 변수가 없으면 기본값으로 true 사용 (양자화 활성화)
            load_in_4bit = True

        if load_in_8bit_env is not None:
            load_in_8bit = load_in_8bit_env.lower() == "true"
        else:
            load_in_8bit = False

        # 4-bit와 8-bit가 동시에 활성화되면 4-bit 우선
        if load_in_4bit and load_in_8bit:
            print("[dependencies] 4-bit와 8-bit 양자화가 동시에 활성화되어 있습니다. 4-bit를 사용합니다.", flush=True)
            load_in_8bit = False

        print(f"[dependencies] 양자화 설정: 4-bit={load_in_4bit}, 8-bit={load_in_8bit}", flush=True)
        if is_windows and (load_in_4bit or load_in_8bit):
            print("[dependencies] Windows 환경 감지: 양자화 시도 중... (실패 시 자동으로 폴백됩니다)", flush=True)

        _qlora_service = QLoRAChatService(
            lora_adapter_path=lora_adapter_path,
            load_in_4bit=load_in_4bit,
            load_in_8bit=load_in_8bit,
        )
        print("[dependencies] QLoRA 서비스 초기화 완료", flush=True)

    return _qlora_service

