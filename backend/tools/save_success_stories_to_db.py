#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
합격수기 데이터를 Neon DB에 저장하는 스크립트

선택사항: DB에 저장하면 나중에 검색/필터링이 가능하지만,
학습용 데이터셋은 CSV/JSONL로도 충분합니다.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import psycopg
from backend.dependencies import connect_db
from backend.config import settings


def create_success_stories_table(conn: psycopg.Connection) -> None:
    """합격수기 테이블 생성 (이미 존재하면 스킵)"""
    with conn.cursor() as cur:
        # 테이블 생성
        cur.execute("""
            CREATE TABLE IF NOT EXISTS success_stories (
                id SERIAL PRIMARY KEY,
                year INTEGER,
                exam_type VARCHAR(50),
                grade VARCHAR(10),
                job_series VARCHAR(100),
                subjects TEXT[],
                study_period VARCHAR(100),
                study_hours VARCHAR(100),
                review_count VARCHAR(100),
                book_count VARCHAR(100),
                daily_plan TEXT,
                subject_methods JSONB,
                interview_prep TEXT,
                difficulties TEXT,
                key_points TEXT,
                raw_text TEXT,
                source_url TEXT,
                source_file TEXT,
                crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 인덱스 생성
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_success_stories_year
            ON success_stories(year)
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_success_stories_exam_type
            ON success_stories(exam_type)
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_success_stories_job_series
            ON success_stories(job_series)
        """)

        conn.commit()
        print("[DB] success_stories 테이블 생성 완료")


def create_advice_qa_table(conn: psycopg.Connection) -> None:
    """학습 상담 Q&A 테이블 생성"""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS advice_qa (
                id SERIAL PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                category VARCHAR(50),
                year INTEGER,
                exam_type VARCHAR(50),
                grade VARCHAR(10),
                job_series VARCHAR(100),
                subjects TEXT[],
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 인덱스 생성
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_advice_qa_category
            ON advice_qa(category)
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_advice_qa_year
            ON advice_qa(year)
        """)

        # 벡터 검색을 위한 embedding 컬럼 (선택사항)
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_attribute
                    WHERE attrelid = 'advice_qa'::regclass
                    AND attname = 'embedding'
                ) THEN
                    ALTER TABLE advice_qa ADD COLUMN embedding vector(768);
                    CREATE INDEX IF NOT EXISTS idx_advice_qa_embedding
                    ON advice_qa USING ivfflat (embedding vector_cosine_ops);
                END IF;
            END $$;
        """)

        conn.commit()
        print("[DB] advice_qa 테이블 생성 완료")


def save_stories_to_db(
    conn: psycopg.Connection,
    stories: List[Dict[str, Any]],
    batch_size: int = 50
) -> int:
    """합격수기 데이터를 DB에 저장"""
    create_success_stories_table(conn)

    saved_count = 0

    with conn.cursor() as cur:
        for story in stories:
            exam_info = story.get("exam_info", {})
            study_style = story.get("study_style", {})

            # subjects 배열 처리
            subjects = exam_info.get("subjects", [])
            if isinstance(subjects, str):
                subjects = [subjects] if subjects else []

            # subject_methods JSON 처리
            subject_methods = story.get("subject_methods", {})
            if isinstance(subject_methods, str):
                try:
                    subject_methods = json.loads(subject_methods)
                except:
                    subject_methods = {}

            try:
                cur.execute("""
                    INSERT INTO success_stories (
                        year, exam_type, grade, job_series, subjects,
                        study_period, study_hours, review_count, book_count,
                        daily_plan, subject_methods, interview_prep, difficulties,
                        key_points, raw_text, source_url, source_file, crawled_at
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                    ON CONFLICT DO NOTHING
                """, (
                    exam_info.get("year"),
                    exam_info.get("exam_type"),
                    exam_info.get("grade"),
                    exam_info.get("job_series"),
                    subjects if subjects else None,
                    study_style.get("총 수험기간"),
                    study_style.get("평균 학습 시간"),
                    study_style.get("평균 회독수"),
                    study_style.get("평균 문제집 권수"),
                    story.get("daily_plan"),
                    json.dumps(subject_methods, ensure_ascii=False) if subject_methods else None,
                    story.get("interview_prep"),
                    story.get("difficulties"),
                    story.get("key_points"),
                    story.get("raw_text"),
                    story.get("source_url"),
                    story.get("source_file"),
                    story.get("crawled_at")
                ))
                saved_count += 1
            except Exception as e:
                print(f"[DB] 저장 실패: {e}")
                continue

        conn.commit()

    print(f"[DB] {saved_count}개의 합격수기 데이터 저장 완료")
    return saved_count


def save_qa_to_db(
    conn: psycopg.Connection,
    qa_pairs: List[Dict[str, Any]],
    batch_size: int = 100
) -> int:
    """Q&A 데이터를 DB에 저장"""
    create_advice_qa_table(conn)

    saved_count = 0

    with conn.cursor() as cur:
        for qa in qa_pairs:
            exam_info = qa.get("exam_info", {})

            # subjects 배열 처리
            subjects = exam_info.get("subjects", [])
            if isinstance(subjects, str):
                subjects = [subjects] if subjects else []

            try:
                cur.execute("""
                    INSERT INTO advice_qa (
                        question, answer, category,
                        year, exam_type, grade, job_series, subjects
                    ) VALUES (
                        %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                """, (
                    qa.get("question"),
                    qa.get("answer"),
                    qa.get("category"),
                    exam_info.get("year"),
                    exam_info.get("exam_type"),
                    exam_info.get("grade"),
                    exam_info.get("job_series"),
                    subjects if subjects else None
                ))
                saved_count += 1
            except Exception as e:
                print(f"[DB] Q&A 저장 실패: {e}")
                continue

        conn.commit()

    print(f"[DB] {saved_count}개의 Q&A 데이터 저장 완료")
    return saved_count


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="합격수기 데이터를 Neon DB에 저장")
    parser.add_argument("--stories-json", type=str, help="합격수기 JSON 파일 경로")
    parser.add_argument("--qa-csv", type=str, help="Q&A CSV 파일 경로")
    parser.add_argument("--qa-jsonl", type=str, help="Q&A JSONL 파일 경로")
    parser.add_argument("--database-url", type=str, default=None, help="옵션: DATABASE_URL 오버라이드")

    args = parser.parse_args()

    db_url = args.database_url or os.getenv("DATABASE_URL") or settings.DATABASE_URL
    if not db_url:
        print("[오류] DATABASE_URL이 설정되지 않았습니다.")
        return 1

    conn = connect_db(db_url)

    # 합격수기 데이터 저장
    if args.stories_json:
        with open(args.stories_json, 'r', encoding='utf-8') as f:
            stories = json.load(f)
        save_stories_to_db(conn, stories)

    # Q&A 데이터 저장
    if args.qa_csv:
        import csv
        qa_pairs = []
        with open(args.qa_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                qa_pairs.append({
                    "question": row.get("question"),
                    "answer": row.get("answer"),
                    "category": row.get("category"),
                    "exam_info": {
                        "year": row.get("year"),
                        "exam_type": row.get("exam_type"),
                        "grade": row.get("grade"),
                        "job_series": row.get("job_series"),
                        "subjects": row.get("subjects", "").split(", ") if row.get("subjects") else []
                    }
                })
        save_qa_to_db(conn, qa_pairs)

    if args.qa_jsonl:
        qa_pairs = []
        with open(args.qa_jsonl, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    if "messages" in data:
                        # ExaOne 형식에서 추출
                        messages = data.get("messages", [])
                        question = None
                        answer = None
                        for msg in messages:
                            if msg.get("role") == "user":
                                question = msg.get("content")
                            elif msg.get("role") == "assistant":
                                answer = msg.get("content")

                        if question and answer:
                            qa_pairs.append({
                                "question": question,
                                "answer": answer,
                                "category": data.get("category", ""),
                                "exam_info": data.get("exam_info", {})
                            })
        save_qa_to_db(conn, qa_pairs)

    conn.close()
    print("[완료] DB 저장 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

