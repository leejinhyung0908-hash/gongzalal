"""풀이 로그(User_Solving_Logs) 라우터.

새 테이블 구조:
- User_Solving_Logs: user_id FK, question_id FK, selected_answer, time_spent, is_wrong_note
"""

from __future__ import annotations

import logging
from typing import List, Optional

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.dependencies import get_db_connection
from backend.domain.admin.models.transfers.user_transfer import (
    UserSolvingLogTransfer,
    UserSolvingLogCreateRequest,
    UserSolvingLogResponse,
)

router = APIRouter(tags=["solving-logs"])
logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic 모델 (배치용)
# ============================================================================

class SolvingLogItem(BaseModel):
    """배치 저장 시 개별 풀이 로그 아이템."""
    question_id: int = Field(..., ge=1, description="문제 ID")
    selected_answer: Optional[str] = Field(default=None, max_length=10, description="선택 답안")
    time_spent: Optional[int] = Field(default=None, ge=0, description="풀이 소요 시간 (초)")
    is_wrong_note: bool = Field(default=False, description="오답 노트 여부")


class BatchSolvingLogRequest(BaseModel):
    """배치 풀이 로그 생성 요청."""
    user_id: int = Field(default=1, ge=1, description="사용자 ID")
    logs: List[SolvingLogItem] = Field(..., description="풀이 로그 목록")


# ============================================================================
# User Solving Log 엔드포인트
# ============================================================================

@router.post("/", response_model=dict)
async def create_solving_log(
    request: UserSolvingLogCreateRequest,
    conn: psycopg.Connection = Depends(get_db_connection)
) -> dict:
    """풀이 로그 생성 엔드포인트."""
    try:
        # 정답 확인
        is_correct = None
        with conn.cursor() as cur:
            cur.execute(
                "SELECT answer_key FROM questions WHERE id = %s",
                (request.question_id,)
            )
            row = cur.fetchone()
            if row and request.selected_answer:
                is_correct = row[0] == request.selected_answer

            cur.execute(
                """
                INSERT INTO user_solving_logs (
                    user_id, question_id, selected_answer, time_spent,
                    special_event, is_wrong_note
                ) VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, user_id, question_id, selected_answer, time_spent,
                          special_event, is_wrong_note, created_at
                """,
                (
                    request.user_id,
                    request.question_id,
                    request.selected_answer,
                    request.time_spent,
                    request.special_event,
                    request.is_wrong_note,
                ),
            )
            row = cur.fetchone()
            conn.commit()

        return {
            "success": True,
            "solving_log": UserSolvingLogResponse(
                id=row[0],
                user_id=row[1],
                question_id=row[2],
                selected_answer=row[3],
                time_spent=row[4],
                special_event=row[5],
                is_wrong_note=row[6],
                is_correct=is_correct,
                created_at=row[7].isoformat() if row[7] else None,
            ).model_dump(),
        }
    except Exception as e:
        conn.rollback()
        logger.error(f"[SolvingLogRouter] 풀이 로그 생성 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"풀이 로그 생성 실패: {str(e)}")


@router.post("/batch", response_model=dict)
async def create_solving_logs_batch(
    request: BatchSolvingLogRequest,
    conn: psycopg.Connection = Depends(get_db_connection),
) -> dict:
    """배치 풀이 로그 생성 - 모의고사 완료 시 한꺼번에 저장."""
    inserted = 0
    errors = []
    try:
        with conn.cursor() as cur:
            for idx, log_item in enumerate(request.logs):
                try:
                    # 정답 확인
                    is_correct = None
                    cur.execute(
                        "SELECT answer_key FROM questions WHERE id = %s",
                        (log_item.question_id,),
                    )
                    q_row = cur.fetchone()
                    if q_row and log_item.selected_answer:
                        is_correct = str(q_row[0]) == str(log_item.selected_answer)

                    cur.execute(
                        """
                        INSERT INTO user_solving_logs (
                            user_id, question_id, selected_answer, time_spent,
                            is_wrong_note
                        ) VALUES (%s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (
                            request.user_id,
                            log_item.question_id,
                            log_item.selected_answer,
                            log_item.time_spent,
                            log_item.is_wrong_note,
                        ),
                    )
                    new_id = cur.fetchone()
                    if new_id:
                        inserted += 1
                    else:
                        errors.append({"index": idx, "error": "INSERT 실패"})
                except Exception as item_err:
                    errors.append({"index": idx, "question_id": log_item.question_id, "error": str(item_err)})

            conn.commit()

        return {
            "success": True,
            "inserted_count": inserted,
            "total": len(request.logs),
            "errors": errors,
            "message": f"{inserted}건 저장 완료",
        }
    except Exception as e:
        conn.rollback()
        logger.error(f"[SolvingLogRouter] 배치 풀이 로그 생성 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"배치 풀이 로그 생성 실패: {str(e)}")


@router.get("/{log_id}", response_model=dict)
async def get_solving_log(
    log_id: int,
    conn: psycopg.Connection = Depends(get_db_connection)
) -> dict:
    """풀이 로그 조회 엔드포인트."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT usl.id, usl.user_id, usl.question_id, usl.selected_answer, usl.time_spent,
                   usl.special_event, usl.is_wrong_note, usl.created_at,
                   q.answer_key
            FROM user_solving_logs usl
            LEFT JOIN questions q ON usl.question_id = q.id
            WHERE usl.id = %s
            """,
            (log_id,),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="풀이 로그를 찾을 수 없습니다.")

    is_correct = None
    if row[8] and row[3]:  # answer_key and selected_answer
        is_correct = row[8] == row[3]

    return {
        "success": True,
        "solving_log": UserSolvingLogResponse(
            id=row[0],
            user_id=row[1],
            question_id=row[2],
            selected_answer=row[3],
            time_spent=row[4],
            special_event=row[5],
            is_wrong_note=row[6],
            is_correct=is_correct,
            created_at=row[7].isoformat() if row[7] else None,
        ).model_dump(),
    }


@router.get("/user/{user_id}", response_model=dict)
async def get_user_solving_logs(
    user_id: int,
    limit: int = 50,
    offset: int = 0,
    conn: psycopg.Connection = Depends(get_db_connection)
) -> dict:
    """사용자의 풀이 로그 목록 조회."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT usl.id, usl.user_id, usl.question_id, usl.selected_answer, usl.time_spent,
                   usl.special_event, usl.is_wrong_note, usl.created_at,
                   q.answer_key
            FROM user_solving_logs usl
            LEFT JOIN questions q ON usl.question_id = q.id
            WHERE usl.user_id = %s
            ORDER BY usl.created_at DESC
            LIMIT %s OFFSET %s
            """,
            (user_id, limit, offset),
        )
        rows = cur.fetchall()

    logs = []
    for r in rows:
        is_correct = None
        if r[8] and r[3]:
            is_correct = r[8] == r[3]
        logs.append(
            UserSolvingLogResponse(
                id=r[0], user_id=r[1], question_id=r[2], selected_answer=r[3],
                time_spent=r[4], special_event=r[5], is_wrong_note=r[6],
                is_correct=is_correct, created_at=r[7].isoformat() if r[7] else None,
            ).model_dump()
        )

    return {"success": True, "solving_logs": logs, "count": len(logs)}


@router.get("/user/{user_id}/wrong-notes", response_model=dict)
async def get_user_wrong_notes(
    user_id: int,
    limit: int = 50,
    offset: int = 0,
    conn: psycopg.Connection = Depends(get_db_connection)
) -> dict:
    """사용자의 오답 노트 목록 조회."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT usl.id, usl.user_id, usl.question_id, usl.selected_answer, usl.time_spent,
                   usl.special_event, usl.is_wrong_note, usl.created_at,
                   q.answer_key, q.question_text
            FROM user_solving_logs usl
            LEFT JOIN questions q ON usl.question_id = q.id
            WHERE usl.user_id = %s AND usl.is_wrong_note = TRUE
            ORDER BY usl.created_at DESC
            LIMIT %s OFFSET %s
            """,
            (user_id, limit, offset),
        )
        rows = cur.fetchall()

    logs = []
    for r in rows:
        is_correct = None
        if r[8] and r[3]:
            is_correct = r[8] == r[3]
        logs.append({
            "id": r[0],
            "user_id": r[1],
            "question_id": r[2],
            "selected_answer": r[3],
            "time_spent": r[4],
            "special_event": r[5],
            "is_wrong_note": r[6],
            "is_correct": is_correct,
            "created_at": r[7].isoformat() if r[7] else None,
            "correct_answer": r[8],
            "question_text": r[9][:100] if r[9] else None,  # 미리보기
        })

    return {"success": True, "wrong_notes": logs, "count": len(logs)}


@router.get("/user/{user_id}/stats", response_model=dict)
async def get_user_stats(
    user_id: int,
    conn: psycopg.Connection = Depends(get_db_connection)
) -> dict:
    """사용자의 풀이 통계 조회."""
    with conn.cursor() as cur:
        # 전체 풀이 수
        cur.execute(
            "SELECT COUNT(*) FROM user_solving_logs WHERE user_id = %s",
            (user_id,)
        )
        total_count = cur.fetchone()[0]

        # 정답 수 (selected_answer = answer_key)
        cur.execute(
            """
            SELECT COUNT(*)
            FROM user_solving_logs usl
            JOIN questions q ON usl.question_id = q.id
            WHERE usl.user_id = %s AND usl.selected_answer = q.answer_key
            """,
            (user_id,)
        )
        correct_count = cur.fetchone()[0]

        # 오답 노트 수
        cur.execute(
            "SELECT COUNT(*) FROM user_solving_logs WHERE user_id = %s AND is_wrong_note = TRUE",
            (user_id,)
        )
        wrong_note_count = cur.fetchone()[0]

        # 평균 소요 시간
        cur.execute(
            "SELECT AVG(time_spent) FROM user_solving_logs WHERE user_id = %s AND time_spent IS NOT NULL",
            (user_id,)
        )
        avg_time = cur.fetchone()[0]

    accuracy = (correct_count / total_count * 100) if total_count > 0 else 0

    return {
        "success": True,
        "stats": {
            "total_solved": total_count,
            "correct_count": correct_count,
            "wrong_count": total_count - correct_count,
            "wrong_note_count": wrong_note_count,
            "accuracy": round(accuracy, 2),
            "avg_time_seconds": round(avg_time, 2) if avg_time else None,
        }
    }


@router.put("/{log_id}/wrong-note", response_model=dict)
async def toggle_wrong_note(
    log_id: int,
    conn: psycopg.Connection = Depends(get_db_connection)
) -> dict:
    """오답 노트 토글 엔드포인트."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE user_solving_logs
                SET is_wrong_note = NOT is_wrong_note
                WHERE id = %s
                RETURNING id, is_wrong_note
                """,
                (log_id,)
            )
            row = cur.fetchone()
            conn.commit()

        if not row:
            raise HTTPException(status_code=404, detail="풀이 로그를 찾을 수 없습니다.")

        return {
            "success": True,
            "log_id": row[0],
            "is_wrong_note": row[1],
            "message": "오답 노트에 추가되었습니다." if row[1] else "오답 노트에서 제거되었습니다."
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"[SolvingLogRouter] 오답 노트 토글 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"오답 노트 토글 실패: {str(e)}")


@router.delete("/{log_id}", response_model=dict)
async def delete_solving_log(
    log_id: int,
    conn: psycopg.Connection = Depends(get_db_connection)
) -> dict:
    """풀이 로그 삭제 엔드포인트."""
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM user_solving_logs WHERE id = %s RETURNING id", (log_id,))
            deleted = cur.fetchone()
            conn.commit()

        if not deleted:
            raise HTTPException(status_code=404, detail="풀이 로그를 찾을 수 없습니다.")

        return {"success": True, "message": "풀이 로그가 삭제되었습니다."}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"[SolvingLogRouter] 풀이 로그 삭제 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"풀이 로그 삭제 실패: {str(e)}")

