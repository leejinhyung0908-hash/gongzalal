"""문제(Questions) 라우터.

새 테이블 구조:
- Questions: exam_id FK, question_no, question_text, answer_key 등
- Question_Images: question_id FK, file_path, coordinates_json
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import psycopg
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.dependencies import get_db_connection

# 프로젝트 루트 (yolo_quiz/data/crops 기준)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
from backend.domain.admin.models.transfers.question_transfer import (
    QuestionTransfer,
    QuestionCreateRequest,
    QuestionSearchRequest,
    QuestionImageTransfer,
)
from backend.domain.admin.hub.orchestrators.question_flow import QuestionFlow

router = APIRouter(tags=["questions"])
logger = logging.getLogger(__name__)

# Orchestrator 인스턴스 (싱글톤 패턴)
_flow = QuestionFlow()


# ============================================================================
# Question 엔드포인트
# ============================================================================

@router.post("/", response_model=dict)
async def create_question(
    request: QuestionCreateRequest,
    conn: psycopg.Connection = Depends(get_db_connection)
) -> dict:
    """문제 생성 엔드포인트."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO questions (
                    exam_id, question_no, question_text, sub_category,
                    answer_key, ind, source_pdf, extra_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                RETURNING id, exam_id, question_no, question_text, sub_category,
                          answer_key, ind, source_pdf, extra_json, created_at, updated_at
                """,
                (
                    request.exam_id,
                    request.question_no,
                    request.question_text,
                    request.sub_category,
                    request.answer_key,
                    request.ind,
                    request.source_pdf,
                    str(request.extra_json or {}),
                ),
            )
            row = cur.fetchone()
            conn.commit()

        return {
            "success": True,
            "question": QuestionTransfer(
                id=row[0],
                exam_id=row[1],
                question_no=row[2],
                question_text=row[3],
                sub_category=row[4],
                answer_key=row[5],
                ind=row[6],
                source_pdf=row[7],
                extra_json=row[8] or {},
                created_at=row[9],
                updated_at=row[10],
            ).model_dump(),
        }
    except Exception as e:
        conn.rollback()
        logger.error(f"[QuestionRouter] 문제 생성 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"문제 생성 실패: {str(e)}")


@router.get("/{question_id}", response_model=dict)
async def get_question(
    question_id: int,
    conn: psycopg.Connection = Depends(get_db_connection)
) -> dict:
    """문제 조회 엔드포인트."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, exam_id, question_no, question_text, sub_category,
                   answer_key, ind, source_pdf, extra_json, created_at, updated_at
            FROM questions WHERE id = %s
            """,
            (question_id,),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")

    return {
        "success": True,
        "question": QuestionTransfer(
            id=row[0],
            exam_id=row[1],
            question_no=row[2],
            question_text=row[3],
            sub_category=row[4],
            answer_key=row[5],
            ind=row[6],
            source_pdf=row[7],
            extra_json=row[8] or {},
            created_at=row[9],
            updated_at=row[10],
        ).model_dump(),
    }


@router.post("/search", response_model=dict)
async def search_questions(
    request: QuestionSearchRequest,
    conn: psycopg.Connection = Depends(get_db_connection)
) -> dict:
    """문제 검색 엔드포인트."""
    conditions = []
    params = []

    if request.exam_id:
        conditions.append("q.exam_id = %s")
        params.append(request.exam_id)
    if request.question_no:
        conditions.append("q.question_no = %s")
        params.append(request.question_no)
    if request.sub_category:
        conditions.append("q.sub_category ILIKE %s")
        params.append(f"%{request.sub_category}%")
    if request.keyword:
        conditions.append("q.question_text ILIKE %s")
        params.append(f"%{request.keyword}%")

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    params.extend([request.limit, request.offset])

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT q.id, q.exam_id, q.question_no, q.question_text, q.sub_category,
                   q.answer_key, q.ind, q.source_pdf, q.extra_json, q.created_at, q.updated_at
            FROM questions q
            WHERE {where_clause}
            ORDER BY q.exam_id, q.question_no
            LIMIT %s OFFSET %s
            """,
            params,
        )
        rows = cur.fetchall()

    questions = [
        QuestionTransfer(
            id=r[0], exam_id=r[1], question_no=r[2], question_text=r[3],
            sub_category=r[4], answer_key=r[5], ind=r[6], source_pdf=r[7],
            extra_json=r[8] or {}, created_at=r[9], updated_at=r[10],
        ).model_dump()
        for r in rows
    ]

    return {"success": True, "questions": questions, "count": len(questions)}


@router.get("/exam/{exam_id}", response_model=dict)
async def get_questions_by_exam(
    exam_id: int,
    conn: psycopg.Connection = Depends(get_db_connection)
) -> dict:
    """특정 시험의 모든 문제 조회."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, exam_id, question_no, question_text, sub_category,
                   answer_key, ind, source_pdf, extra_json, created_at, updated_at
            FROM questions
            WHERE exam_id = %s
            ORDER BY question_no
            """,
            (exam_id,),
        )
        rows = cur.fetchall()

    questions = [
        QuestionTransfer(
            id=r[0], exam_id=r[1], question_no=r[2], question_text=r[3],
            sub_category=r[4], answer_key=r[5], ind=r[6], source_pdf=r[7],
            extra_json=r[8] or {}, created_at=r[9], updated_at=r[10],
        ).model_dump()
        for r in rows
    ]

    return {"success": True, "questions": questions, "count": len(questions)}


# ============================================================================
# Question Image 엔드포인트
# ============================================================================

class QuestionImageCreateRequest(BaseModel):
    """문제 이미지 생성 요청."""
    question_id: int = Field(..., ge=1, description="문제 ID")
    file_path: str = Field(..., max_length=255, description="파일 경로")
    coordinates_json: Dict[str, Any] = Field(default_factory=dict, description="좌표 정보")
    image_type: str = Field(..., max_length=50, description="이미지 유형")


@router.post("/images", response_model=dict)
async def create_question_image(
    request: QuestionImageCreateRequest,
    conn: psycopg.Connection = Depends(get_db_connection)
) -> dict:
    """문제 이미지 생성 엔드포인트."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO question_images (question_id, file_path, coordinates_json, image_type)
                VALUES (%s, %s, %s::jsonb, %s)
                RETURNING id, question_id, file_path, coordinates_json, image_type
                """,
                (
                    request.question_id,
                    request.file_path,
                    str(request.coordinates_json),
                    request.image_type,
                ),
            )
            row = cur.fetchone()
            conn.commit()

        return {
            "success": True,
            "image": QuestionImageTransfer(
                id=row[0],
                question_id=row[1],
                file_path=row[2],
                coordinates_json=row[3] or {},
                image_type=row[4],
            ).model_dump(),
        }
    except Exception as e:
        conn.rollback()
        logger.error(f"[QuestionRouter] 이미지 생성 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"이미지 생성 실패: {str(e)}")


@router.get("/{question_id}/images", response_model=dict)
async def get_question_images(
    question_id: int,
    conn: psycopg.Connection = Depends(get_db_connection)
) -> dict:
    """문제의 이미지 목록 조회."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, question_id, file_path, coordinates_json, image_type
            FROM question_images
            WHERE question_id = %s
            """,
            (question_id,),
        )
        rows = cur.fetchall()

    images = [
        QuestionImageTransfer(
            id=r[0], question_id=r[1], file_path=r[2],
            coordinates_json=r[3] or {}, image_type=r[4],
        ).model_dump()
        for r in rows
    ]

    return {"success": True, "images": images, "count": len(images)}


# ============================================================================
# Random Question Images (가상 모의고사 - 랜덤 풀기)
# ============================================================================

@router.get("/images/random", response_model=dict)
async def get_random_question_images(
    count: int = 20,
    conn: psycopg.Connection = Depends(get_db_connection),
) -> dict:
    """랜덤 문제 이미지 목록을 시험 메타데이터와 함께 반환합니다.

    Args:
        count: 반환할 이미지 수 (기본 20)

    Returns:
        랜덤 문제 이미지 리스트 (시험 정보 포함)
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                qi.id AS image_id,
                qi.question_id,
                qi.file_path,
                qi.coordinates_json,
                qi.image_type,
                q.question_no,
                q.answer_key,
                q.exam_id,
                e.year,
                e.exam_type,
                e.subject,
                e.grade,
                e.series
            FROM question_images qi
            JOIN questions q ON qi.question_id = q.id
            JOIN exams e ON q.exam_id = e.id
            ORDER BY RANDOM()
            LIMIT %s
            """,
            (min(count, 100),),
        )
        rows = cur.fetchall()

    images = []
    for r in rows:
        images.append({
            "image_id": r[0],
            "question_id": r[1],
            "file_path": r[2],
            "coordinates_json": r[3] or {},
            "image_type": r[4],
            "question_no": r[5],
            "answer_key": r[6],
            "exam_id": r[7],
            "year": r[8],
            "exam_type": r[9],
            "subject": r[10],
            "grade": r[11],
            "series": r[12],
        })

    return {"success": True, "images": images, "count": len(images)}


@router.get("/images/serve/{image_id}")
async def serve_question_image(
    image_id: int,
    conn: psycopg.Connection = Depends(get_db_connection),
):
    """문제 이미지 파일을 서빙합니다.

    DB에 저장된 file_path를 기반으로 실제 이미지 파일을 반환합니다.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT file_path, image_type FROM question_images WHERE id = %s",
            (image_id,),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")

    file_path_str = row[0].replace("\\", "/")
    image_type = row[1] or "webp"

    # yolo_quiz 기준 경로 탐색
    candidates = [
        _PROJECT_ROOT / "yolo_quiz" / file_path_str,
        _PROJECT_ROOT / file_path_str,
    ]

    resolved_path = None
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            resolved_path = candidate
            break

    if not resolved_path:
        raise HTTPException(
            status_code=404,
            detail=f"이미지 파일을 찾을 수 없습니다: {file_path_str}",
        )

    media_type_map = {
        "webp": "image/webp",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
    }
    media_type = media_type_map.get(image_type.lower(), "image/webp")

    return FileResponse(
        path=str(resolved_path),
        media_type=media_type,
        filename=resolved_path.name,
    )


# ============================================================================
# YOLO Crop Results 업로드
# ============================================================================

class CropResultsUploadRequest(BaseModel):
    """YOLO crop_results.json 업로드 요청."""
    crop_results: List[Dict[str, Any]] = Field(..., description="crop_results.json 데이터 배열")
    filename: str = Field(default="crop_results.json", description="원본 파일명")


@router.post("/upload-crop-results")
async def upload_crop_results(
    request: CropResultsUploadRequest,
) -> dict:
    """YOLO crop_results.json 업로드 및 DB 저장 엔드포인트.

    crop_results.json 데이터를 받아 폴더명에서 시험 메타데이터를 파싱하고,
    exams → questions → question_images 순서로 DB에 저장합니다.

    Args:
        request: crop_results 데이터

    Returns:
        처리 결과
    """
    try:
        print(
            f"[QuestionRouter] >>> /upload-crop-results 호출됨: "
            f"filename={request.filename}, items={len(request.crop_results)}",
            flush=True,
        )

        if not request.crop_results:
            raise HTTPException(status_code=400, detail="crop_results 데이터가 비어있습니다.")

        logger.info(
            f"[QuestionRouter] crop_results 업로드 수신: "
            f"filename={request.filename}, items={len(request.crop_results)}"
        )

        # QuestionFlow로 데이터 전달
        result = await _flow.process_crop_results(
            crop_results=request.crop_results,
            filename=request.filename,
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[QuestionRouter] crop_results 업로드 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"crop_results 처리 실패: {str(e)}")

