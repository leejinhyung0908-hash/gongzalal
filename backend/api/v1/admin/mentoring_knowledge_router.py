"""멘토링 지식(MentoringKnowledge) 라우터.

merged_training_data.jsonl을 업로드하여 mentoring_knowledge 테이블에 삽입하고,
RAG 검색 및 학습 계획 생성 서비스를 제공합니다.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import psycopg
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from backend.dependencies import get_db_connection

router = APIRouter(tags=["mentoring-knowledge"])
logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic 스키마
# ============================================================================

class MentoringKnowledgeResponse(BaseModel):
    """멘토링 지식 단건 응답."""
    id: int
    instruction: str
    question: str
    intent: Optional[str] = None
    context: str
    thought_process: Optional[str] = None
    response: str
    created_at: Optional[str] = None


class MentoringKnowledgeSearchRequest(BaseModel):
    """RAG 검색 요청."""
    query: str = Field(..., description="검색 질문")
    top_k: int = Field(default=5, ge=1, le=20, description="반환할 결과 수")
    intent_filter: Optional[str] = Field(default=None, description="의도 필터 (예: ADVICE)")


# ============================================================================
# JSONL 업로드
# ============================================================================

@router.post("/upload-jsonl")
async def upload_mentoring_jsonl(
    file: UploadFile = File(...),
    conn: psycopg.Connection = Depends(get_db_connection),
) -> dict:
    """merged_training_data.jsonl 업로드 엔드포인트.

    JSONL 형식:
    {
      "instruction": "...",
      "input": {
        "question": "...",
        "intent": "ADVICE",
        "context": "합격자 수기: ..."
      },
      "output": {
        "thought_process": "...",
        "response": "..."
      }
    }
    """
    logger.info(f"[MentoringKnowledge] /upload-jsonl 호출: filename={getattr(file, 'filename', None)}")

    if not file.filename or not file.filename.endswith(".jsonl"):
        raise HTTPException(status_code=400, detail="JSONL 파일만 업로드할 수 있습니다.")

    try:
        contents = await file.read()
        text = contents.decode("utf-8")
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        inserted_count = 0
        skipped_count = 0
        errors: List[Dict[str, Any]] = []

        with conn.cursor() as cur:
            for i, line in enumerate(lines, start=1):
                try:
                    item = json.loads(line)

                    # 필드 추출
                    instruction = item.get("instruction", "")
                    input_data = item.get("input", {})
                    output_data = item.get("output", {})

                    question = input_data.get("question", "") if isinstance(input_data, dict) else str(input_data)
                    intent = input_data.get("intent", None) if isinstance(input_data, dict) else None
                    context = input_data.get("context", "") if isinstance(input_data, dict) else ""
                    thought_process = output_data.get("thought_process", None) if isinstance(output_data, dict) else None
                    response = output_data.get("response", "") if isinstance(output_data, dict) else str(output_data)

                    if not question or not response:
                        skipped_count += 1
                        errors.append({"line": i, "error": "question 또는 response가 비어 있습니다."})
                        continue

                    cur.execute(
                        """
                        INSERT INTO mentoring_knowledge
                            (instruction, question, intent, context, thought_process, response)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (instruction, question, intent, context, thought_process, response),
                    )
                    inserted_count += 1

                except json.JSONDecodeError as e:
                    skipped_count += 1
                    errors.append({"line": i, "error": f"JSON 파싱 오류: {str(e)}"})
                except Exception as e:
                    skipped_count += 1
                    errors.append({"line": i, "error": str(e)})

        logger.info(
            f"[MentoringKnowledge] 업로드 완료: {inserted_count}건 삽입, {skipped_count}건 스킵"
        )

        return {
            "success": True,
            "filename": file.filename,
            "total_lines": len(lines),
            "inserted_count": inserted_count,
            "skipped_count": skipped_count,
            "errors": errors[:10] if errors else None,
            "message": f"{inserted_count}건의 멘토링 지식이 저장되었습니다.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MentoringKnowledge] 업로드 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"파일 처리 중 오류: {str(e)}")


# ============================================================================
# 조회 엔드포인트
# ============================================================================

@router.get("/", response_model=dict)
async def list_mentoring_knowledge(
    page: int = Query(default=1, ge=1, description="페이지 번호"),
    size: int = Query(default=20, ge=1, le=100, description="페이지 크기"),
    intent: Optional[str] = Query(default=None, description="의도 필터"),
    conn: psycopg.Connection = Depends(get_db_connection),
) -> dict:
    """멘토링 지식 목록 조회."""
    offset = (page - 1) * size

    with conn.cursor() as cur:
        # 총 개수
        if intent:
            cur.execute(
                "SELECT COUNT(*) FROM mentoring_knowledge WHERE intent = %s",
                (intent,),
            )
        else:
            cur.execute("SELECT COUNT(*) FROM mentoring_knowledge")
        total = cur.fetchone()[0]

        # 데이터 조회
        if intent:
            cur.execute(
                """
                SELECT id, instruction, question, intent, context,
                       thought_process, response, created_at
                FROM mentoring_knowledge
                WHERE intent = %s
                ORDER BY id DESC
                LIMIT %s OFFSET %s
                """,
                (intent, size, offset),
            )
        else:
            cur.execute(
                """
                SELECT id, instruction, question, intent, context,
                       thought_process, response, created_at
                FROM mentoring_knowledge
                ORDER BY id DESC
                LIMIT %s OFFSET %s
                """,
                (size, offset),
            )
        rows = cur.fetchall()

    items = [
        {
            "id": r[0],
            "instruction": r[1][:100] + "..." if len(r[1]) > 100 else r[1],
            "question": r[2],
            "intent": r[3],
            "context": r[4][:200] + "..." if r[4] and len(r[4]) > 200 else r[4],
            "thought_process": r[5][:200] + "..." if r[5] and len(r[5]) > 200 else r[5],
            "response": r[6][:200] + "..." if len(r[6]) > 200 else r[6],
            "created_at": str(r[7]) if r[7] else None,
        }
        for r in rows
    ]

    return {
        "success": True,
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "total_pages": (total + size - 1) // size,
    }


@router.get("/stats", response_model=dict)
async def get_mentoring_stats(
    conn: psycopg.Connection = Depends(get_db_connection),
) -> dict:
    """멘토링 지식 통계."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM mentoring_knowledge")
        total = cur.fetchone()[0]

        cur.execute(
            """
            SELECT intent, COUNT(*) as cnt
            FROM mentoring_knowledge
            WHERE intent IS NOT NULL
            GROUP BY intent
            ORDER BY cnt DESC
            """
        )
        intent_stats = [{"intent": r[0], "count": r[1]} for r in cur.fetchall()]

        cur.execute(
            "SELECT COUNT(*) FROM mentoring_knowledge WHERE knowledge_vector IS NOT NULL"
        )
        embedded_count = cur.fetchone()[0]

    return {
        "success": True,
        "total": total,
        "embedded_count": embedded_count,
        "intent_distribution": intent_stats,
    }


@router.get("/{knowledge_id}", response_model=dict)
async def get_mentoring_knowledge(
    knowledge_id: int,
    conn: psycopg.Connection = Depends(get_db_connection),
) -> dict:
    """멘토링 지식 상세 조회."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, instruction, question, intent, context,
                   thought_process, response, created_at
            FROM mentoring_knowledge
            WHERE id = %s
            """,
            (knowledge_id,),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="멘토링 지식을 찾을 수 없습니다.")

    return {
        "success": True,
        "item": {
            "id": row[0],
            "instruction": row[1],
            "question": row[2],
            "intent": row[3],
            "context": row[4],
            "thought_process": row[5],
            "response": row[6],
            "created_at": str(row[7]) if row[7] else None,
        },
    }


# ============================================================================
# 텍스트 기반 검색 (벡터 임베딩 전 사용 가능)
# ============================================================================

@router.get("/search/text", response_model=dict)
async def search_mentoring_text(
    q: str = Query(..., description="검색 키워드"),
    top_k: int = Query(default=5, ge=1, le=20),
    conn: psycopg.Connection = Depends(get_db_connection),
) -> dict:
    """키워드 기반 멘토링 지식 검색 (ILIKE)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, instruction, question, intent, context,
                   thought_process, response, created_at
            FROM mentoring_knowledge
            WHERE question ILIKE %s
               OR context ILIKE %s
               OR response ILIKE %s
            ORDER BY id DESC
            LIMIT %s
            """,
            (f"%{q}%", f"%{q}%", f"%{q}%", top_k),
        )
        rows = cur.fetchall()

    items = [
        {
            "id": r[0],
            "instruction": r[1][:100] + "..." if len(r[1]) > 100 else r[1],
            "question": r[2],
            "intent": r[3],
            "context": r[4][:200] + "..." if r[4] and len(r[4]) > 200 else r[4],
            "thought_process": r[5][:200] + "..." if r[5] and len(r[5]) > 200 else r[5],
            "response": r[6][:200] + "..." if len(r[6]) > 200 else r[6],
            "created_at": str(r[7]) if r[7] else None,
        }
        for r in rows
    ]

    return {
        "success": True,
        "query": q,
        "count": len(items),
        "items": items,
    }


# ============================================================================
# 임베딩 생성
# ============================================================================

class MentoringEmbeddingRequest(BaseModel):
    """임베딩 생성 요청."""
    batch_size: int = Field(default=200, ge=1, le=2000, description="배치 크기")


@router.post("/enqueue-embeddings")
async def enqueue_mentoring_embeddings(
    request: MentoringEmbeddingRequest = MentoringEmbeddingRequest(),
    conn: psycopg.Connection = Depends(get_db_connection),
) -> dict:
    """멘토링 지식 임베딩 생성 엔드포인트.

    knowledge_vector가 NULL인 레코드에 대해 임베딩을 생성합니다.
    임베딩 텍스트: question + intent + context (검색 대상 필드를 결합)
    """
    try:
        # 임베딩이 필요한 건수 확인
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM mentoring_knowledge WHERE knowledge_vector IS NULL")
            pending_count = cur.fetchone()[0]

        if pending_count == 0:
            return {
                "success": True,
                "message": "임베딩이 필요한 멘토링 지식이 없습니다.",
                "processed_count": 0,
                "total_count": 0,
                "mode": "none",
            }

        # KURE-v1 배치 임베딩 생성 (개별 호출 대비 10~50배 빠름)
        from backend.core.utils.embedding import generate_embeddings_batch

        processed_count = 0
        errors: List[Dict[str, Any]] = []

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, question, intent, context
                FROM mentoring_knowledge
                WHERE knowledge_vector IS NULL
                ORDER BY id
                LIMIT %s
                """,
                (request.batch_size,),
            )
            rows = cur.fetchall()

        if not rows:
            return {
                "success": True,
                "message": "임베딩이 필요한 멘토링 지식이 없습니다.",
                "processed_count": 0,
                "total_count": 0,
                "remaining_count": 0,
                "mode": "none",
            }

        logger.info(
            f"[MentoringKnowledge] KURE-v1 배치 임베딩 시작: {len(rows)}건 / 전체 미처리 {pending_count}건"
        )

        # 1) 임베딩 텍스트를 한꺼번에 준비
        ids = []
        texts = []
        for row in rows:
            mk_id = row[0]
            question = row[1] or ""
            intent = row[2] or ""
            context = row[3] or ""

            embedding_text = f"질문: {question}"
            if intent:
                embedding_text += f" 의도: {intent}"
            if context:
                context_truncated = context[:500] if len(context) > 500 else context
                embedding_text += f" 맥락: {context_truncated}"

            ids.append(mk_id)
            texts.append(embedding_text)

        # 2) 배치 임베딩 생성 (SentenceTransformer 내부 배치 처리)
        try:
            vectors = generate_embeddings_batch(texts, batch_size=32)
        except Exception as e:
            logger.error(f"[MentoringKnowledge] 배치 임베딩 생성 실패: {e}")
            raise HTTPException(status_code=500, detail=f"KURE-v1 임베딩 생성 실패: {str(e)}")

        # 3) DB에 저장
        for mk_id, vec in zip(ids, vectors):
            try:
                embedding_str = "[" + ",".join(map(str, vec)) + "]"
                with conn.cursor() as update_cur:
                    update_cur.execute(
                        """
                        UPDATE mentoring_knowledge
                        SET knowledge_vector = %s::vector
                        WHERE id = %s
                        """,
                        (embedding_str, mk_id),
                    )
                conn.commit()
                processed_count += 1
            except Exception as e:
                logger.error(f"[MentoringKnowledge] ID {mk_id} DB 저장 실패: {e}")
                errors.append({"id": mk_id, "error": str(e)})
                conn.rollback()

        # 남은 건수 재조회
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM mentoring_knowledge WHERE knowledge_vector IS NULL")
            remaining = cur.fetchone()[0]

        logger.info(
            f"[MentoringKnowledge] 배치 임베딩 완료: {processed_count}건 성공, {len(errors)}건 실패, {remaining}건 남음"
        )

        return {
            "success": True,
            "message": f"{processed_count}건의 멘토링 지식 임베딩을 생성했습니다. ({remaining}건 남음)",
            "processed_count": processed_count,
            "total_count": len(rows),
            "remaining_count": remaining,
            "errors": errors[:10] if errors else None,
            "mode": "direct",
        }

    except Exception as e:
        logger.error(f"[MentoringKnowledge] 임베딩 생성 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"임베딩 생성 오류: {str(e)}")


@router.get("/embedding-status")
async def get_mentoring_embedding_status(
    conn: psycopg.Connection = Depends(get_db_connection),
) -> dict:
    """멘토링 지식 임베딩 상태 조회."""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM mentoring_knowledge")
            total_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM mentoring_knowledge WHERE knowledge_vector IS NOT NULL")
            embedded_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM mentoring_knowledge WHERE knowledge_vector IS NULL")
            remaining_count = cur.fetchone()[0]

        return {
            "success": True,
            "is_complete": remaining_count == 0,
            "total_count": total_count,
            "embedded_count": embedded_count,
            "remaining_count": remaining_count,
            "progress_percent": round(embedded_count / total_count * 100, 1) if total_count > 0 else 0,
            "message": "완료" if remaining_count == 0 else f"{remaining_count}건 남음",
        }

    except Exception as e:
        logger.error(f"[MentoringKnowledge] 임베딩 상태 조회 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 삭제
# ============================================================================

@router.delete("/all", response_model=dict)
async def delete_all_mentoring_knowledge(
    conn: psycopg.Connection = Depends(get_db_connection),
) -> dict:
    """멘토링 지식 전체 삭제."""
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM mentoring_knowledge")
            deleted_count = cur.rowcount

        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"{deleted_count}건의 멘토링 지식이 삭제되었습니다.",
        }
    except Exception as e:
        logger.error(f"[MentoringKnowledge] 전체 삭제 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

