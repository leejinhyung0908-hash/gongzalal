"""시험(Exams) 및 문제(Questions) 라우터.

새 테이블 구조:
- Exams: 시험 메타데이터 (연도, 유형, 시리즈, 등급, 과목)
- Questions: 개별 문제 (exam_id FK로 연결)
"""

from __future__ import annotations

import re
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, TypedDict

import psycopg
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END, START

from backend.dependencies import get_db_connection
from backend.domain.admin.hub.orchestrators.exam_flow import ExamFlow
from backend.domain.admin.models.transfers.exam_transfer import (
    ExamTransfer,
    ExamCreateRequest,
    ExamSearchRequest,
)
from backend.domain.admin.models.transfers.question_transfer import (
    QuestionTransfer,
    QuestionCreateRequest,
    QuestionSearchRequest,
)


router = APIRouter(tags=["exam"])
logger = logging.getLogger(__name__)

# Orchestrator 인스턴스 (싱글톤 패턴)
_flow = ExamFlow()


# ============================================================================
# Request/Response 모델
# ============================================================================

class ExamAnswerRequest(BaseModel):
    question: str = Field(..., description="사용자 질문(예: 작년 한국사 3번 문제 정답 뭐야?)")


class ExamAnswerResponse(BaseModel):
    year: int
    exam_type: str
    series: Optional[str]
    grade: str
    subject: str
    question_no: int
    answer_key: str


class ExamAnswerTextResponse(BaseModel):
    answer: str
    meta: ExamAnswerResponse


# ============================================================================
# 파싱 유틸리티
# ============================================================================

def _resolve_relative_year(text: str, now_year: int) -> Optional[int]:
    """텍스트에서 연도 추출."""
    m = re.search(r"(?:(20)?(\d{2}))\s*년", text)
    if m:
        y2 = int(m.group(2))
        return 2000 + y2
    if "올해" in text:
        return now_year
    if "작년" in text:
        return now_year - 1
    if "재작년" in text or "그저께" in text:
        return now_year - 2
    return None


def _parse_exam_type(text: str) -> Optional[str]:
    """텍스트에서 시험 유형 추출."""
    if "국가직" in text:
        return "국가직"
    if "지방직" in text or "지방" in text:
        return "지방직"
    return None


def _parse_grade(text: str) -> str:
    """텍스트에서 급수 추출."""
    m = re.search(r"(\d)\s*급", text)
    if m:
        return f"{m.group(1)}급"
    return "9급"


def _parse_question_no(text: str) -> Optional[int]:
    """텍스트에서 문항 번호 추출."""
    m = re.search(r"(\d{1,3})\s*번", text)
    if not m:
        return None
    return int(m.group(1))


def _parse_series(text: str) -> Optional[str]:
    """텍스트에서 시리즈(직렬) 추출."""
    m = re.search(r"([가-힣]+행정직)", text)
    if m:
        return m.group(1)
    if "교육행정" in text:
        return "교육행정직"
    if "일반행정" in text:
        return "일반행정직"
    return None


def _get_distinct_values(conn: psycopg.Connection) -> Dict[str, List[str]]:
    """DB에서 distinct 값들 조회 (새 스키마)."""
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT subject FROM exams ORDER BY subject")
        subjects = [r[0] for r in cur.fetchall() if r and r[0]]
        cur.execute("SELECT DISTINCT series FROM exams ORDER BY series")
        series_list = [r[0] for r in cur.fetchall() if r and r[0]]
        cur.execute("SELECT DISTINCT exam_type FROM exams ORDER BY exam_type")
        exam_types = [r[0] for r in cur.fetchall() if r and r[0]]
    return {"subjects": subjects, "series": series_list, "exam_types": exam_types}


def _pick_first_contained(text: str, candidates: List[str]) -> Optional[str]:
    """텍스트에 포함된 첫 번째 후보 반환."""
    for c in candidates:
        if c and c in text:
            return c
    return None


def _fetch_answer_rows(
    conn: psycopg.Connection,
    *,
    year: int,
    exam_type: str,
    grade: str,
    subject: str,
    question_no: int,
    series: Optional[str],
) -> List[Dict[str, Any]]:
    """문제 정답 조회 (새 스키마: exams + questions JOIN)."""
    if series:
        sql = """
            SELECT e.year, e.exam_type, e.series, e.grade, e.subject, q.question_no, q.answer_key
            FROM questions q
            JOIN exams e ON q.exam_id = e.id
            WHERE e.year=%s AND e.exam_type=%s AND e.series=%s AND e.grade=%s
                  AND e.subject=%s AND q.question_no=%s
            ORDER BY e.series
            LIMIT 10
        """
        params = (year, exam_type, series, grade, subject, question_no)
    else:
        sql = """
            SELECT e.year, e.exam_type, e.series, e.grade, e.subject, q.question_no, q.answer_key
            FROM questions q
            JOIN exams e ON q.exam_id = e.id
            WHERE e.year=%s AND e.exam_type=%s AND e.grade=%s
                  AND e.subject=%s AND q.question_no=%s
            ORDER BY e.series
            LIMIT 10
        """
        params = (year, exam_type, grade, subject, question_no)

    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append({
            "year": int(r[0]),
            "exam_type": str(r[1]),
            "series": str(r[2]) if r[2] else None,
            "grade": str(r[3]),
            "subject": str(r[4]),
            "question_no": int(r[5]),
            "answer_key": str(r[6]),
        })
    return out


# ============================================================================
# Exam 엔드포인트
# ============================================================================

@router.post("/", response_model=dict)
async def create_exam(
    request: ExamCreateRequest,
    conn: psycopg.Connection = Depends(get_db_connection)
) -> dict:
    """시험 생성 엔드포인트."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO exams (year, exam_type, series, grade, subject)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, year, exam_type, series, grade, subject, created_at, updated_at
                """,
                (request.year, request.exam_type, request.series, request.grade, request.subject),
            )
            row = cur.fetchone()
            conn.commit()

        return {
            "success": True,
            "exam": ExamTransfer(
                id=row[0],
                year=row[1],
                exam_type=row[2],
                series=row[3],
                grade=row[4],
                subject=row[5],
                created_at=row[6],
                updated_at=row[7],
            ).model_dump(),
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"시험 생성 실패: {str(e)}")


@router.get("/{exam_id}", response_model=dict)
async def get_exam(
    exam_id: int,
    conn: psycopg.Connection = Depends(get_db_connection)
) -> dict:
    """시험 조회 엔드포인트."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, year, exam_type, series, grade, subject, created_at, updated_at
            FROM exams WHERE id = %s
            """,
            (exam_id,),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="시험을 찾을 수 없습니다.")

    return {
        "success": True,
        "exam": ExamTransfer(
            id=row[0],
            year=row[1],
            exam_type=row[2],
            series=row[3],
            grade=row[4],
            subject=row[5],
            created_at=row[6],
            updated_at=row[7],
        ).model_dump(),
    }


@router.post("/search", response_model=dict)
async def search_exams(
    request: ExamSearchRequest,
    conn: psycopg.Connection = Depends(get_db_connection)
) -> dict:
    """시험 검색 엔드포인트."""
    conditions = []
    params = []

    if request.year:
        conditions.append("year = %s")
        params.append(request.year)
    if request.exam_type:
        conditions.append("exam_type = %s")
        params.append(request.exam_type)
    if request.series:
        conditions.append("series = %s")
        params.append(request.series)
    if request.grade:
        conditions.append("grade = %s")
        params.append(request.grade)
    if request.subject:
        conditions.append("subject ILIKE %s")
        params.append(f"%{request.subject}%")

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    params.extend([request.limit, request.offset])

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT id, year, exam_type, series, grade, subject, created_at, updated_at
            FROM exams
            WHERE {where_clause}
            ORDER BY year DESC, exam_type, subject
            LIMIT %s OFFSET %s
            """,
            params,
        )
        rows = cur.fetchall()

    exams = [
        ExamTransfer(
            id=r[0], year=r[1], exam_type=r[2], series=r[3],
            grade=r[4], subject=r[5], created_at=r[6], updated_at=r[7],
        ).model_dump()
        for r in rows
    ]

    return {"success": True, "exams": exams, "count": len(exams)}


# ============================================================================
# 기존 호환 엔드포인트 (정답 조회)
# ============================================================================

@router.post("/answer", response_model=ExamAnswerResponse)
async def get_exam_answer(
    req: ExamAnswerRequest, conn: psycopg.Connection = Depends(get_db_connection)
) -> ExamAnswerResponse:
    """문제 정답 조회 엔드포인트."""
    q = req.question.strip()
    if not q:
        raise HTTPException(status_code=400, detail="질문이 비어있습니다.")

    now_year = datetime.now().year
    year = _resolve_relative_year(q, now_year) or now_year
    exam_type = _parse_exam_type(q) or "지방직"
    grade = _parse_grade(q)
    qno = _parse_question_no(q)
    series = _parse_series(q)

    distinct = _get_distinct_values(conn)
    subject = _pick_first_contained(q, distinct["subjects"])
    if subject is None:
        raise HTTPException(
            status_code=400,
            detail=f"과목명을 인식하지 못했습니다. 가능한 과목: {', '.join(distinct['subjects'][:30])}",
        )
    if qno is None:
        raise HTTPException(status_code=400, detail="문항 번호를 인식하지 못했습니다. (예: 3번)")

    rows = _fetch_answer_rows(
        conn,
        year=year,
        exam_type=exam_type,
        grade=grade,
        subject=subject,
        question_no=qno,
        series=series,
    )
    if not rows:
        raise HTTPException(
            status_code=404,
            detail="해당 조건의 문항을 찾지 못했습니다. (연도, 시험구분, 직렬, 급수, 과목, 문항을 기입해서 알려주세요. 예: 25년 지방 일반행정 9급 한국사 17번)",
        )

    if series is None and len({r["series"] for r in rows if r["series"]}) > 1:
        opts = sorted({r["series"] for r in rows if r["series"]})
        raise HTTPException(
            status_code=409,
            detail=f"직렬을 특정할 수 없습니다. 질문에 직렬을 포함해 주세요. 예: {', '.join(opts)}",
        )

    row = rows[0]
    return ExamAnswerResponse(
        year=int(row["year"]),
        exam_type=str(row["exam_type"]),
        series=row["series"],
        grade=str(row["grade"]),
        subject=str(row["subject"]),
        question_no=int(row["question_no"]),
        answer_key=str(row["answer_key"]),
    )


@router.post("/answer_text", response_model=ExamAnswerTextResponse)
async def get_exam_answer_text(
    req: ExamAnswerRequest, conn: psycopg.Connection = Depends(get_db_connection)
) -> ExamAnswerTextResponse:
    """문제 정답 텍스트 응답 엔드포인트."""
    meta = await get_exam_answer(req, conn)
    series_str = f" {meta.series}" if meta.series else ""
    answer = (
        f"{meta.year}년 {meta.exam_type} {meta.grade}{series_str} "
        f"{meta.subject} {meta.question_no}번 정답은 {meta.answer_key}번입니다."
    )
    return ExamAnswerTextResponse(answer=answer, meta=meta)


@router.get("/catalog")
async def get_exam_catalog(conn: psycopg.Connection = Depends(get_db_connection)):
    """DB에 적재된 시험 메타 카탈로그(과목/시리즈/시험구분/연도)를 반환."""
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT year FROM exams ORDER BY year DESC")
        years = [int(r[0]) for r in cur.fetchall() if r and r[0] is not None]
        cur.execute("SELECT DISTINCT exam_type FROM exams ORDER BY exam_type")
        exam_types = [str(r[0]) for r in cur.fetchall() if r and r[0]]
        cur.execute("SELECT DISTINCT series FROM exams ORDER BY series")
        series_list = [str(r[0]) for r in cur.fetchall() if r and r[0]]
        cur.execute("SELECT DISTINCT subject FROM exams ORDER BY subject")
        subjects = [str(r[0]) for r in cur.fetchall() if r and r[0]]
    return {"years": years, "exam_types": exam_types, "series": series_list, "subjects": subjects}


# ============================================================================
# JSONL 업로드 및 Flow 처리
# ============================================================================

@router.post("/upload-jsonl")
async def upload_jsonl_file(
    file: UploadFile = File(...),
    category: str = "exam"
) -> dict:
    """JSONL 파일 업로드 및 ExamFlow 처리 엔드포인트."""
    try:
        print(f"[ExamRouter] >>> /upload-jsonl 호출됨: filename={getattr(file, 'filename', None)}", flush=True)

        if not file.filename or not file.filename.endswith(".jsonl"):
            raise HTTPException(status_code=400, detail="JSONL 파일만 업로드할 수 있습니다.")

        contents = await file.read()
        text = contents.decode("utf-8")
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        parsed_items: List[Dict[str, Any]] = []
        all_parsed_data: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []

        for i, line in enumerate(lines, start=1):
            try:
                item = json.loads(line)
                all_parsed_data.append({"line_number": i, "data": item})
                if i <= 5:
                    parsed_items.append({"line_number": i, "data": item})
            except json.JSONDecodeError as e:
                errors.append({"line": i, "error": str(e)})

        if category == "commentary":
            raise HTTPException(
                status_code=400,
                detail="commentary 카테고리는 /api/v1/admin/commentaries/upload-jsonl 사용"
            )

        # ExamFlow로 데이터 전달
        flow_result: Dict[str, Any] | None = None
        try:
            jsonl_data = [item["data"] for item in all_parsed_data]
            flow_result = await _flow.process_jsonl_data(
                jsonl_data=jsonl_data,
                category=category,
                filename=file.filename or "unknown.jsonl"
            )
        except Exception as flow_error:
            logger.warning(f"[ExamRouter] ExamFlow 처리 중 오류: {flow_error}")

        # LangGraph 처리 (미리보기용)
        class JsonlProcessingState(TypedDict):
            items: List[Dict[str, Any]]
            category: str
            processed_items: List[Dict[str, Any]]
            errors: List[Dict[str, Any]]

        def process_items_node(state: JsonlProcessingState) -> JsonlProcessingState:
            processed = [
                {
                    "line_number": idx,
                    "category": state['category'],
                    "data": item_data,
                    "processed_at": datetime.now().isoformat(),
                }
                for idx, item_data in enumerate(state['items'], start=1)
            ]
            return {**state, "processed_items": processed}

        def validate_items_node(state: JsonlProcessingState) -> JsonlProcessingState:
            validated = [item for item in state['processed_items'] if item.get("data")]
            return {**state, "processed_items": validated}

        graph = StateGraph(JsonlProcessingState)
        graph.add_node("process", process_items_node)
        graph.add_node("validate", validate_items_node)
        graph.add_edge(START, "process")
        graph.add_edge("process", "validate")
        graph.add_edge("validate", END)

        compiled_graph = graph.compile()
        initial_state: JsonlProcessingState = {
            "items": [item["data"] for item in parsed_items],
            "category": category,
            "processed_items": [],
            "errors": errors
        }
        final_state = compiled_graph.invoke(initial_state)

        response: Dict[str, Any] = {
            "success": True if flow_result is None else bool(flow_result.get("success", True)),
            "filename": file.filename,
            "category": category,
            "total_lines": len(lines),
            "parsed_items": parsed_items,
            "processed_items": final_state.get("processed_items", []),
            "errors": final_state.get("errors") if final_state.get("errors") else None,
            "message": (
                flow_result.get("message") if isinstance(flow_result, dict) and flow_result.get("message")
                else f"총 {len(lines)}개 라인 처리 완료"
            ),
        }

        if isinstance(flow_result, dict):
            response["flow_result"] = flow_result

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ExamRouter] 파일 업로드 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"파일 처리 중 오류: {str(e)}")


@router.post("/flow", response_model=dict)
async def process_exam_flow(request: ExamAnswerRequest) -> dict:
    """Exam 요청 처리 엔드포인트 (KoELECTRA 기반 분기)."""
    try:
        request_text = request.question
        if not isinstance(request_text, str):
            request_text = str(request_text)

        result = await _flow.process_exam_request(request_text, request.model_dump())

        if not result.get("success", False):
            raise HTTPException(status_code=400, detail=result.get("error", "처리 실패"))

        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[ExamRouter] 오류 발생: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(exc)}")


# ============================================================================
# 임베딩 관련 엔드포인트
# ============================================================================

class EmbeddingEnqueueRequest(BaseModel):
    """임베딩 작업 큐 추가 요청."""
    batch_size: int = Field(default=100, ge=1, le=1000, description="배치 크기")


@router.post("/enqueue-embeddings")
async def enqueue_embeddings(
    request: EmbeddingEnqueueRequest = EmbeddingEnqueueRequest(),
    conn: psycopg.Connection = Depends(get_db_connection)
) -> dict:
    """임베딩 작업을 큐에 추가하는 엔드포인트 (새 스키마)."""
    try:
        # 임베딩이 필요한 시험 수 확인 (exam_vector가 NULL인 것)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM exams WHERE exam_vector IS NULL")
            exam_count = cur.fetchone()[0]

        if exam_count == 0:
            return {
                "success": True,
                "message": "임베딩이 필요한 시험이 없습니다.",
                "processed_count": 0,
                "total_count": 0,
                "mode": "none"
            }

        # KURE-v1으로 직접 임베딩 생성
        from backend.core.utils.embedding import generate_embedding

        processed_count = 0
        errors = []

        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, year, exam_type, series, grade, subject
                FROM exams
                WHERE exam_vector IS NULL
                LIMIT %s
            """, (request.batch_size,))
            rows = cur.fetchall()

        for row in rows:
            try:
                exam_id = row[0]
                embedding_text = f"{row[1]}년 {row[2]} {row[3] or ''} {row[4]} {row[5]}"
                embedding_vector = generate_embedding(embedding_text)
                embedding_str = "[" + ",".join(map(str, embedding_vector)) + "]"

                with conn.cursor() as update_cur:
                    update_cur.execute("""
                        UPDATE exams SET exam_vector = %s::vector, updated_at = now()
                        WHERE id = %s
                    """, (embedding_str, exam_id))

                conn.commit()
                processed_count += 1

            except Exception as e:
                logger.error(f"[ExamRouter] 시험 {row[0]} 임베딩 실패: {e}")
                errors.append({"exam_id": row[0], "error": str(e)})
                conn.rollback()

        return {
            "success": True,
            "message": f"{processed_count}개 시험의 임베딩을 생성했습니다.",
            "processed_count": processed_count,
            "total_count": len(rows),
            "errors": errors if errors else None,
            "mode": "direct"
        }

    except Exception as e:
        logger.error(f"[ExamRouter] 임베딩 큐 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"임베딩 큐 추가 오류: {str(e)}")


@router.get("/embedding-status")
async def get_embedding_status(conn: psycopg.Connection = Depends(get_db_connection)) -> dict:
    """임베딩 작업 상태 조회 엔드포인트."""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM exams WHERE exam_vector IS NULL")
            remaining_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM exams")
            total_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM exams WHERE exam_vector IS NOT NULL")
            processed_count = cur.fetchone()[0]

        return {
            "is_complete": remaining_count == 0,
            "processed_count": processed_count,
            "total_count": total_count,
            "remaining_count": remaining_count,
            "message": "완료" if remaining_count == 0 else f"{remaining_count}개 시험 남음"
        }

    except Exception as e:
        logger.error(f"[ExamRouter] 상태 조회 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"상태 조회 오류: {str(e)}")
