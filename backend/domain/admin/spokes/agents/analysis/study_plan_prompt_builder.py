"""학습 계획 프롬프트 빌더.

Phase 1의 풀이 로그 분석 결과 + RAG 검색된 합격 수기를
하나의 EXAONE 프롬프트로 조합합니다.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class StudyPlanPromptBuilder:
    """분석 결과 + RAG 컨텍스트 → EXAONE 프롬프트 생성기."""

    # 시스템 역할 설정
    SYSTEM_ROLE = (
        "당신은 공무원 시험 합격을 위한 전문 AI 멘토입니다. "
        "사용자의 실제 풀이 데이터 분석 결과와 합격자들의 학습 수기를 종합하여, "
        "개인화된 학습 계획을 수립해주세요."
    )

    # 출력 형식 안내
    OUTPUT_FORMAT = """아래 JSON 형태로 학습 계획을 출력하세요:
{
  "summary": "전체 분석 요약 (2~3문장)",
  "priority_subjects": ["보완이 시급한 과목 순서"],
  "weekly_schedule": [
    {"day": "월", "subjects": ["과목1", "과목2"], "focus": "집중 포인트", "hours": 3},
    ...
  ],
  "specific_advice": [
    "데이터 기반 구체적 조언 1",
    "데이터 기반 구체적 조언 2",
    ...
  ],
  "motivation": "사용자에게 전하는 동기부여 메시지"
}"""

    @classmethod
    def build_prompt(
        cls,
        analysis_summary: str,
        rag_context: str,
        user_question: str,
        *,
        user_info: Optional[Dict[str, Any]] = None,
    ) -> str:
        """EXAONE에 전달할 최종 프롬프트를 생성합니다.

        Args:
            analysis_summary: SolvingLogAnalyzer.summarize_for_prompt()의 결과
            rag_context: mentoring_rag.build_mentoring_context()의 결과
            user_question: 사용자의 원래 질문
            user_info: 사용자 프로필 정보 (선택)

        Returns:
            완성된 프롬프트 문자열
        """
        parts = [cls.SYSTEM_ROLE, ""]

        # 규칙
        parts.append("===== 규칙 =====")
        parts.append("1. [사용자 분석 데이터]를 최우선으로 활용하여 약점 보완 중심 계획을 세우세요.")
        parts.append("2. [합격자 수기]의 학습 방법론을 참고하되, 사용자의 현재 수준에 맞게 조정하세요.")
        parts.append("3. 과목별 정답률이 낮은 과목에 더 많은 시간을 배정하세요.")
        parts.append("4. 시간 과다 소요 문항이 있다면 해당 유형의 연습을 포함시키세요.")
        parts.append("5. 반복 오답 문항이 있다면 해당 개념의 복습을 반드시 포함시키세요.")
        parts.append("6. 답변은 한국어로 작성하세요.")
        parts.append("7. JSON 형식을 지켜주세요.")
        parts.append("")

        # 사용자 프로필 (있으면)
        if user_info:
            parts.append("===== 사용자 프로필 =====")
            if user_info.get("display_name"):
                parts.append(f"이름: {user_info['display_name']}")
            if user_info.get("daily_study_time"):
                hours = user_info["daily_study_time"] / 60
                parts.append(f"일일 가용 학습 시간: {hours:.1f}시간 ({user_info['daily_study_time']}분)")
            if user_info.get("target_date"):
                parts.append(f"목표 시험일: {user_info['target_date']}")
            if user_info.get("base_score"):
                parts.append(f"초기 점수: {user_info['base_score']}점")
            parts.append("")

        # 분석 데이터
        parts.append("===== 사용자 풀이 분석 데이터 =====")
        parts.append(analysis_summary)
        parts.append("")

        # RAG 컨텍스트
        if rag_context:
            parts.append("===== 합격자 학습 수기 (참고) =====")
            parts.append(rag_context)
            parts.append("")

        # 사용자 질문
        parts.append("===== 사용자 질문 =====")
        parts.append(user_question)
        parts.append("")

        # 출력 형식
        parts.append("===== 출력 형식 =====")
        parts.append(cls.OUTPUT_FORMAT)
        parts.append("")
        parts.append("위 데이터를 종합하여 학습 계획을 생성해주세요:")

        return "\n".join(parts)

    @classmethod
    def build_rag_queries_from_analysis(
        cls,
        analysis: Dict[str, Any],
    ) -> List[str]:
        """분석 결과를 기반으로 RAG 검색 쿼리를 생성합니다.

        Phase 3: 규칙 기반 쿼리 생성 (EXAONE 호출 없이 토큰 절약)

        Args:
            analysis: SolvingLogAnalyzer.analyze()의 결과

        Returns:
            생성된 검색 쿼리 리스트
        """
        queries = []

        if not analysis.get("has_data"):
            # 데이터가 없으면 범용 쿼리
            return ["공무원 시험 초보 학습 계획 추천"]

        # 1) 취약 과목별 쿼리
        weak = analysis.get("weak_subjects", [])
        for subj in weak[:3]:
            subject_name = subj["subject"]
            accuracy = subj["accuracy"]

            if accuracy < 40:
                queries.append(f"{subject_name} 기초부터 다시 시작 학습법 합격 수기")
            elif accuracy < 60:
                queries.append(f"{subject_name} 취약 과목 보완 학습 전략")
            else:
                queries.append(f"{subject_name} 실력 향상 심화 학습법")

        # 2) 전체 정답률 기반 쿼리
        overall_acc = analysis.get("overall_accuracy", 0)
        if overall_acc < 50:
            queries.append("노베이스 초시생 단기 합격 전략 기초부터")
        elif overall_acc < 70:
            queries.append("중간 실력 합격선 돌파 전략 효율적 학습")
        else:
            queries.append("고득점 마무리 실전 모의고사 전략")

        # 3) 반복 오답이 있으면 관련 쿼리
        repeated = analysis.get("repeated_wrong", [])
        if repeated:
            wrong_subjects = list({rw["subject"] for rw in repeated[:3]})
            for subj in wrong_subjects:
                queries.append(f"{subj} 반복 오답 극복 학습법")

        # 4) 시간 관리 문제가 있으면
        slow = analysis.get("slow_questions", [])
        if len(slow) >= 3:
            queries.append("시간 관리 빠른 풀이 전략 실전 팁")

        # 중복 제거
        seen = set()
        unique_queries = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                unique_queries.append(q)

        logger.info(
            f"[PromptBuilder] RAG 쿼리 {len(unique_queries)}개 생성: "
            f"{[q[:30] for q in unique_queries]}"
        )

        return unique_queries

