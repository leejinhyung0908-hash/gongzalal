"""
6단계: FastAPI 랜덤 문제 풀이 API 서버

랜덤 문제 출제, 답안 제출, 풀이 로그 저장 API를 제공합니다.

기능:
- GET  /api/questions/random: 랜덤 문제 조회
- POST /api/questions/{id}/submit: 답안 제출 및 채점
- GET  /api/users/{id}/stats: 사용자 통계
- GET  /api/users/{id}/wrong-notes: 오답 노트

사용법:
    python step6_api_server.py
    uvicorn step6_api_server:app --reload
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import psycopg
from psycopg.rows import dict_row

from config import DATABASE_URL, CROP_OUTPUT_DIR, API_HOST, API_PORT


# ============================================================================
# Pydantic 모델
# ============================================================================

class QuestionResponse(BaseModel):
    """문제 응답."""
    id: int
    exam_id: int
    question_no: int
    question_text: Optional[str] = None
    image_path: Optional[str] = None
    image_url: Optional[str] = None
    options: Optional[Dict[str, str]] = None
    subject: Optional[str] = None
    year: Optional[int] = None


class SubmitRequest(BaseModel):
    """답안 제출 요청."""
    user_id: int
    selected_answer: str
    time_spent: int  # 초


class SubmitResponse(BaseModel):
    """답안 제출 응답."""
    is_correct: bool
    correct_answer: Optional[str] = None
    time_spent: int
    message: str


class UserStats(BaseModel):
    """사용자 통계."""
    total_solved: int
    correct_count: int
    accuracy_percent: float
    average_time_seconds: Optional[float] = None
    wrong_note_count: int


# ============================================================================
# FastAPI 앱
# ============================================================================

app = FastAPI(
    title="YOLO Quiz API",
    description="YOLO 기반 기출 문항 랜덤 풀이 서비스",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 서빙 (크롭 이미지)
if CROP_OUTPUT_DIR.exists():
    app.mount("/images", StaticFiles(directory=str(CROP_OUTPUT_DIR)), name="images")


def get_db():
    """DB 연결."""
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


# ============================================================================
# API 엔드포인트
# ============================================================================

@app.get("/")
async def root():
    """루트 엔드포인트."""
    return {"message": "YOLO Quiz API", "docs": "/docs"}


@app.get("/api/questions/random", response_model=QuestionResponse)
async def get_random_question(
    subject: Optional[str] = Query(None, description="과목 필터"),
    year: Optional[int] = Query(None, description="연도 필터"),
    exclude_ids: Optional[str] = Query(None, description="제외할 문제 ID (쉼표 구분)")
):
    """랜덤 문제 조회.

    Args:
        subject: 과목 필터
        year: 연도 필터
        exclude_ids: 이미 푼 문제 ID 제외

    Returns:
        랜덤 문제
    """
    conn = get_db()

    try:
        with conn.cursor() as cur:
            # 쿼리 조건 구성
            conditions = []
            params = []

            if subject:
                conditions.append("e.subject = %s")
                params.append(subject)

            if year:
                conditions.append("e.year = %s")
                params.append(year)

            if exclude_ids:
                ids = [int(x.strip()) for x in exclude_ids.split(",") if x.strip()]
                if ids:
                    placeholders = ",".join(["%s"] * len(ids))
                    conditions.append(f"q.id NOT IN ({placeholders})")
                    params.extend(ids)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            # 랜덤 문제 조회
            query = f"""
                SELECT
                    q.id, q.exam_id, q.question_no, q.question_text, q.answer_key,
                    q.extra_json,
                    e.subject, e.year,
                    qi.file_path
                FROM questions q
                JOIN exams e ON q.exam_id = e.id
                LEFT JOIN question_images qi ON q.id = qi.question_id
                {where_clause}
                ORDER BY RANDOM()
                LIMIT 1
            """

            cur.execute(query, params)
            row = cur.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")

            # 이미지 URL 생성
            image_url = None
            if row["file_path"]:
                # 상대 경로로 변환
                file_path = Path(row["file_path"])
                if file_path.is_relative_to(CROP_OUTPUT_DIR):
                    rel_path = file_path.relative_to(CROP_OUTPUT_DIR)
                else:
                    rel_path = file_path.name
                image_url = f"/images/{rel_path}"

            # 옵션 추출
            options = None
            if row["extra_json"] and isinstance(row["extra_json"], dict):
                options = row["extra_json"].get("options")

            return QuestionResponse(
                id=row["id"],
                exam_id=row["exam_id"],
                question_no=row["question_no"],
                question_text=row["question_text"],
                image_path=row["file_path"],
                image_url=image_url,
                options=options,
                subject=row["subject"],
                year=row["year"],
            )

    finally:
        conn.close()


@app.post("/api/questions/{question_id}/submit", response_model=SubmitResponse)
async def submit_answer(question_id: int, request: SubmitRequest):
    """답안 제출 및 채점.

    Args:
        question_id: 문제 ID
        request: 제출 요청

    Returns:
        채점 결과
    """
    conn = get_db()

    try:
        with conn.cursor() as cur:
            # 정답 조회
            cur.execute(
                "SELECT answer_key FROM questions WHERE id = %s",
                (question_id,)
            )
            row = cur.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")

            correct_answer = row["answer_key"]
            is_correct = str(request.selected_answer).strip() == str(correct_answer).strip() if correct_answer else None

            # 풀이 로그 저장
            cur.execute(
                """
                INSERT INTO user_solving_logs (
                    user_id, question_id, selected_answer, time_spent, is_wrong_note
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    request.user_id,
                    question_id,
                    request.selected_answer,
                    request.time_spent,
                    not is_correct if is_correct is not None else False
                )
            )
            conn.commit()

            # 응답 메시지
            if is_correct is None:
                message = "답안이 제출되었습니다. (정답 미등록)"
            elif is_correct:
                message = "🎉 정답입니다!"
            else:
                message = f"❌ 오답입니다. 정답: {correct_answer}"

            return SubmitResponse(
                is_correct=is_correct if is_correct is not None else False,
                correct_answer=correct_answer,
                time_spent=request.time_spent,
                message=message,
            )

    finally:
        conn.close()


@app.get("/api/users/{user_id}/stats", response_model=UserStats)
async def get_user_stats(user_id: int):
    """사용자 풀이 통계 조회.

    Args:
        user_id: 사용자 ID

    Returns:
        통계 정보
    """
    conn = get_db()

    try:
        with conn.cursor() as cur:
            # 총 풀이 수
            cur.execute(
                "SELECT COUNT(*) as cnt FROM user_solving_logs WHERE user_id = %s",
                (user_id,)
            )
            total = cur.fetchone()["cnt"]

            # 정답 수
            cur.execute(
                """
                SELECT COUNT(*) as cnt
                FROM user_solving_logs l
                JOIN questions q ON l.question_id = q.id
                WHERE l.user_id = %s AND l.selected_answer = q.answer_key
                """,
                (user_id,)
            )
            correct = cur.fetchone()["cnt"]

            # 평균 시간
            cur.execute(
                """
                SELECT AVG(time_spent) as avg_time
                FROM user_solving_logs
                WHERE user_id = %s AND time_spent IS NOT NULL
                """,
                (user_id,)
            )
            avg_time = cur.fetchone()["avg_time"]

            # 오답 노트 수
            cur.execute(
                "SELECT COUNT(*) as cnt FROM user_solving_logs WHERE user_id = %s AND is_wrong_note = TRUE",
                (user_id,)
            )
            wrong_notes = cur.fetchone()["cnt"]

            accuracy = (correct / total * 100) if total > 0 else 0

            return UserStats(
                total_solved=total,
                correct_count=correct,
                accuracy_percent=round(accuracy, 2),
                average_time_seconds=round(avg_time, 2) if avg_time else None,
                wrong_note_count=wrong_notes,
            )

    finally:
        conn.close()


@app.get("/api/subjects")
async def get_subjects():
    """과목 목록 조회."""
    conn = get_db()

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT subject FROM exams WHERE subject IS NOT NULL ORDER BY subject"
            )
            rows = cur.fetchall()
            return {"subjects": [row["subject"] for row in rows]}

    finally:
        conn.close()


@app.get("/api/years")
async def get_years():
    """연도 목록 조회."""
    conn = get_db()

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT year FROM exams ORDER BY year DESC"
            )
            rows = cur.fetchall()
            return {"years": [row["year"] for row in rows]}

    finally:
        conn.close()


# ============================================================================
# 메인
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print("=" * 50)
    print(" 🚀 YOLO Quiz API Server")
    print("=" * 50)
    print(f"\n서버 주소: http://{API_HOST}:{API_PORT}")
    print(f"API 문서: http://localhost:{API_PORT}/docs")

    uvicorn.run(app, host=API_HOST, port=API_PORT)


