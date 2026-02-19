"""
5단계: 크롭된 문항을 NeonDB에 저장

crop_results.json의 데이터를 DB 테이블에 저장합니다:
- Questions: 문항 메타데이터
- Question_Images: 이미지 파일 경로 및 좌표

사용법:
    python step5_save_to_db.py
    python step5_save_to_db.py --json ./data/crops/crop_results.json
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import argparse

import psycopg
from psycopg.rows import dict_row

from config import DATABASE_URL, CROP_OUTPUT_DIR


def get_db_connection():
    """DB 연결 획득."""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def ensure_tables_exist(conn):
    """필요한 테이블 존재 확인 및 생성.

    Args:
        conn: DB 연결
    """
    with conn.cursor() as cur:
        # Exams 테이블
        cur.execute("""
            CREATE TABLE IF NOT EXISTS exams (
                id SERIAL PRIMARY KEY,
                year SMALLINT NOT NULL,
                exam_type VARCHAR(50),
                series VARCHAR(50),
                grade VARCHAR(20),
                subject VARCHAR(100) NOT NULL,
                exam_vector VECTOR(1536),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(year, exam_type, subject)
            );
        """)

        # Questions 테이블
        cur.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id SERIAL PRIMARY KEY,
                exam_id INTEGER REFERENCES exams(id) ON DELETE CASCADE,
                question_no SMALLINT NOT NULL,
                question_text TEXT,
                sub_category VARCHAR(100),
                answer_key VARCHAR(10),
                ind BOOLEAN DEFAULT FALSE,
                source_pdf VARCHAR(500),
                extra_json JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)

        # Question_Images 테이블
        cur.execute("""
            CREATE TABLE IF NOT EXISTS question_images (
                id SERIAL PRIMARY KEY,
                question_id INTEGER REFERENCES questions(id) ON DELETE CASCADE,
                file_path VARCHAR(500) NOT NULL,
                coordinates_json JSONB,
                image_type VARCHAR(20),
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)

        conn.commit()
        print("✅ 테이블 확인/생성 완료")


def get_or_create_exam(
    conn,
    year: int,
    subject: str,
    exam_type: str = None,
    series: str = None,
    grade: str = None
) -> int:
    """시험 레코드 조회 또는 생성.

    Args:
        conn: DB 연결
        year: 연도
        subject: 과목
        exam_type: 시험 유형
        series: 시리즈
        grade: 등급

    Returns:
        exam_id
    """
    with conn.cursor() as cur:
        # 기존 레코드 조회
        cur.execute(
            """
            SELECT id FROM exams
            WHERE year = %s AND subject = %s AND exam_type IS NOT DISTINCT FROM %s
            """,
            (year, subject, exam_type)
        )
        row = cur.fetchone()

        if row:
            return row["id"]

        # 새 레코드 생성
        cur.execute(
            """
            INSERT INTO exams (year, exam_type, series, grade, subject)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (year, exam_type, series, grade, subject)
        )
        row = cur.fetchone()
        conn.commit()

        return row["id"]


def insert_question(
    conn,
    exam_id: int,
    question_no: int,
    question_text: str = None,
    answer_key: str = None,
    sub_category: str = None,
    source_pdf: str = None,
    extra_json: dict = None
) -> int:
    """문항 레코드 생성.

    Args:
        conn: DB 연결
        exam_id: 시험 ID
        question_no: 문항 번호
        ...

    Returns:
        question_id
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO questions (
                exam_id, question_no, question_text, answer_key,
                sub_category, source_pdf, extra_json
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
            RETURNING id
            """,
            (
                exam_id, question_no, question_text, answer_key,
                sub_category, source_pdf,
                json.dumps(extra_json) if extra_json else None
            )
        )
        row = cur.fetchone()
        conn.commit()

        return row["id"]


def insert_question_image(
    conn,
    question_id: int,
    file_path: str,
    coordinates: dict = None,
    image_type: str = None
) -> int:
    """문항 이미지 레코드 생성.

    Args:
        conn: DB 연결
        question_id: 문항 ID
        file_path: 파일 경로
        coordinates: 좌표 정보 (bbox)
        image_type: 이미지 타입

    Returns:
        image_id
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO question_images (
                question_id, file_path, coordinates_json, image_type
            )
            VALUES (%s, %s, %s::jsonb, %s)
            RETURNING id
            """,
            (
                question_id, file_path,
                json.dumps(coordinates) if coordinates else None,
                image_type
            )
        )
        row = cur.fetchone()
        conn.commit()

        return row["id"]


def process_crop_results(conn, results: List[Dict[str, Any]]):
    """크롭 결과를 DB에 저장.

    Args:
        conn: DB 연결
        results: crop_results.json 내용
    """
    print(f"\n📊 총 {len(results)}개 레코드 처리 중...")

    # 시험별로 그룹화
    exams_map = {}  # (year, subject) -> exam_id
    questions_map = {}  # (exam_id, question_no) -> question_id

    saved_count = 0

    for item in results:
        year = item.get("year", datetime.now().year)
        subject = item.get("subject", "미분류")
        exam_type = item.get("exam_type")

        # 시험 레코드
        exam_key = (year, subject, exam_type)
        if exam_key not in exams_map:
            exam_id = get_or_create_exam(conn, year, subject, exam_type)
            exams_map[exam_key] = exam_id
        else:
            exam_id = exams_map[exam_key]

        question_no = item.get("question_no", 1)

        # 문항 레코드
        question_key = (exam_id, question_no)
        if question_key not in questions_map:
            question_id = insert_question(
                conn,
                exam_id=exam_id,
                question_no=question_no,
                source_pdf=item.get("source_image"),
                extra_json={
                    "confidence": item.get("confidence"),
                    "class_name": item.get("class_name"),
                }
            )
            questions_map[question_key] = question_id
        else:
            question_id = questions_map[question_key]

        # 이미지 레코드
        bbox = item.get("bbox", [])
        coordinates = {
            "x1": bbox[0] if len(bbox) > 0 else 0,
            "y1": bbox[1] if len(bbox) > 1 else 0,
            "x2": bbox[2] if len(bbox) > 2 else 0,
            "y2": bbox[3] if len(bbox) > 3 else 0,
        }

        crop_path = item.get("crop_path", "")
        image_type = Path(crop_path).suffix.lstrip(".") if crop_path else None

        insert_question_image(
            conn,
            question_id=question_id,
            file_path=crop_path,
            coordinates=coordinates,
            image_type=image_type
        )

        saved_count += 1

    print(f"✅ {saved_count}개 이미지 레코드 저장 완료")
    print(f"   시험: {len(exams_map)}개")
    print(f"   문항: {len(questions_map)}개")


def main():
    parser = argparse.ArgumentParser(description="크롭 결과를 DB에 저장")
    parser.add_argument(
        "--json", type=str,
        default=str(CROP_OUTPUT_DIR / "crop_results.json"),
        help="크롭 결과 JSON 파일"
    )
    parser.add_argument("--dry-run", action="store_true", help="저장 없이 미리보기")

    args = parser.parse_args()

    print("=" * 50)
    print(" 💾 크롭 결과 DB 저장")
    print("=" * 50)

    json_path = Path(args.json)
    if not json_path.exists():
        print(f"\n❌ JSON 파일을 찾을 수 없습니다: {json_path}")
        print("   먼저 step4_crop_questions.py를 실행하세요.")
        return

    # JSON 로드
    with open(json_path, "r", encoding="utf-8") as f:
        results = json.load(f)

    print(f"\n📄 로드: {json_path}")
    print(f"   레코드 수: {len(results)}개")

    if args.dry_run:
        print("\n🔍 미리보기 (dry-run):")
        for i, item in enumerate(results[:5]):
            print(f"   [{i+1}] Q{item.get('question_no')}: {item.get('crop_path')}")
        if len(results) > 5:
            print(f"   ... 외 {len(results) - 5}개")
        return

    # DB 연결
    try:
        conn = get_db_connection()
        print("✅ DB 연결 성공")
    except Exception as e:
        print(f"\n❌ DB 연결 실패: {e}")
        print("   config_example.env를 .env로 복사하고 DATABASE_URL을 설정하세요.")
        return

    try:
        # 테이블 확인
        ensure_tables_exist(conn)

        # 데이터 저장
        process_crop_results(conn, results)

    finally:
        conn.close()

    print("\n" + "=" * 50)
    print(" ✅ DB 저장 완료!")
    print("=" * 50)
    print("\n다음 단계: 랜덤 문제 API 서버 실행")
    print("  python step6_api_server.py")


if __name__ == "__main__":
    main()


