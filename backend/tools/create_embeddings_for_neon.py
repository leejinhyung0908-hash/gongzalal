"""
합격 수기 데이터를 Neon DB에 저장하기 위한 Embedding 생성 및 저장 스크립트

사용 방법:
1. conda activate torch313 (또는 다른 conda 환경)
2. .env 파일에 DATABASE_URL 설정
3. python create_embeddings_for_neon.py 실행

필수 패키지:
- sentence-transformers (pip install sentence-transformers)
- psycopg, pgvector, python-dotenv (이미 설치되어 있을 수 있음)
"""

import json
import os
import sys
from typing import Dict, Any, List
from pathlib import Path

# 환경 변수 로드
from dotenv import load_dotenv
load_dotenv()

# 데이터베이스 연결
import psycopg
from pgvector.psycopg import register_vector

# KURE-v1 Embedding 모델 사용
KURE_AVAILABLE = False
kure_model = None

try:
    from sentence_transformers import SentenceTransformer
    import torch
    KURE_AVAILABLE = True
except ImportError:
    KURE_AVAILABLE = False
    print("[경고] sentence-transformers 라이브러리가 설치되지 않았습니다. pip install sentence-transformers 실행 필요")

# 모델은 main 함수에서 로드 (전역 변수로 사용)
def load_kure_model():
    """KURE-v1 모델 로드"""
    global kure_model
    if kure_model is None:
        print("[로딩] KURE-v1 모델 로딩 중... (첫 실행 시 Hugging Face에서 다운로드)")
        kure_model = SentenceTransformer('nlpai-lab/KURE-v1')
        print("[OK] KURE-v1 모델 로딩 완료")
    return kure_model


def create_text_from_story(story: Dict[str, Any], source: str = "gongdanki") -> str:
    """
    합격 수기 JSON을 검색 가능한 텍스트로 변환

    Args:
        story: 합격 수기 JSON 객체
        source: 데이터 소스 (gongdanki 또는 megagong)

    Returns:
        검색 가능한 텍스트 문자열
    """
    parts = []

    # 시험 정보
    exam_info = story.get("exam_info", {})
    if exam_info:
        exam_parts = []
        if exam_info.get("year"):
            exam_parts.append(f"시험 연도: {exam_info['year']}")
        if exam_info.get("exam_type"):
            exam_parts.append(f"시험 유형: {exam_info['exam_type']}")
        if exam_info.get("grade"):
            exam_parts.append(f"등급: {exam_info['grade']}급")
        if exam_info.get("job_series"):
            exam_parts.append(f"직렬: {exam_info['job_series']}")
        if exam_info.get("subjects"):
            exam_parts.append(f"응시 과목: {', '.join(exam_info['subjects'])}")
        if exam_info.get("총 수험기간"):
            exam_parts.append(f"수험 기간: {exam_info['총 수험기간']}")
        if exam_parts:
            parts.append(" ".join(exam_parts))

    # 수험생활 스타일
    study_style = story.get("study_style", {})
    if study_style:
        style_parts = []
        if study_style.get("수험생활"):
            style_parts.append(f"수험생활: {study_style['수험생활']}")
        if study_style.get("평균 회독수"):
            style_parts.append(f"평균 회독수: {study_style['평균 회독수']}")
        if style_parts:
            parts.append(" ".join(style_parts))

    # 일일 학습 계획
    if story.get("daily_plan"):
        parts.append(f"일일 학습 계획: {story['daily_plan']}")

    # 과목별 학습법
    subject_methods = story.get("subject_methods", {})
    if subject_methods:
        if isinstance(subject_methods, dict):
            # megagong 형식 (이미 과목별로 분리됨)
            for subject, method in subject_methods.items():
                if method and len(method.strip()) > 10:
                    # 중복된 과목명 제거 (예: "국어국어는" -> "국어는")
                    method_clean = method.strip()
                    if method_clean.startswith(subject):
                        if len(method_clean) > len(subject) and method_clean[len(subject):len(subject)+len(subject)] == subject:
                            method_clean = method_clean[len(subject):]
                    parts.append(f"{subject} 학습법: {method_clean[:500]}")  # 길이 제한
        elif isinstance(subject_methods, str):
            # gongdanki 형식 (전체 또는 과목별 텍스트)
            parts.append(f"과목별 학습법: {subject_methods[:1000]}")

    # 면접 준비
    if story.get("interview_prep"):
        parts.append(f"면접 준비: {story['interview_prep']}")

    # 어려웠던 점
    if story.get("difficulties"):
        parts.append(f"어려웠던 점: {story['difficulties']}")

    # 핵심 포인트
    if story.get("key_points"):
        parts.append(f"핵심 포인트: {story['key_points']}")

    return "\n".join(parts)


def create_embedding(text: str, model: SentenceTransformer = None) -> List[float]:
    """
    텍스트를 KURE-v1 embedding 벡터로 변환

    Args:
        text: 변환할 텍스트
        model: KURE-v1 모델 (None이면 전역 모델 사용)

    Returns:
        embedding 벡터 (리스트)
    """
    if not KURE_AVAILABLE:
        raise ImportError("KURE-v1 모델이 로드되지 않았습니다. sentence-transformers 설치 필요")

    if model is None:
        model = load_kure_model()

    # 텍스트가 너무 길면 잘라내기 (KURE-v1은 최대 512 토큰)
    max_chars = 2000  # 안전하게 2000자로 제한
    if len(text) > max_chars:
        text = text[:max_chars]

    # KURE-v1 모델로 embedding 생성
    embedding = model.encode(text, normalize_embeddings=True, show_progress_bar=False)

    return embedding.tolist()


def setup_database_schema(conn: psycopg.Connection):
    """데이터베이스 스키마 설정 (테이블 생성)"""
    register_vector(conn)

    with conn.cursor() as cur:
        # pgvector 확장 활성화
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        # 합격 수기 테이블 생성
        # KURE-v1은 1024차원 embedding을 생성합니다
        cur.execute("""
            CREATE TABLE IF NOT EXISTS success_stories (
                id SERIAL PRIMARY KEY,
                source VARCHAR(50) NOT NULL,  -- 'gongdanki' or 'megagong'
                story_id INTEGER,  -- 원본 JSON의 인덱스
                exam_info JSONB,  -- 시험 정보
                study_style JSONB,  -- 수험생활 스타일
                daily_plan TEXT,
                subject_methods JSONB,
                interview_prep TEXT,
                difficulties TEXT,
                key_points TEXT,
                raw_text TEXT,  -- 원본 텍스트
                search_text TEXT,  -- 검색용 텍스트
                embedding vector(1024),  -- KURE-v1은 1024차원
                source_url TEXT,
                crawled_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 검색 성능을 위한 인덱스 생성
        cur.execute("""
            CREATE INDEX IF NOT EXISTS success_stories_embedding_idx
            ON success_stories
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
        """)

        # 소스별 인덱스
        cur.execute("""
            CREATE INDEX IF NOT EXISTS success_stories_source_idx
            ON success_stories(source);
        """)

        conn.commit()
        print("[OK] 데이터베이스 스키마 설정 완료")


def insert_story_to_db(
    conn: psycopg.Connection,
    story: Dict[str, Any],
    story_index: int,
    source: str,
    embedding: List[float]
):
    """합격 수기를 데이터베이스에 삽입"""
    register_vector(conn)

    search_text = create_text_from_story(story, source)

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO success_stories (
                source, story_id, exam_info, study_style, daily_plan,
                subject_methods, interview_prep, difficulties, key_points,
                raw_text, search_text, embedding, source_url, crawled_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            source,
            story_index,
            json.dumps(story.get("exam_info", {}), ensure_ascii=False),
            json.dumps(story.get("study_style", {}), ensure_ascii=False),
            story.get("daily_plan"),
            json.dumps(story.get("subject_methods", {}), ensure_ascii=False),
            story.get("interview_prep"),
            story.get("difficulties"),
            story.get("key_points"),
            story.get("raw_text"),
            search_text,
            embedding,
            story.get("source_url"),
            story.get("crawled_at")
        ))
        conn.commit()


def process_stories_file(file_path: str, source: str, conn: psycopg.Connection, model):
    """합격 수기 JSON 파일을 처리하여 DB에 저장"""
    print(f"\n[{source}] 파일 처리 시작: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        stories = json.load(f)

    print(f"[{source}] 총 {len(stories)}개의 합격 수기 발견")

    success_count = 0
    error_count = 0

    for idx, story in enumerate(stories):
        try:
            # 검색용 텍스트 생성
            search_text = create_text_from_story(story, source)

            if not search_text or len(search_text.strip()) < 50:
                print(f"[{source}] 스킵: 인덱스 {idx} - 텍스트가 너무 짧음")
                continue

            # Embedding 생성
            print(f"[{source}] 처리 중 ({idx+1}/{len(stories)}): Embedding 생성 중...", end="\r")
            embedding = create_embedding(search_text, model=model)

            # DB에 저장
            insert_story_to_db(conn, story, idx, source, embedding)
            success_count += 1

            if (idx + 1) % 10 == 0:
                print(f"[{source}] 진행 상황: {idx+1}/{len(stories)} 완료 (성공: {success_count}, 실패: {error_count})")

        except Exception as e:
            error_count += 1
            print(f"\n[{source}] 오류 발생 (인덱스 {idx}): {e}")
            continue

    print(f"\n[{source}] 완료! 성공: {success_count}, 실패: {error_count}")


def main():
    """메인 함수"""
    # 환경 변수 확인
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("[오류] DATABASE_URL 환경 변수가 설정되지 않았습니다.")
        print("       .env 파일에 DATABASE_URL을 설정하거나 환경 변수로 설정하세요.")
        print("       형식: postgresql+psycopg://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=require")
        sys.exit(1)

    # KURE-v1 모델 확인 및 로드
    if not KURE_AVAILABLE:
        print("[오류] KURE-v1 모델을 로드할 수 없습니다.")
        print("       다음 명령어로 필요한 패키지를 설치하세요:")
        print("       pip install sentence-transformers torch")
        sys.exit(1)

    # 모델 미리 로드 (첫 실행 시 다운로드 시간 고려)
    print("[모델] KURE-v1 모델 로딩 중...")
    load_kure_model()

    # 데이터베이스 연결
    print("[DB] 데이터베이스 연결 중...")
    try:
        # psycopg 형식으로 변환
        dsn = database_url.replace("postgresql+psycopg://", "postgresql://")
        conn = psycopg.connect(dsn, autocommit=False)
        print("[OK] 데이터베이스 연결 성공")
    except Exception as e:
        print(f"[오류] 데이터베이스 연결 실패: {e}")
        sys.exit(1)

    try:
        # 스키마 설정
        setup_database_schema(conn)

        # 파일 경로
        base_dir = Path(__file__).parent
        gongdanki_file = base_dir / "data" / "success_stories" / "gongdanki" / "success_stories.json"
        megagong_file = base_dir / "data" / "success_stories" / "megagong" / "megagong_stories.json"

        # 모델 로드
        model = load_kure_model()

        # gongdanki 처리
        if gongdanki_file.exists():
            process_stories_file(str(gongdanki_file), "gongdanki", conn, model)
        else:
            print(f"[경고] 파일을 찾을 수 없습니다: {gongdanki_file}")

        # megagong 처리
        if megagong_file.exists():
            process_stories_file(str(megagong_file), "megagong", conn, model)
        else:
            print(f"[경고] 파일을 찾을 수 없습니다: {megagong_file}")

        print("\n[완료] 모든 데이터 처리 완료!")

    except KeyboardInterrupt:
        print("\n[중단] 사용자에 의해 중단되었습니다.")
        conn.rollback()
    except Exception as e:
        print(f"\n[오류] 처리 중 오류 발생: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()
        print("[DB] 데이터베이스 연결 종료")


if __name__ == "__main__":
    main()

