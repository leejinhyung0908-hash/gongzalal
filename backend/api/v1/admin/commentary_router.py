"""해설 라우터.

새 테이블 구조:
- Commentaries: question_id FK, body, type, success_period, target_exam, final_score, approved
- Audio_Notes: commentary_id FK, file_path, voice_type, duration
"""

import json
import logging
from typing import List, Dict, Any

import psycopg
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from pydantic import BaseModel, Field

from backend.dependencies import get_db_connection
from backend.domain.admin.models.transfers.commentary_transfer import (
    CommentaryCreateRequest,
    CommentaryResponse,
)
from backend.domain.admin.hub.orchestrators.commentary_flow import CommentaryFlow

router = APIRouter(tags=["commentaries"])

# Orchestrator 인스턴스 (싱글톤 패턴)
_flow = CommentaryFlow()

logger = logging.getLogger(__name__)


@router.post("/", response_model=dict)
async def create_commentary(request: CommentaryCreateRequest) -> dict:
    """해설 생성/갱신 엔드포인트.

    KoELECTRA로 요청을 분석하여 규칙/정책 기반으로 분기 처리:
    - 규칙 기반: 명확한 경우 → commentary_service
    - 정책 기반: 애매한 경우 → commentary_agent

    Args:
        request: 해설 생성/갱신 요청

    Returns:
        처리 결과
    """
    try:
        # 요청 텍스트 생성 (KoELECTRA 분석용)
        request_text = f"해설 생성/갱신 요청: user_id={request.user_id}, question_id={request.question_id}, body={request.body[:100]}"

        # Orchestrator로 요청 처리
        result = await _flow.process_commentary_request(request_text, request.model_dump())

        if not result.get("success", False):
            raise HTTPException(status_code=400, detail=result.get("error", "처리 실패"))

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as exc:
        print(f"[CommentaryRouter] 오류 발생: {exc}", flush=True)
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(exc)}")


@router.get("/by-question/{question_id}", response_model=dict)
async def get_commentary_by_question(
    question_id: int,
    conn: psycopg.Connection = Depends(get_db_connection),
) -> dict:
    """question_id로 해설 조회 엔드포인트.

    해당 문제에 연결된 해설(EXPLANATION 타입)을 반환합니다.

    Args:
        question_id: 문제 ID

    Returns:
        해설 정보 (body 텍스트 포함)
    """
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, question_id, body, type, approved, created_at, updated_at
                FROM commentaries
                WHERE question_id = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (question_id,),
            )
            row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="해당 문제의 해설이 없습니다.")

        return {
            "success": True,
            "commentary": {
                "id": row[0],
                "user_id": row[1],
                "question_id": row[2],
                "body": row[3],
                "type": row[4],
                "approved": row[5],
                "created_at": row[6].isoformat() if row[6] else None,
                "updated_at": row[7].isoformat() if row[7] else None,
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[CommentaryRouter] question_id={question_id} 해설 조회 오류: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(exc)}")


@router.get("/{commentary_id}", response_model=dict)
async def get_commentary(commentary_id: int) -> dict:
    """해설 조회 엔드포인트.

    Args:
        commentary_id: 해설 ID

    Returns:
        해설 정보
    """
    try:
        from backend.domain.admin.spokes.services.commentary_service import CommentaryService

        service = CommentaryService()
        commentary = await service.get_commentary_by_id(commentary_id)

        if not commentary:
            raise HTTPException(status_code=404, detail="해설을 찾을 수 없습니다.")

        return {"success": True, "commentary": commentary}
    except HTTPException:
        raise
    except Exception as exc:
        print(f"[CommentaryRouter] 오류 발생: {exc}", flush=True)
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(exc)}")


@router.post("/upload-jsonl")
async def upload_jsonl_file(
    file: UploadFile = File(...),
) -> dict:
    """해설 JSONL 파일 업로드 엔드포인트.

    all_commentary.jsonl 형식:
    - id, question(해설 본문), answer, subject, source_md, source_pdf

    exams/questions 테이블에 있는 문제와 매칭하여 commentaries 테이블에 삽입합니다.
    """
    print(f"[CommentaryRouter] /upload-jsonl 호출: filename={getattr(file, 'filename', None)}", flush=True)

    try:
        # 파일 확장자 확인
        if not file.filename or not file.filename.endswith(".jsonl"):
            raise HTTPException(status_code=400, detail="JSONL 파일만 업로드할 수 있습니다.")

        # 파일 내용 읽기 & 파싱
        contents = await file.read()
        text = contents.decode("utf-8")
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        all_parsed_data: List[Dict[str, Any]] = []
        parse_errors: List[Dict[str, Any]] = []

        for i, line in enumerate(lines, start=1):
            try:
                item = json.loads(line)
                all_parsed_data.append({"line_number": i, "data": item})
            except json.JSONDecodeError as e:
                parse_errors.append({"line": i, "error": str(e)})

        logger.info(
            f"[CommentaryRouter] 파싱 완료: {len(all_parsed_data)}개 항목, {len(parse_errors)}개 오류"
        )

        # CommentaryFlow로 데이터 전달 (DB 삽입)
        jsonl_data = [item["data"] for item in all_parsed_data]
        flow_result = await _flow.process_jsonl_data(
            jsonl_data=jsonl_data,
            category="commentary",
            filename=file.filename or "unknown.jsonl",
        )

        # 응답 생성
        inserted = flow_result.get("inserted_count", 0) if isinstance(flow_result, dict) else 0
        skipped = flow_result.get("skipped_count", 0) if isinstance(flow_result, dict) else 0
        conversion_errors = flow_result.get("conversion_errors", []) if isinstance(flow_result, dict) else []
        insertion_errors = flow_result.get("insertion_errors", []) if isinstance(flow_result, dict) else []

        return {
            "success": bool(flow_result.get("success")) if isinstance(flow_result, dict) else False,
            "filename": file.filename,
            "category": "commentary",
            "total_lines": len(lines),
            "parsed_items": len(all_parsed_data),
            "inserted_count": inserted,
            "skipped_count": skipped,
            "message": flow_result.get("message", "") if isinstance(flow_result, dict) else "처리 실패",
            "errors": parse_errors or None,
            "conversion_errors": conversion_errors[:10] if conversion_errors else None,
            "insertion_errors": insertion_errors[:10] if insertion_errors else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CommentaryRouter] 파일 업로드 오류: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"파일 처리 중 오류가 발생했습니다: {str(e)}",
        )


class CommentaryEmbeddingEnqueueRequest(BaseModel):
    """해설 임베딩 작업 큐 추가 요청."""
    batch_size: int = Field(default=100, ge=1, le=1000, description="배치 크기")


@router.post("/enqueue-embeddings")
async def enqueue_commentary_embeddings(
    request: CommentaryEmbeddingEnqueueRequest = CommentaryEmbeddingEnqueueRequest(),
    conn: psycopg.Connection = Depends(get_db_connection)
) -> dict:
    """해설 임베딩 작업을 BullMQ 큐에 추가하는 엔드포인트.

    Args:
        request: 임베딩 작업 큐 추가 요청 (배치 크기 포함)
        conn: 데이터베이스 연결

    Returns:
        작업 큐 추가 결과 또는 직접 처리 결과
    """
    try:
        logger.info("[CommentaryRouter] 해설 임베딩 작업 큐 추가 요청 수신")
        print("[CommentaryRouter] >>> /enqueue-embeddings 호출됨", flush=True)

        # 임베딩이 필요한 해설 수 확인 (commentary_vector가 NULL인 것)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*)
                FROM commentaries
                WHERE commentary_vector IS NULL
            """)
            total_count = cur.fetchone()[0]

        if total_count == 0:
            return {
                "success": True,
                "message": "임베딩이 필요한 해설이 없습니다.",
                "processed_count": 0,
                "total_count": 0,
                "mode": "none"
            }

        # BullMQ에 작업 추가 (Redis가 설정되어 있는 경우)
        try:
            from backend.api.v1.shared.redis import enqueue_bullmq_job, get_redis, is_redis_available

            if is_redis_available():
                logger.info("[CommentaryRouter] Redis 연결 성공, BullMQ 큐에 작업 추가 중...")
                redis_client = get_redis()
                redis_client.ping()

                job_id = enqueue_bullmq_job(
                    queue_name="commentary_embedding_queue",
                    job_data={
                        "action": "generate_commentary_embeddings",
                        "batch_size": request.batch_size,
                        "total_count": total_count
                    }
                )

                if job_id:
                    logger.info(f"[CommentaryRouter] ✅ Redis/BullMQ를 통해 해설 임베딩 작업 큐 추가 완료: job_id={job_id}")
                    return {
                        "success": True,
                        "message": f"해설 임베딩 작업이 큐에 추가되었습니다. (총 {total_count}개 해설, Redis/BullMQ 사용)",
                        "job_id": job_id,
                        "total_count": total_count,
                        "mode": "redis_bullmq"
                    }
                else:
                    raise HTTPException(
                        status_code=500,
                        detail="작업 큐 추가에 실패했습니다."
                    )
            else:
                raise ValueError("Redis 사용 불가")
        except (ValueError, ImportError, Exception) as redis_error:
            # Redis가 설정되지 않았거나 연결 실패 시 직접 처리
            logger.warning(f"[CommentaryRouter] ⚠️ Redis 사용 불가, 직접 처리 모드로 전환: {redis_error}")

            # KURE-v1으로 직접 임베딩 생성 (동기 처리)
            from backend.core.utils.embedding import generate_embedding

            processed_count = 0
            errors = []

            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, body, type
                    FROM commentaries
                    WHERE commentary_vector IS NULL
                    LIMIT %s
                """, (request.batch_size,))
                rows = cur.fetchall()

            for row in rows:
                try:
                    commentary_id = row[0]
                    body = row[1] or ""
                    commentary_type = row[2] or ""

                    # 임베딩 생성할 텍스트 구성
                    embedding_text = f"{body}"
                    if commentary_type:
                        embedding_text += f" 유형: {commentary_type}"

                    embedding_vector = generate_embedding(embedding_text)
                    embedding_str = "[" + ",".join(map(str, embedding_vector)) + "]"

                    with conn.cursor() as update_cur:
                        update_cur.execute("""
                            UPDATE commentaries
                            SET commentary_vector = %s::vector,
                                updated_at = now()
                            WHERE id = %s
                        """, (embedding_str, commentary_id))

                    conn.commit()
                    processed_count += 1
                    logger.info(f"[CommentaryRouter] 해설 {commentary_id} 임베딩 생성 완료")

                except Exception as e:
                    error_msg = f"해설 {row[0]} 처리 실패: {str(e)}"
                    logger.error(f"[CommentaryRouter] {error_msg}")
                    errors.append({"commentary_id": row[0], "error": str(e)})
                    conn.rollback()

            logger.info(f"[CommentaryRouter] ✅ 직접 처리 모드로 {processed_count}개 해설 임베딩 생성 완료")
            return {
                "success": True,
                "message": f"{processed_count}개 해설의 임베딩을 생성했습니다. (Redis 미사용, 직접 처리)",
                "processed_count": processed_count,
                "total_count": len(rows),
                "errors": errors if errors else None,
                "mode": "direct"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CommentaryRouter] 해설 임베딩 작업 큐 추가 오류: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"해설 임베딩 작업 큐 추가 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/embedding-status")
async def get_commentary_embedding_status(
    conn: psycopg.Connection = Depends(get_db_connection)
) -> dict:
    """해설 임베딩 작업 상태 조회 엔드포인트.

    Returns:
        해설 임베딩 작업 상태
    """
    try:
        # 임베딩이 필요한 해설 수
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*)
                FROM commentaries
                WHERE commentary_vector IS NULL
            """)
            remaining_count = cur.fetchone()[0]

            # 전체 해설 수
            cur.execute("SELECT COUNT(*) FROM commentaries")
            total_count = cur.fetchone()[0]

            # 임베딩 완료 해설 수
            cur.execute("""
                SELECT COUNT(*)
                FROM commentaries
                WHERE commentary_vector IS NOT NULL
            """)
            processed_count = cur.fetchone()[0]

        is_complete = remaining_count == 0

        return {
            "is_complete": is_complete,
            "processed_count": processed_count,
            "total_count": total_count,
            "remaining_count": remaining_count,
            "message": "완료" if is_complete else f"{remaining_count}개 해설 남음"
        }

    except Exception as e:
        logger.error(f"[CommentaryRouter] 상태 조회 오류: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"상태 조회 중 오류가 발생했습니다: {str(e)}"
        )
