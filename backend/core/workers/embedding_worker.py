"""임베딩 작업을 처리하는 BullMQ 워커.

Redis를 통해 BullMQ 큐에서 작업을 가져와 임베딩을 생성하고 저장합니다.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Optional, Dict, Any

import psycopg

from backend.api.v1.shared.redis import (
    get_redis,
    get_bullmq_job,
    update_bullmq_job_status,
    BULLMQ_QUEUE_PREFIX,
    BULLMQ_JOB_PREFIX,
)
from backend.config import settings
from backend.dependencies import get_global_db_connection
from backend.core.utils.embedding import generate_embedding

logger = logging.getLogger(__name__)

# 워커 실행 여부
_worker_running = False
_worker_task: Optional[asyncio.Task] = None

QUEUE_NAME = "embedding_queue"
COMMENTARY_QUEUE_NAME = "commentary_embedding_queue"
BATCH_SIZE = 100  # 한 번에 처리할 문항 수
POLL_INTERVAL = 2  # 큐 폴링 간격 (초) - 더 빠른 처리


async def process_embedding_batch(
    conn: psycopg.Connection,
    batch_size: int = BATCH_SIZE
) -> Dict[str, Any]:
    """임베딩 배치 처리.

    Args:
        conn: 데이터베이스 연결
        batch_size: 배치 크기

    Returns:
        처리 결과
    """
    try:
        # 임베딩이 없는 questions 조회 (exams와 조인하여 subject 가져옴)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT q.id, q.question_text, q.answer_key, e.subject
                FROM questions q
                JOIN exams e ON q.exam_id = e.id
                WHERE q.extra_json IS NOT NULL
                LIMIT %s
            """, (batch_size,))
            rows = cur.fetchall()

        if not rows:
            return {
                "processed_count": 0,
                "total_count": 0,
                "errors": []
            }

        processed_count = 0
        errors = []

        for row in rows:
            try:
                question_id = row[0]
                question_text = row[1] or ""
                answer_key = row[2] or ""
                subject = row[3] or ""

                # 임베딩 생성할 텍스트 구성
                embedding_text = f"{subject} {question_text} 정답: {answer_key}"

                # KURE-v1으로 임베딩 생성
                embedding_vector = generate_embedding(embedding_text)

                # DB에 임베딩 저장 (pgvector 형식: [1.0, 2.0, ...] 문자열)
                embedding_str = "[" + ",".join(map(str, embedding_vector)) + "]"

                # exams 테이블의 exam_vector에 저장 (시험 단위 임베딩)
                # 개별 문제 임베딩은 별도 테이블이 필요하므로, 현재는 로그만 남김
                logger.debug(
                    f"[EmbeddingWorker] 문항 {question_id} 임베딩 생성 완료 "
                    f"(subject={subject}, dim={len(embedding_vector)})"
                )

                conn.commit()
                processed_count += 1

                # 배치 진행 상황 로그 (10개마다 또는 마지막 항목)
                if processed_count % 10 == 0 or processed_count == len(rows):
                    logger.info(
                        f"[EmbeddingWorker] 배치 진행: {processed_count}/{len(rows)}개 처리 완료 "
                        f"(batch_size={batch_size})"
                    )

            except Exception as e:
                error_msg = f"문항 {row[0]} 처리 실패: {str(e)}"
                logger.error(f"[EmbeddingWorker] {error_msg}")
                errors.append({"question_id": row[0], "error": str(e)})
                conn.rollback()

        return {
            "processed_count": processed_count,
            "total_count": len(rows),
            "errors": errors
        }

    except Exception as e:
        logger.error(f"[EmbeddingWorker] 배치 처리 오류: {e}", exc_info=True)
        return {
            "processed_count": 0,
            "total_count": 0,
            "errors": [{"error": str(e)}]
        }


async def process_commentary_embedding_batch(
    conn: psycopg.Connection,
    batch_size: int = BATCH_SIZE
) -> Dict[str, Any]:
    """Commentary 임베딩 배치 처리.

    Args:
        conn: 데이터베이스 연결
        batch_size: 배치 크기

    Returns:
        처리 결과
    """
    try:
        # 임베딩이 없는 commentaries 조회 (questions + exams 조인)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.id, c.body, c.selected, e.subject
                FROM commentaries c
                JOIN questions q ON c.question_id = q.id
                JOIN exams e ON q.exam_id = e.id
                WHERE c.commentary_vector IS NULL
                LIMIT %s
            """, (batch_size,))
            rows = cur.fetchall()

        if not rows:
            return {
                "processed_count": 0,
                "total_count": 0,
                "errors": []
            }

        processed_count = 0
        errors = []

        for row in rows:
            try:
                commentary_id = row[0]
                body = row[1] or ""
                selected = row[2] or ""
                subject = row[3] or ""

                # 임베딩 생성할 텍스트 구성
                embedding_text = f"{subject} 해설: {body} 선택한 답: {selected}"

                # KURE-v1으로 임베딩 생성
                embedding_vector = generate_embedding(embedding_text)

                # DB에 임베딩 저장 (pgvector 형식)
                embedding_str = "[" + ",".join(map(str, embedding_vector)) + "]"

                with conn.cursor() as insert_cur:
                    # commentaries 테이블의 commentary_vector 컬럼에 직접 저장
                    insert_cur.execute("""
                        UPDATE commentaries
                        SET commentary_vector = %s::vector
                        WHERE id = %s
                    """, (embedding_str, commentary_id))

                conn.commit()
                processed_count += 1

                # 배치 진행 상황 로그 (10개마다 또는 마지막 항목)
                if processed_count % 10 == 0 or processed_count == len(rows):
                    logger.info(
                        f"[EmbeddingWorker] Commentary 배치 진행: {processed_count}/{len(rows)}개 처리 완료 "
                        f"(batch_size={batch_size})"
                    )

            except Exception as e:
                error_msg = f"해설 {row[0]} 처리 실패: {str(e)}"
                logger.error(f"[EmbeddingWorker] {error_msg}")
                errors.append({"commentary_id": row[0], "error": str(e)})
                conn.rollback()

        return {
            "processed_count": processed_count,
            "total_count": len(rows),
            "errors": errors
        }

    except Exception as e:
        logger.error(f"[EmbeddingWorker] Commentary 배치 처리 오류: {e}", exc_info=True)
        return {
            "processed_count": 0,
            "total_count": 0,
            "errors": [{"error": str(e)}]
        }


async def process_bullmq_job(job_id: str, queue_name: str = QUEUE_NAME) -> bool:
    """BullMQ 작업 처리.

    Args:
        job_id: 작업 ID

    Returns:
        처리 성공 여부
    """
    try:
        # 작업 정보 조회
        job_data = get_bullmq_job(queue_name, job_id)
        if job_data is None:
            logger.warning(f"[EmbeddingWorker] 작업을 찾을 수 없음: {job_id}")
            return False

        # 작업 상태를 active로 변경
        update_bullmq_job_status(queue_name, job_id, "active")

        # 작업 데이터 추출
        job_payload = job_data.get("data", {})
        batch_size = job_payload.get("batch_size", BATCH_SIZE)
        action = job_payload.get("action", "generate_embeddings")

        logger.info(f"[EmbeddingWorker] 🔄 배치 작업 처리 시작: job_id={job_id}, queue={queue_name}, action={action}, batch_size={batch_size}")
        print(f"[EmbeddingWorker] 🔄 배치 작업 처리 시작: queue={queue_name}, action={action}, batch_size={batch_size}", flush=True)

        # DB 연결
        conn = get_global_db_connection()
        if conn is None or conn.closed:
            logger.error("[EmbeddingWorker] DB 연결이 없습니다.")
            update_bullmq_job_status(
                queue_name,
                job_id,
                "failed",
                {"error": "DB 연결이 없습니다."}
            )
            return False

        # 큐에 따라 다른 배치 처리 함수 호출
        if queue_name == COMMENTARY_QUEUE_NAME or action == "generate_commentary_embeddings":
            result = await process_commentary_embedding_batch(conn, batch_size)
        else:
            result = await process_embedding_batch(conn, batch_size)

        # 작업 상태를 completed로 변경
        update_bullmq_job_status(
            queue_name,
            job_id,
            "completed",
            result
        )

        logger.info(
            f"[EmbeddingWorker] ✅ 배치 작업 처리 완료: job_id={job_id}, queue={queue_name}, "
            f"batch_size={batch_size}, processed={result['processed_count']}, "
            f"total_fetched={result['total_count']}, errors={len(result.get('errors', []))}"
        )
        print(
            f"[EmbeddingWorker] ✅ 배치 작업 처리 완료: queue={queue_name}, batch_size={batch_size}, "
            f"processed={result['processed_count']}개",
            flush=True
        )

        return True

    except Exception as e:
        logger.error(f"[EmbeddingWorker] 작업 처리 오류: {e}", exc_info=True)
        update_bullmq_job_status(
            queue_name,
            job_id,
            "failed",
            {"error": str(e)}
        )
        return False


async def embedding_worker_loop():
    """임베딩 워커 메인 루프.

    Redis 연결이 유효한 동안 계속해서 큐에서 작업을 가져와 처리합니다.
    """
    global _worker_running

    logger.info("[EmbeddingWorker] 워커 시작")
    print("[EmbeddingWorker] 워커 시작", flush=True)
    _worker_running = True

    while _worker_running:
        try:
            # Redis 연결 확인
            redis_client = get_redis()
            try:
                redis_client.ping()
            except Exception as e:
                logger.error(f"[EmbeddingWorker] Redis 연결 실패: {e}")
                await asyncio.sleep(POLL_INTERVAL)
                continue

            # 두 큐 모두 확인 (exam_questions와 commentaries)
            queues_to_check = [
                (QUEUE_NAME, "exam_questions"),
                (COMMENTARY_QUEUE_NAME, "commentaries")
            ]

            job_found = False

            for queue_name, table_name in queues_to_check:
                queue_key = f"{BULLMQ_QUEUE_PREFIX}{queue_name}:wait"

                # 큐 길이 확인 (디버깅용)
                queue_length = redis_client.llen(queue_key)
                if queue_length > 0:
                    logger.info(f"[EmbeddingWorker] {queue_name} 큐에 {queue_length}개 작업 대기 중")
                    print(f"[EmbeddingWorker] {queue_name} 큐에 {queue_length}개 작업 대기 중", flush=True)

                job_id = redis_client.rpop(queue_key)  # FIFO 방식

                if job_id:
                    print(f"[EmbeddingWorker] 📥 {queue_name} 큐에서 작업 가져옴: {job_id}", flush=True)
                    if isinstance(job_id, bytes):
                        job_id = job_id.decode("utf-8")

                    logger.info(f"[EmbeddingWorker] 작업 발견: {job_id} (queue={queue_name})")

                    # 작업 처리
                    success = await process_bullmq_job(job_id, queue_name)

                    # 작업이 완료되었지만 더 처리할 항목이 있으면 새 작업 추가
                    if success:
                        conn = get_global_db_connection()
                        if conn and not conn.closed:
                            with conn.cursor() as cur:
                                if queue_name == COMMENTARY_QUEUE_NAME:
                                    # commentaries 남은 개수 확인 (commentary_vector가 NULL인 것)
                                    cur.execute("""
                                        SELECT COUNT(*)
                                        FROM commentaries c
                                        WHERE c.commentary_vector IS NULL
                                    """)
                                else:
                                    # questions 남은 개수 확인
                                    cur.execute("""
                                        SELECT COUNT(*)
                                        FROM questions q
                                        WHERE q.extra_json IS NOT NULL
                                    """)
                                remaining = cur.fetchone()[0]

                                if remaining > 0:
                                    # 새 작업 추가 (자동으로 다음 배치 처리)
                                    from backend.api.v1.shared.redis import enqueue_bullmq_job
                                    job_payload = get_bullmq_job(queue_name, job_id)
                                    if job_payload:
                                        batch_size = job_payload.get("data", {}).get("batch_size", BATCH_SIZE)
                                        next_batch_size = min(batch_size, remaining)
                                        action = "generate_commentary_embeddings" if queue_name == COMMENTARY_QUEUE_NAME else "generate_embeddings"
                                        enqueue_bullmq_job(
                                            queue_name=queue_name,
                                            job_data={
                                                "action": action,
                                                "batch_size": next_batch_size,
                                                "total_count": remaining
                                            }
                                        )
                                        logger.info(
                                            f"[EmbeddingWorker] 🔄 다음 배치 작업 추가 ({queue_name}): "
                                            f"batch_size={next_batch_size}, remaining={remaining}개"
                                        )
                                        print(
                                            f"[EmbeddingWorker] 🔄 다음 배치 작업 추가 ({queue_name}): "
                                            f"batch_size={next_batch_size}, remaining={remaining}개",
                                            flush=True
                                        )

                    job_found = True
                    break  # 한 번에 하나의 작업만 처리

            if not job_found:
                # 작업이 없으면 대기
                await asyncio.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            logger.info("[EmbeddingWorker] 워커 중지 요청")
            _worker_running = False
            break
        except Exception as e:
            logger.error(f"[EmbeddingWorker] 워커 루프 오류: {e}", exc_info=True)
            await asyncio.sleep(POLL_INTERVAL)

    logger.info("[EmbeddingWorker] 워커 종료")


def start_embedding_worker() -> asyncio.Task:
    """임베딩 워커 시작.

    Returns:
        워커 태스크
    """
    global _worker_task, _worker_running

    if _worker_task is not None and not _worker_task.done():
        logger.warning("[EmbeddingWorker] 워커가 이미 실행 중입니다.")
        return _worker_task

    _worker_running = True
    _worker_task = asyncio.create_task(embedding_worker_loop())
    logger.info("[EmbeddingWorker] 워커 태스크 생성 완료")
    print("[EmbeddingWorker] 워커 태스크 생성 완료", flush=True)

    return _worker_task


def stop_embedding_worker():
    """임베딩 워커 중지."""
    global _worker_running, _worker_task

    logger.info("[EmbeddingWorker] 워커 중지 요청")
    _worker_running = False

    if _worker_task and not _worker_task.done():
        _worker_task.cancel()
        logger.info("[EmbeddingWorker] 워커 태스크 취소 완료")


def is_worker_running() -> bool:
    """워커 실행 여부 확인."""
    return _worker_running and _worker_task is not None and not _worker_task.done()

