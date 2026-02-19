#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSONL(문항/정답) → Neon(Postgres) exam_questions 테이블 적재 스크립트

PowerShell 예시:
  python -m backend.tools.ingest_exam_questions_to_neon `
    --jsonl "data/gongmuwon/dataset/all_subjects_from_md.jsonl" `
    --year 2025 `
    --exam-type "지방직" `
    --job-series "일반행정직" `
    --grade "9급"

NOTE:
- 책형은 구분하지 않으므로 저장/조회에서 제외.
- embedding은 지금 단계에서는 NULL로 두고, 추후 배치로 채우는 것을 권장.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import psycopg

from backend.dependencies import connect_db, setup_schema
from backend.config import settings


def _iter_jsonl(path: str) -> Iterable[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _parse_source_md(source_md: str) -> Dict[str, Any]:
    """source_md 파일명에서 메타데이터 추출

    예: "250621+지방+9급+교육학개론-B.md"
    → {"year": 2025, "exam_type": "지방직", "grade": "9급", "subject": "교육학개론"}
    """
    import re
    from datetime import datetime

    if not source_md:
        return {}

    # 파일명에서 정보 추출
    # 형식: YYMMDD+exam_type+grade+subject-B.md
    parts = source_md.replace(".md", "").split("+")

    result = {}

    # 날짜 추출 (첫 번째 부분: YYMMDD)
    if parts and len(parts[0]) >= 6:
        date_str = parts[0]
        try:
            # YYMMDD 형식 파싱
            year_2digit = int(date_str[:2])
            month = int(date_str[2:4])
            day = int(date_str[4:6])

            # 2000년대 가정 (2025년 = 25)
            if year_2digit < 50:
                year = 2000 + year_2digit
            else:
                year = 1900 + year_2digit

            result["year"] = year
        except (ValueError, IndexError):
            pass

    # exam_type 추출
    if len(parts) > 1:
        exam_type_raw = parts[1].strip()
        if "지방" in exam_type_raw:
            result["exam_type"] = "지방직"
        elif "국가" in exam_type_raw:
            result["exam_type"] = "국가직"

    # grade 추출
    if len(parts) > 2:
        grade_raw = parts[2].strip()
        if "9급" in grade_raw:
            result["grade"] = "9급"
        elif "7급" in grade_raw:
            result["grade"] = "7급"
        elif "5급" in grade_raw:
            result["grade"] = "5급"

    # subject는 이미 JSONL에 있으므로 여기서는 추출하지 않음

    return result


def ingest(
    conn: psycopg.Connection,
    rows: Iterable[Dict[str, Any]],
    *,
    year: int = None,
    exam_type: str = None,
    job_series: str = None,
    grade: str = None,
    exam_name: str = None,
    auto_parse_source_md: bool = True,
    batch_size: int = 200,
) -> int:
    """JSONL 데이터를 exam_questions 테이블에 삽입

    Args:
        conn: DB 연결
        rows: JSONL 행 데이터
        year: 연도 (auto_parse_source_md=True이면 source_md에서 추출)
        exam_type: 시험 구분 (auto_parse_source_md=True이면 source_md에서 추출)
        job_series: 직렬 (기본값: "일반행정직")
        grade: 급수 (auto_parse_source_md=True이면 source_md에서 추출)
        exam_name: 시험명 (기본값: "지방공무원 공개경쟁임용")
        auto_parse_source_md: source_md에서 메타데이터 자동 추출 여부
        batch_size: 배치 크기
    """
    # ON CONFLICT 없이 먼저 시도 (중복은 무시)
    # 먼저 constraint 확인
    with conn.cursor() as cur:
        cur.execute("""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'exam_questions'
            AND constraint_type = 'UNIQUE'
        """)
        constraints = [row[0] for row in cur.fetchall()]

    # ON CONFLICT 절 구성
    if constraints:
        # constraint가 있으면 사용
        constraint_name = constraints[0] if constraints else None
        conflict_clause = f"ON CONFLICT ON CONSTRAINT {constraint_name}" if constraint_name else ""
    else:
        # constraint가 없으면 컬럼 목록 사용
        conflict_clause = "ON CONFLICT (year, exam_type, job_series, grade, subject, question_no)"

    sql = f"""
    INSERT INTO exam_questions (
      year, exam_type, job_series, grade, exam_name,
      subject, question_no, source_md, source_pdf,
      question_text, answer_key, extra_json, embedding
    )
    VALUES (
      %(year)s, %(exam_type)s, %(job_series)s, %(grade)s, %(exam_name)s,
      %(subject)s, %(question_no)s, %(source_md)s, %(source_pdf)s,
      %(question_text)s, %(answer_key)s, %(extra_json)s::jsonb, %(embedding)s
    )
    {conflict_clause}
    DO UPDATE SET
      exam_name = EXCLUDED.exam_name,
      source_md = EXCLUDED.source_md,
      source_pdf = EXCLUDED.source_pdf,
      question_text = EXCLUDED.question_text,
      answer_key = EXCLUDED.answer_key,
      extra_json = EXCLUDED.extra_json,
      embedding = COALESCE(EXCLUDED.embedding, exam_questions.embedding),
      updated_at = now()
    ;
    """

    buf: List[Dict[str, Any]] = []
    total = 0

    def _flush() -> None:
        nonlocal total, buf
        if not buf:
            return
        with conn.cursor() as cur:
            cur.executemany(sql, buf)
        conn.commit()
        total += len(buf)
        buf = []

    for r in rows:
        qno = int(str(r.get("id", "")).strip())

        # source_md에서 메타데이터 추출
        parsed = {}
        if auto_parse_source_md and r.get("source_md"):
            parsed = _parse_source_md(r.get("source_md"))

        # 기본값 설정
        payload = {
            "year": parsed.get("year") or year or 2025,
            "exam_type": parsed.get("exam_type") or exam_type or "지방직",
            "job_series": job_series or "일반행정직",
            "grade": parsed.get("grade") or grade or "9급",
            "exam_name": exam_name or "지방공무원 공개경쟁임용",
            "subject": str(r.get("subject") or "").strip(),
            "question_no": qno,
            "source_md": r.get("source_md"),
            "source_pdf": r.get("source_pdf"),
            "question_text": str(r.get("question") or "").strip(),
            "answer_key": str(r.get("answer") or "").strip(),
            "extra_json": json.dumps({}),  # JSONB는 JSON 문자열로 전달
            "embedding": None,
        }
        buf.append(payload)
        if len(buf) >= batch_size:
            _flush()

    _flush()
    return total


def main() -> int:
    ap = argparse.ArgumentParser(description="JSONL 문항/정답을 Neon exam_questions에 적재합니다.")
    ap.add_argument("--jsonl", required=True, help="입력 JSONL 경로")
    ap.add_argument("--year", type=int, default=None, help="연도 (예: 2025, source_md에서 자동 추출 가능)")
    ap.add_argument("--exam-type", default=None, help="시험 구분 (예: 국가직/지방직, source_md에서 자동 추출 가능)")
    ap.add_argument("--job-series", default="일반행정직", help="직렬 (예: 교육행정직/일반행정직, 기본: 일반행정직)")
    ap.add_argument("--grade", default=None, help="급수 (기본: source_md에서 자동 추출 또는 9급)")
    ap.add_argument("--exam-name", default="지방공무원 공개경쟁임용", help="시험명(표시용)")
    ap.add_argument("--batch-size", type=int, default=200, help="배치 크기")
    ap.add_argument("--no-auto-parse", action="store_true", help="source_md 자동 파싱 비활성화")
    ap.add_argument("--database-url", default=None, help="옵션: DATABASE_URL 오버라이드")
    args = ap.parse_args()

    db_url = args.database_url or os.getenv("DATABASE_URL") or settings.DATABASE_URL
    conn = connect_db(db_url)
    setup_schema(conn)

    n = ingest(
        conn,
        _iter_jsonl(args.jsonl),
        year=args.year,
        exam_type=args.exam_type,
        job_series=args.job_series,
        grade=args.grade,
        exam_name=args.exam_name,
        auto_parse_source_md=not args.no_auto_parse,
        batch_size=args.batch_size,
    )
    print(f"[OK] upsert {n} rows into exam_questions")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


