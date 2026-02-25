"""문제(Questions) 라우터.

새 테이블 구조:
- Questions: exam_id FK, question_no, question_text, answer_key 등
- Question_Images: question_id FK, file_path, coordinates_json
"""

from __future__ import annotations

import json
import logging
import re
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


def _extract_question_nos(coordinates_json: Any, fallback_no: int) -> List[int]:
    """coordinates_json에서 복수 문항 번호를 추출합니다."""
    if isinstance(coordinates_json, dict):
        raw = coordinates_json.get("question_nos")
        if isinstance(raw, list):
            nums: List[int] = []
            for n in raw:
                try:
                    qn = int(n)
                except (TypeError, ValueError):
                    continue
                if qn > 0:
                    nums.append(qn)
            if nums:
                return sorted(set(nums))
    return [int(fallback_no)]


def _extract_question_nos_from_path(file_path: str) -> List[int]:
    """파일명에서 문항 번호를 추출합니다.

    지원 예시:
    - gook_q01.webp -> [1]
    - gook_q07_q08.webp -> [7, 8]
    """
    file_name = file_path.replace("\\", "/").rsplit("/", 1)[-1].lower()
    if file_name.startswith("page_"):
        return []
    nums = [int(n) for n in re.findall(r"(?:^|_)q(\d{1,3})", file_name)]
    nums = [n for n in nums if n > 0]
    return sorted(set(nums))


def _resolve_question_nos(coordinates_json: Any, fallback_no: int, file_path: str) -> List[int]:
    """문항 번호를 coordinates_json 우선, 파일명 보조로 해석합니다."""
    from_coordinates = _extract_question_nos(coordinates_json, fallback_no)
    from_path = _extract_question_nos_from_path(file_path or "")

    # coordinates_json에 유효한 복수 번호가 있으면 최우선 사용
    if len(from_coordinates) > 1:
        return from_coordinates

    # 파일명이 더 풍부한 정보를 주면 파일명 사용
    if len(from_path) > len(from_coordinates):
        return from_path

    # 둘 다 단일이면 coordinates 우선
    return from_coordinates


def _build_mapped_questions(
    conn: psycopg.Connection,
    exam_id: int,
    question_nos: List[int],
    fallback_question_id: int,
    fallback_question_no: int,
    fallback_answer_key: Any,
) -> List[Dict[str, Any]]:
    """이미지가 대표하는 문항 목록(question_id/문항번호/정답)을 구성합니다."""
    requested = sorted(set(int(n) for n in question_nos if int(n) > 0))
    if not requested:
        requested = [int(fallback_question_no)]

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, question_no, answer_key
            FROM questions
            WHERE exam_id = %s
              AND question_no = ANY(%s)
            """,
            (exam_id, requested),
        )
        rows = cur.fetchall()

    by_qno: Dict[int, Dict[str, Any]] = {}
    for q_id, q_no, ans in rows:
        by_qno[int(q_no)] = {
            "question_id": int(q_id),
            "question_no": int(q_no),
            "answer_key": str(ans) if ans is not None else None,
        }

    mapped: List[Dict[str, Any]] = []
    for q_no in requested:
        if q_no in by_qno:
            mapped.append(by_qno[q_no])

    if not mapped:
        mapped = [{
            "question_id": int(fallback_question_id),
            "question_no": int(fallback_question_no),
            "answer_key": str(fallback_answer_key) if fallback_answer_key is not None else None,
        }]

    return mapped


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
        coordinates_json = r[3] or {}
        question_nos = _resolve_question_nos(coordinates_json, r[5], r[2] or "")
        mapped_questions = _build_mapped_questions(
            conn=conn,
            exam_id=int(r[7]),
            question_nos=question_nos,
            fallback_question_id=int(r[1]),
            fallback_question_no=int(r[5]),
            fallback_answer_key=r[6],
        )
        images.append({
            "image_id": r[0],
            "question_id": r[1],
            "file_path": r[2],
            "coordinates_json": coordinates_json,
            "image_type": r[4],
            "question_no": r[5],
            "question_nos": question_nos,
            "mapped_questions": mapped_questions,
            "answer_key": r[6],
            "exam_id": r[7],
            "year": r[8],
            "exam_type": r[9],
            "subject": r[10],
            "grade": r[11],
            "series": r[12],
        })

    return {"success": True, "images": images, "count": len(images)}


@router.get("/images/select", response_model=dict)
async def get_selected_question_images(
    year: int,
    subject: str,
    series: Optional[str] = None,
    count: int = 20,
    conn: psycopg.Connection = Depends(get_db_connection),
) -> dict:
    """선택 조건(연도/과목/회차)에 맞는 문제 이미지를 문항 번호 순서대로 반환합니다."""
    where_clauses = ["e.year = %s", "e.subject = %s"]
    params: List[Any] = [year, subject]

    if series:
        # 현재 exams.series 컬럼에는 월이 아닌 직렬명이 저장될 수 있어,
        # "N월" 형식은 image file_path의 폴더명(YYMMDD+...)에서 월을 추출해 필터링합니다.
        month_match = None
        try:
            if series.endswith("월"):
                month_match = int(series.replace("월", "").strip())
        except ValueError:
            month_match = None

        if month_match and 1 <= month_match <= 12:
            yy = str(year)[-2:]
            mm = f"{month_match:02d}"
            where_clauses.append(
                r"REPLACE(qi.file_path, '\\', '/') LIKE %s"
            )
            params.append(f"%/{yy}{mm}__+%")
        else:
            # 월 형식이 아닐 때는 기존 series 조건도 지원
            where_clauses.append("e.series = %s")
            params.append(series)

    where_sql = " AND ".join(where_clauses)
    limit_count = min(count, 100)

    with conn.cursor() as cur:
        # 1) 조건에 맞는 시험지 1개를 먼저 고정 (여러 시험 혼합 방지)
        cur.execute(
            f"""
            SELECT
                e.id,
                COUNT(DISTINCT q.id) AS q_count,
                BOOL_OR(REPLACE(qi.file_path, '\\', '/') LIKE %s) AS has_duplicated_folder
            FROM exams e
            JOIN questions q ON q.exam_id = e.id
            JOIN question_images qi ON qi.question_id = q.id
            WHERE {where_sql}
            GROUP BY e.id
            ORDER BY q_count DESC, has_duplicated_folder ASC, e.id ASC
            LIMIT 1
            """,
            ["%(2)/%", *params],
        )
        exam_row = cur.fetchone()

        if not exam_row:
            return {"success": True, "images": [], "count": 0}

        target_exam_id = exam_row[0]

        # 2) 고정된 시험지에서 문제 번호 순서대로 조회
        cur.execute(
            """
            WITH one_image_per_question AS (
                SELECT DISTINCT ON (q.id)
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
                FROM questions q
                JOIN question_images qi ON qi.question_id = q.id
                JOIN exams e ON q.exam_id = e.id
                WHERE q.exam_id = %s
                ORDER BY q.id, qi.id
            )
            SELECT *
            FROM one_image_per_question
            ORDER BY question_no ASC
            LIMIT %s
            """,
            (target_exam_id, limit_count),
        )
        rows = cur.fetchall()

    images = []
    for r in rows:
        coordinates_json = r[3] or {}
        question_nos = _resolve_question_nos(coordinates_json, r[5], r[2] or "")
        mapped_questions = _build_mapped_questions(
            conn=conn,
            exam_id=int(r[7]),
            question_nos=question_nos,
            fallback_question_id=int(r[1]),
            fallback_question_no=int(r[5]),
            fallback_answer_key=r[6],
        )
        images.append({
            "image_id": r[0],
            "question_id": r[1],
            "file_path": r[2],
            "coordinates_json": coordinates_json,
            "image_type": r[4],
            "question_no": r[5],
            "question_nos": question_nos,
            "mapped_questions": mapped_questions,
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

