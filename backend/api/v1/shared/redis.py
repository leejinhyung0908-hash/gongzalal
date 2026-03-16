"""Upstash Redis 클라이언트 및 JWT/BullMQ 통신 설정.

Upstash Redis를 사용하여 JWT access token을 저장하고,
BullMQ와 통신할 수 있도록 설정합니다.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone

from upstash_redis import Redis

from backend.config import settings

logger = logging.getLogger(__name__)

# Upstash Redis 클라이언트 초기화
redis: Optional[Redis] = None


def init_redis() -> Redis:
    """Upstash Redis 클라이언트 초기화."""
    global redis

    if redis is not None:
        return redis

    if not settings.UPSTASH_REDIS_REST_URL or not settings.UPSTASH_REDIS_REST_TOKEN:
        raise ValueError(
            "UPSTASH_REDIS_REST_URL과 UPSTASH_REDIS_REST_TOKEN 환경 변수가 설정되지 않았습니다."
        )

    redis = Redis(
        url=settings.UPSTASH_REDIS_REST_URL,
        token=settings.UPSTASH_REDIS_REST_TOKEN
    )

    # 연결 테스트
    try:
        redis.ping()
        logger.info("[Redis] Upstash Redis 연결 성공")
    except Exception as e:
        logger.error(f"[Redis] Upstash Redis 연결 실패: {e}")
        raise

    return redis


def get_redis() -> Redis:
    """Redis 클라이언트 인스턴스 반환."""
    if redis is None:
        return init_redis()
    return redis


def is_redis_available() -> bool:
    """Redis 클라이언트가 사용 가능한지 확인.

    Returns:
        Redis가 초기화되어 있고 연결 가능하면 True, 아니면 False
    """
    try:
        if redis is None:
            # 환경 변수 확인
            if not settings.UPSTASH_REDIS_REST_URL or not settings.UPSTASH_REDIS_REST_TOKEN:
                return False
            # 초기화 시도
            try:
                init_redis()
            except Exception:
                return False

        # 연결 테스트
        redis.ping()
        return True
    except Exception as e:
        logger.debug(f"[Redis] Redis 사용 불가: {e}")
        return False


# JWT 토큰 관련 Redis 키 패턴 (Access Token만 Redis에 저장)
JWT_TOKEN_PREFIX = "jwt:access_token:"
JWT_USER_PREFIX = "jwt:user:"

# BullMQ 관련 Redis 키 패턴
BULLMQ_QUEUE_PREFIX = "bull:"
BULLMQ_JOB_PREFIX = "bullmq:job:"
EMBEDDING_QUEUES = {"embedding_queue", "commentary_embedding_queue"}


def _ensure_embedding_worker_running(queue_name: str) -> None:
    """임베딩 큐 작업이 enqueue되면 워커를 on-demand로 시작한다."""
    if queue_name not in EMBEDDING_QUEUES:
        return

    # 실행 중 이벤트 루프가 없는 컨텍스트에서는 워커 시작을 건너뛴다.
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        logger.debug("[Redis] 이벤트 루프 없음 - 워커 자동 시작 건너뜀")
        return

    try:
        # 순환 참조를 피하기 위해 지연 import
        from backend.core.workers.embedding_worker import is_worker_running, start_embedding_worker

        if not is_worker_running():
            start_embedding_worker()
            logger.info(f"[Redis] 임베딩 워커 on-demand 시작: queue={queue_name}")
    except Exception as e:
        # enqueue 자체는 성공했으므로 warning으로만 남긴다.
        logger.warning(f"[Redis] 워커 on-demand 시작 실패 (queue={queue_name}): {e}")


def store_jwt_token(user_id: str, access_token: str, expires_in: int = 1800) -> bool:
    """JWT access token을 Redis에 저장. (Refresh token은 Neon DB에 저장)

    Args:
        user_id: 사용자 ID
        access_token: JWT access token
        expires_in: 토큰 만료 시간 (초, 기본값: 30분)

    Returns:
        저장 성공 여부
    """
    try:
        redis_client = get_redis()

        # Access token 저장 (토큰을 키로 사용)
        token_key = f"{JWT_TOKEN_PREFIX}{access_token}"
        token_data = {
            "user_id": user_id,
            "token": access_token,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()
        }
        redis_client.setex(
            token_key,
            expires_in,
            json.dumps(token_data)
        )

        # 사용자별 토큰 매핑 저장 (사용자 ID를 키로 사용)
        user_key = f"{JWT_USER_PREFIX}{user_id}"
        redis_client.setex(
            user_key,
            expires_in,
            access_token
        )

        logger.info(f"[Redis] JWT access token 저장 완료: user_id={user_id}")
        return True

    except Exception as e:
        logger.error(f"[Redis] JWT access token 저장 실패: {e}")
        return False


def get_jwt_token(access_token: str) -> Optional[Dict[str, Any]]:
    """JWT access token 정보 조회.

    Args:
        access_token: JWT access token

    Returns:
        토큰 정보 (user_id, token, created_at, expires_at) 또는 None
    """
    try:
        redis_client = get_redis()
        token_key = f"{JWT_TOKEN_PREFIX}{access_token}"
        token_data = redis_client.get(token_key)

        if token_data is None:
            return None

        if isinstance(token_data, bytes):
            token_data = token_data.decode("utf-8")

        return json.loads(token_data)

    except Exception as e:
        logger.error(f"[Redis] JWT 토큰 조회 실패: {e}")
        return None


def get_user_token(user_id: str) -> Optional[str]:
    """사용자 ID로 access token 조회.

    Args:
        user_id: 사용자 ID

    Returns:
        access token 또는 None
    """
    try:
        redis_client = get_redis()
        user_key = f"{JWT_USER_PREFIX}{user_id}"
        token = redis_client.get(user_key)

        if token is None:
            return None

        if isinstance(token, bytes):
            token = token.decode("utf-8")

        return token

    except Exception as e:
        logger.error(f"[Redis] 사용자 토큰 조회 실패: {e}")
        return None


def delete_jwt_token(access_token: str) -> bool:
    """JWT access token 삭제 (로그아웃).

    Args:
        access_token: JWT access token

    Returns:
        삭제 성공 여부
    """
    try:
        redis_client = get_redis()

        # 토큰 정보 조회
        token_data = get_jwt_token(access_token)
        if token_data:
            user_id = token_data.get("user_id")

            # 토큰 삭제
            token_key = f"{JWT_TOKEN_PREFIX}{access_token}"
            redis_client.delete(token_key)

            # 사용자 매핑 삭제
            if user_id:
                user_key = f"{JWT_USER_PREFIX}{user_id}"
                redis_client.delete(user_key)

        logger.info(f"[Redis] JWT 토큰 삭제 완료")
        return True

    except Exception as e:
        logger.error(f"[Redis] JWT 토큰 삭제 실패: {e}")
        return False


def verify_jwt_token(access_token: str) -> Optional[Dict[str, Any]]:
    """JWT access token 검증.

    Args:
        access_token: JWT access token

    Returns:
        검증된 토큰 정보 또는 None
    """
    token_data = get_jwt_token(access_token)

    if token_data is None:
        return None

    # 만료 시간 확인
    expires_at_str = token_data.get("expires_at")
    if expires_at_str:
        expires_at = datetime.fromisoformat(expires_at_str)
        if datetime.now(timezone.utc) > expires_at:
            # 만료된 토큰 삭제
            delete_jwt_token(access_token)
            return None

    return token_data


# BullMQ 통신 관련 함수들
def enqueue_bullmq_job(
    queue_name: str,
    job_data: Dict[str, Any],
    job_id: Optional[str] = None,
    delay: int = 0
) -> Optional[str]:
    """BullMQ에 작업 추가.

    Args:
        queue_name: 큐 이름
        job_data: 작업 데이터
        job_id: 작업 ID (선택, 없으면 자동 생성)
        delay: 지연 시간 (초)

    Returns:
        작업 ID 또는 None
    """
    try:
        redis_client = get_redis()

        if job_id is None:
            import uuid
            job_id = str(uuid.uuid4())

        # BullMQ 작업 데이터 구조
        job_key = f"{BULLMQ_JOB_PREFIX}{queue_name}:{job_id}"
        job_payload = {
            "id": job_id,
            "name": queue_name,
            "data": job_data,
            "opts": {
                "delay": delay * 1000 if delay > 0 else 0,  # BullMQ는 밀리초 단위
                "attempts": 3,
                "backoff": {
                    "type": "exponential",
                    "delay": 2000
                }
            },
            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            "processedOn": None,
            "finishedOn": None
        }

        # 작업 저장
        redis_client.set(
            job_key,
            json.dumps(job_payload)
        )

        # 큐에 작업 추가 (BullMQ 형식)
        queue_key = f"{BULLMQ_QUEUE_PREFIX}{queue_name}:wait"
        redis_client.lpush(queue_key, job_id)
        _ensure_embedding_worker_running(queue_name)

        logger.info(f"[Redis] BullMQ 작업 추가: queue={queue_name}, job_id={job_id}")
        return job_id

    except Exception as e:
        logger.error(f"[Redis] BullMQ 작업 추가 실패: {e}")
        return None


def get_bullmq_job(queue_name: str, job_id: str) -> Optional[Dict[str, Any]]:
    """BullMQ 작업 조회.

    Args:
        queue_name: 큐 이름
        job_id: 작업 ID

    Returns:
        작업 데이터 또는 None
    """
    try:
        redis_client = get_redis()
        job_key = f"{BULLMQ_JOB_PREFIX}{queue_name}:{job_id}"
        job_data = redis_client.get(job_key)

        if job_data is None:
            return None

        if isinstance(job_data, bytes):
            job_data = job_data.decode("utf-8")

        return json.loads(job_data)

    except Exception as e:
        logger.error(f"[Redis] BullMQ 작업 조회 실패: {e}")
        return None


def update_bullmq_job_status(
    queue_name: str,
    job_id: str,
    status: str,
    result: Optional[Dict[str, Any]] = None
) -> bool:
    """BullMQ 작업 상태 업데이트.

    Args:
        queue_name: 큐 이름
        job_id: 작업 ID
        status: 상태 ("active", "completed", "failed")
        result: 작업 결과 (선택)

    Returns:
        업데이트 성공 여부
    """
    try:
        redis_client = get_redis()
        job_key = f"{BULLMQ_JOB_PREFIX}{queue_name}:{job_id}"

        job_data = get_bullmq_job(queue_name, job_id)
        if job_data is None:
            return False

        # 상태 업데이트
        job_data["status"] = status
        if status == "completed":
            job_data["finishedOn"] = int(datetime.now(timezone.utc).timestamp() * 1000)
            if result:
                job_data["returnvalue"] = result
        elif status == "failed":
            job_data["failedReason"] = result.get("error", "Unknown error") if result else "Unknown error"

        redis_client.set(
            job_key,
            json.dumps(job_data)
        )

        # 큐에서 이동 (wait -> active -> completed/failed)
        if status == "active":
            wait_key = f"{BULLMQ_QUEUE_PREFIX}{queue_name}:wait"
            active_key = f"{BULLMQ_QUEUE_PREFIX}{queue_name}:active"
            redis_client.lrem(wait_key, 1, job_id)
            redis_client.lpush(active_key, job_id)
        elif status in ("completed", "failed"):
            active_key = f"{BULLMQ_QUEUE_PREFIX}{queue_name}:active"
            redis_client.lrem(active_key, 1, job_id)

        logger.info(f"[Redis] BullMQ 작업 상태 업데이트: queue={queue_name}, job_id={job_id}, status={status}")
        return True

    except Exception as e:
        logger.error(f"[Redis] BullMQ 작업 상태 업데이트 실패: {e}")
        return False


# ═══════════════════════════════════════════════════
# 대화 이력 (Chat History) 관련 함수
# ═══════════════════════════════════════════════════

CHAT_HISTORY_PREFIX = "chat:session:"
CHAT_HISTORY_TTL = 1800  # 30분 (대화가 이어지면 갱신)
CHAT_MAX_MESSAGES = 20   # 최대 보관 메시지 수 (오래된 것부터 제거)


def store_chat_message(
    session_id: str,
    role: str,
    text: str,
) -> bool:
    """대화 메시지를 Redis에 추가합니다.

    Args:
        session_id: 대화 세션 ID (thread_id)
        role: "user" 또는 "bot"
        text: 메시지 내용

    Returns:
        저장 성공 여부
    """
    try:
        redis_client = get_redis()
        key = f"{CHAT_HISTORY_PREFIX}{session_id}"

        # 기존 이력 로드
        raw = redis_client.get(key)
        if raw:
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            data = json.loads(raw)
        else:
            data = {"session_id": session_id, "messages": [], "context_summary": ""}

        # 새 메시지 추가
        data["messages"].append({
            "role": role,
            "text": text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # 최대 메시지 수 제한 (오래된 것부터 제거)
        if len(data["messages"]) > CHAT_MAX_MESSAGES:
            data["messages"] = data["messages"][-CHAT_MAX_MESSAGES:]

        # 저장 (TTL 갱신)
        redis_client.setex(key, CHAT_HISTORY_TTL, json.dumps(data, ensure_ascii=False))
        logger.debug(f"[Redis] 대화 메시지 저장: session={session_id}, role={role}")
        return True

    except Exception as e:
        logger.error(f"[Redis] 대화 메시지 저장 실패: {e}")
        return False


def get_chat_history(session_id: str) -> Dict[str, Any]:
    """대화 이력을 Redis에서 조회합니다.

    Args:
        session_id: 대화 세션 ID (thread_id)

    Returns:
        { session_id, messages: [...], context_summary: str }
        세션이 없으면 빈 구조를 반환합니다.
    """
    try:
        redis_client = get_redis()
        key = f"{CHAT_HISTORY_PREFIX}{session_id}"
        raw = redis_client.get(key)

        if raw is None:
            return {"session_id": session_id, "messages": [], "context_summary": ""}

        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")

        data = json.loads(raw)
        logger.debug(
            f"[Redis] 대화 이력 조회: session={session_id}, "
            f"messages={len(data.get('messages', []))}건"
        )
        return data

    except Exception as e:
        logger.error(f"[Redis] 대화 이력 조회 실패: {e}")
        return {"session_id": session_id, "messages": [], "context_summary": ""}


def update_context_summary(session_id: str, summary: str) -> bool:
    """대화 맥락 요약을 갱신합니다.

    Args:
        session_id: 대화 세션 ID
        summary: 새 맥락 요약 문자열

    Returns:
        갱신 성공 여부
    """
    try:
        redis_client = get_redis()
        key = f"{CHAT_HISTORY_PREFIX}{session_id}"
        raw = redis_client.get(key)

        if raw is None:
            data = {"session_id": session_id, "messages": [], "context_summary": summary}
        else:
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            data = json.loads(raw)
            data["context_summary"] = summary

        redis_client.setex(key, CHAT_HISTORY_TTL, json.dumps(data, ensure_ascii=False))
        logger.debug(f"[Redis] 맥락 요약 갱신: session={session_id}")
        return True

    except Exception as e:
        logger.error(f"[Redis] 맥락 요약 갱신 실패: {e}")
        return False


# ═══════════════════════════════════════════════════
# 초기화
# ═══════════════════════════════════════════════════

# 초기화 함수 (애플리케이션 시작 시 호출)
def setup_redis() -> bool:
    """Redis 초기화 및 연결 테스트."""
    try:
        init_redis()
        logger.info("[Redis] Redis 설정 완료")
        return True
    except Exception as e:
        logger.error(f"[Redis] Redis 설정 실패: {e}")
        return False

