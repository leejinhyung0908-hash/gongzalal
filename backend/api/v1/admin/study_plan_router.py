"""학습 계획(Study_Plans) 라우터.

새 테이블 구조:
- Study_Plans: user_id FK, plan_json, version

학습 분석 + AI 계획 생성 파이프라인:
1. /analyze/{user_id} — 풀이 로그 분석 (SQL + Python)
2. /generate — 분석 + RAG + EXAONE → 개인화 학습 계획 생성
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.config import settings
from backend.dependencies import get_db_connection
from backend.domain.admin.models.transfers.user_transfer import (
    StudyPlanTransfer,
    StudyPlanCreateRequest,
    StudyPlanUpdateRequest,
)
from backend.domain.admin.spokes.agents.analysis.solving_log_analyzer import (
    SolvingLogAnalyzer,
)

router = APIRouter(tags=["study-plans"])
logger = logging.getLogger(__name__)


# ============================================================================
# 풀이 로그 분석 엔드포인트 (/{plan_id} 보다 앞에 위치해야 함)
# ============================================================================

@router.get("/analyze/{user_id}", response_model=dict)
async def analyze_solving_logs(
    user_id: int,
    conn: psycopg.Connection = Depends(get_db_connection),
) -> dict:
    """사용자의 풀이 로그를 분석합니다.

    과목별 정답률, 취약/강점 과목, 시간 분석, 반복 오답,
    점수 추이 등 종합 분석 결과를 반환합니다.
    """
    try:
        analyzer = SolvingLogAnalyzer(conn)
        analysis = analyzer.analyze(user_id)
        return {"success": True, "analysis": analysis}
    except Exception as e:
        logger.error(f"[StudyPlanRouter] 풀이 로그 분석 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"분석 실패: {str(e)}")


# ============================================================================
# AI 학습 계획 생성 엔드포인트 (/{plan_id} 보다 앞에 위치해야 함)
# ============================================================================

class GeneratePlanRequest(BaseModel):
    """AI 학습 계획 생성 요청."""

    user_id: int = Field(..., ge=1, description="사용자 ID")
    question: str = Field(
        default="내 풀이 데이터를 분석해서 학습 계획을 세워줘",
        description="사용자 질문/요청",
    )


@router.post("/generate", response_model=dict)
async def generate_study_plan_ai(
    request: GeneratePlanRequest,
    conn: psycopg.Connection = Depends(get_db_connection),
) -> dict:
    """분석 + RAG + EXAONE으로 개인화 학습 계획을 생성합니다.

    1. 풀이 로그 분석
    2. 분석 기반 합격 수기 RAG 검색
    3. EXAONE으로 학습 계획 생성 (실패 시 템플릿 폴백)
    4. study_plans 테이블에 저장
    """
    try:
        from backend.domain.admin.hub.orchestrators.study_plan_flow import StudyPlanFlow

        # LLM 로드 시도 (실패해도 템플릿으로 폴백)
        # Study Plan은 모델 타입을 분리해 운영할 수 있습니다.
        # 예) STUDY_PLAN_MODEL_TYPE=gemini, STUDY_PLAN_MODEL_NAME=gemini-1.5-flash
        llm = None
        try:
            from backend.dependencies import get_llm
            llm = get_llm(
                model_type=settings.STUDY_PLAN_MODEL_TYPE,
                model_name=settings.STUDY_PLAN_MODEL_NAME,
            )
        except Exception as e:
            logger.warning(f"[StudyPlanRouter] LLM 로드 실패, 템플릿 사용: {e}")

        flow = StudyPlanFlow()
        result = await flow.process_study_plan_request(
            request_text=request.question,
            request_data={
                "action": "generate",
                "user_id": request.user_id,
                "_conn": conn,
                "_llm": llm,
            },
        )
        return result

    except Exception as e:
        logger.error(f"[StudyPlanRouter] AI 학습 계획 생성 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"학습 계획 생성 실패: {str(e)}")


# ============================================================================
# 기본 CRUD 엔드포인트
# ============================================================================

@router.post("/", response_model=dict)
async def create_study_plan(
    request: StudyPlanCreateRequest,
    conn: psycopg.Connection = Depends(get_db_connection)
) -> dict:
    """학습 계획 생성 엔드포인트."""
    try:
        with conn.cursor() as cur:
            # 기존 계획 확인하여 version 증가
            cur.execute(
                "SELECT MAX(version) FROM study_plans WHERE user_id = %s",
                (request.user_id,)
            )
            max_version = cur.fetchone()[0] or 0
            new_version = max_version + 1

            cur.execute(
                """
                INSERT INTO study_plans (user_id, plan_json, version)
                VALUES (%s, %s::jsonb, %s)
                RETURNING id, user_id, plan_json, version, created_at, updated_at
                """,
                (request.user_id, str(request.plan_json), new_version),
            )
            row = cur.fetchone()
            conn.commit()

        return {
            "success": True,
            "study_plan": StudyPlanTransfer(
                id=row[0],
                user_id=row[1],
                plan_json=row[2] or {},
                version=row[3],
                created_at=row[4],
                updated_at=row[5],
            ).model_dump(),
        }
    except Exception as e:
        conn.rollback()
        logger.error(f"[StudyPlanRouter] 학습 계획 생성 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"학습 계획 생성 실패: {str(e)}")


@router.get("/user/{user_id}", response_model=dict)
async def get_user_study_plans(
    user_id: int,
    conn: psycopg.Connection = Depends(get_db_connection)
) -> dict:
    """사용자의 학습 계획 목록 조회."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, user_id, plan_json, version, created_at, updated_at
            FROM study_plans
            WHERE user_id = %s
            ORDER BY version DESC
            """,
            (user_id,),
        )
        rows = cur.fetchall()

    plans = [
        StudyPlanTransfer(
            id=r[0], user_id=r[1], plan_json=r[2] or {},
            version=r[3], created_at=r[4], updated_at=r[5],
        ).model_dump()
        for r in rows
    ]

    return {"success": True, "study_plans": plans, "count": len(plans)}


@router.get("/user/{user_id}/latest", response_model=dict)
async def get_latest_study_plan(
    user_id: int,
    conn: psycopg.Connection = Depends(get_db_connection)
) -> dict:
    """사용자의 최신 학습 계획 조회."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, user_id, plan_json, version, created_at, updated_at
            FROM study_plans
            WHERE user_id = %s
            ORDER BY version DESC
            LIMIT 1
            """,
            (user_id,),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="학습 계획을 찾을 수 없습니다.")

    return {
        "success": True,
        "study_plan": StudyPlanTransfer(
            id=row[0],
            user_id=row[1],
            plan_json=row[2] or {},
            version=row[3],
            created_at=row[4],
            updated_at=row[5],
        ).model_dump(),
    }


# /{plan_id} 패턴은 반드시 /analyze, /generate, /user 등 고정 경로 뒤에 위치해야 함
@router.get("/{plan_id}", response_model=dict)
async def get_study_plan(
    plan_id: int,
    conn: psycopg.Connection = Depends(get_db_connection)
) -> dict:
    """학습 계획 조회 엔드포인트."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, user_id, plan_json, version, created_at, updated_at
            FROM study_plans WHERE id = %s
            """,
            (plan_id,),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="학습 계획을 찾을 수 없습니다.")

    return {
        "success": True,
        "study_plan": StudyPlanTransfer(
            id=row[0],
            user_id=row[1],
            plan_json=row[2] or {},
            version=row[3],
            created_at=row[4],
            updated_at=row[5],
        ).model_dump(),
    }


@router.put("/{plan_id}", response_model=dict)
async def update_study_plan(
    plan_id: int,
    request: StudyPlanUpdateRequest,
    conn: psycopg.Connection = Depends(get_db_connection)
) -> dict:
    """학습 계획 수정 엔드포인트."""
    try:
        with conn.cursor() as cur:
            # 기존 계획 조회
            cur.execute("SELECT user_id, version FROM study_plans WHERE id = %s", (plan_id,))
            existing = cur.fetchone()

            if not existing:
                raise HTTPException(status_code=404, detail="학습 계획을 찾을 수 없습니다.")

            # 수정 (새 버전으로 저장 - 이력 관리)
            if request.plan_json:
                cur.execute(
                    """
                    INSERT INTO study_plans (user_id, plan_json, version)
                    VALUES (%s, %s::jsonb, %s)
                    RETURNING id, user_id, plan_json, version, created_at, updated_at
                    """,
                    (existing[0], str(request.plan_json), existing[1] + 1),
                )
                row = cur.fetchone()
                conn.commit()

                return {
                    "success": True,
                    "study_plan": StudyPlanTransfer(
                        id=row[0],
                        user_id=row[1],
                        plan_json=row[2] or {},
                        version=row[3],
                        created_at=row[4],
                        updated_at=row[5],
                    ).model_dump(),
                    "message": "새 버전으로 저장되었습니다."
                }
            else:
                return {"success": True, "message": "변경사항이 없습니다."}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"[StudyPlanRouter] 학습 계획 수정 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"학습 계획 수정 실패: {str(e)}")


@router.delete("/{plan_id}", response_model=dict)
async def delete_study_plan(
    plan_id: int,
    conn: psycopg.Connection = Depends(get_db_connection)
) -> dict:
    """학습 계획 삭제 엔드포인트."""
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM study_plans WHERE id = %s RETURNING id", (plan_id,))
            deleted = cur.fetchone()
            conn.commit()

        if not deleted:
            raise HTTPException(status_code=404, detail="학습 계획을 찾을 수 없습니다.")

        return {"success": True, "message": "학습 계획이 삭제되었습니다."}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"[StudyPlanRouter] 학습 계획 삭제 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"학습 계획 삭제 실패: {str(e)}")
