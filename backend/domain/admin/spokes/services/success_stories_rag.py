"""
합격 수기 RAG 서비스 (Neon DB 벡터 검색)

Neon DB에 저장된 합격 수기 데이터를 벡터 검색으로 찾아서 반환합니다.
"""

import os
from typing import List, Dict, Any, Optional, Tuple
import psycopg
from pgvector.psycopg import register_vector

from backend.dependencies import get_db_connection
from backend.core.utils.embedding import generate_embedding


class SuccessStoriesRAG:
    """합격 수기 RAG 서비스"""

    def __init__(self):
        pass

    def search_similar_stories(
        self,
        query: str,
        top_k: int = 3,
        min_similarity: float = 0.5,
        source: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """질문과 유사한 합격 수기 검색

        Args:
            query: 검색 질문
            top_k: 반환할 결과 수
            min_similarity: 최소 유사도 (0.0 ~ 1.0)
            source: 소스 필터 ('gongdanki' 또는 'megagong', None이면 전체)

        Returns:
            검색된 합격 수기 리스트 (유사도 내림차순)
        """
        try:
            # 전역 싱글톤 KURE-v1으로 질문 embedding 생성
            query_embedding = generate_embedding(query)

            # DB 연결
            conn = get_db_connection()
            register_vector(conn)

            with conn.cursor() as cur:
                # 벡터 검색 쿼리
                if source:
                    cur.execute("""
                        SELECT
                            id,
                            source,
                            story_id,
                            exam_info,
                            study_style,
                            daily_plan,
                            subject_methods,
                            interview_prep,
                            difficulties,
                            key_points,
                            search_text,
                            source_url,
                            1 - (embedding <=> %s::vector) as similarity
                        FROM success_stories
                        WHERE source = %s
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                    """, (query_embedding, source, query_embedding, top_k))
                else:
                    cur.execute("""
                        SELECT
                            id,
                            source,
                            story_id,
                            exam_info,
                            study_style,
                            daily_plan,
                            subject_methods,
                            interview_prep,
                            difficulties,
                            key_points,
                            search_text,
                            source_url,
                            1 - (embedding <=> %s::vector) as similarity
                        FROM success_stories
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                    """, (query_embedding, query_embedding, top_k))

                rows = cur.fetchall()

                results = []
                for row in rows:
                    similarity = float(row[12])
                    if similarity < min_similarity:
                        continue

                    results.append({
                        "id": row[0],
                        "source": row[1],
                        "story_id": row[2],
                        "exam_info": row[3],
                        "study_style": row[4],
                        "daily_plan": row[5],
                        "subject_methods": row[6],
                        "interview_prep": row[7],
                        "difficulties": row[8],
                        "key_points": row[9],
                        "search_text": row[10],
                        "source_url": row[11],
                        "similarity": similarity
                    })

                return results

        except Exception as e:
            print(f"[SuccessStoriesRAG] 검색 오류: {e}", flush=True)
            return []

    def format_context_for_llm(self, stories: List[Dict[str, Any]]) -> str:
        """검색된 합격 수기를 LLM용 컨텍스트로 포맷팅

        Args:
            stories: 검색된 합격 수기 리스트

        Returns:
            LLM에 전달할 컨텍스트 문자열
        """
        if not stories:
            return "관련 합격 수기를 찾지 못했습니다."

        context_parts = []
        for i, story in enumerate(stories, 1):
            exam_info = story.get("exam_info", {})
            exam_type = exam_info.get("exam_type", "알 수 없음")
            grade = exam_info.get("grade", "알 수 없음")
            job_series = exam_info.get("job_series", "알 수 없음")
            year = exam_info.get("year", "알 수 없음")

            context_parts.append(f"\n[합격 수기 {i}]")
            context_parts.append(f"- 출처: {story.get('source', '알 수 없음')}")
            context_parts.append(f"- 시험 정보: {year}년 {exam_type} {grade} {job_series}")

            if story.get("daily_plan"):
                context_parts.append(f"- 일일 계획: {story['daily_plan'][:200]}...")

            if story.get("key_points"):
                context_parts.append(f"- 핵심 포인트: {story['key_points'][:200]}...")

            if story.get("subject_methods"):
                # 과목별 학습법 요약
                subject_methods = story["subject_methods"]
                if isinstance(subject_methods, dict):
                    subjects = list(subject_methods.keys())[:3]  # 최대 3개 과목만
                    context_parts.append(f"- 주요 과목 학습법: {', '.join(subjects)}")

            context_parts.append(f"- 유사도: {story.get('similarity', 0):.2f}")

        return "\n".join(context_parts)

