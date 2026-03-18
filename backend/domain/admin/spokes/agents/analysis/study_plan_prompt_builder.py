"""학습 계획 프롬프트 빌더.

StudyPlanFlow의 요청으로 EXAONE(또는 외부 LLM)에 전달할 프롬프트를 구성합니다.

제공하는 프롬프트 종류:
1. build_prompt()              — 강력한 LLM(GPT-4 등)용 상세 프롬프트.
                                  전체 학습 계획 JSON 한 번에 생성.
2. build_summarization_prompt() — EXAONE 2.4B(CPU)용 경량 프롬프트.
                                  템플릿 원문 → 단계별 bullet 요약.
3. build_rag_queries_from_analysis() — RAG 검색 쿼리 목록 생성.

역할 분리 원칙:
  PromptBuilder — 프롬프트 구성(문자열 조립)만 담당.
  StudyPlanFlow — 데이터 수집·LLM 호출·파싱·저장 담당.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# employment_status(영문 ENUM) → 한국어 매핑
_EMP_LABEL_MAP = {
    "EMPLOYED": "재직",
    "UNEMPLOYED": "무직",
    "STUDENT": "학생",
    "SELF_EMPLOYED": "자영업",
    "OTHER": "기타",
}


class StudyPlanPromptBuilder:
    """학습 계획 생성을 위한 프롬프트 팩토리.

    build_prompt()              : 강력 LLM용 상세 프롬프트 (full JSON 생성)
    build_summarization_prompt(): EXAONE CPU용 경량 프롬프트 (bullet 요약)
    build_rag_queries_from_analysis(): RAG 검색 쿼리 목록 생성
    """

    # 시스템 역할 설정
    SYSTEM_ROLE = (
        "당신은 공무원 시험 합격을 위한 전문 AI 학습 멘토입니다.\n"
        "사용자의 프로필 정보(나이, 직장 상태, 초시 여부, 목표 직렬, 취약/강점 과목), "
        "실제 풀이 데이터 분석 결과, 그리고 환경이 유사한 합격자들의 학습 수기를 종합하여,\n"
        "단순 시간표가 아닌 과목별 학습 전략·일일 루틴·어려움 극복 방안·핵심 합격 전략까지 "
        "포함하는 종합적이고 실질적인 학습 계획을 수립해주세요."
    )

    # 출력 형식 안내 — 확장된 JSON 스키마
    OUTPUT_FORMAT = """아래 JSON 형태로 학습 계획을 출력하세요:
{
  "summary": "전체 분석 요약 (2~3문장). 사용자의 현재 수준과 목표, 매칭된 합격자와의 유사점을 언급",

  "matched_stories_analysis": "매칭된 합격 수기와 사용자 환경의 유사점 분석 (2~3문장). 왜 이 합격자들의 전략이 사용자에게 적합한지 설명",

  "priority_subjects": ["보완이 시급한 과목 순서 (최대 5개)"],

  "subject_plans": [
    {
      "subject": "과목명",
      "current_level": "현재 수준 설명 (분석 데이터 기반)",
      "strategy": "이 과목의 학습 전략 (합격자 수기 참고하여 구체적으로)",
      "recommended_materials": "추천 학습 방법이나 접근법",
      "weekly_hours": 3,
      "priority": "높음/보통/유지"
    }
  ],

  "daily_routine": {
    "description": "합격자 수기를 참고한 추천 일일 루틴 설명",
    "morning": "오전 학습 내용 (예: 6:00-8:00 취약과목 집중)",
    "afternoon": "오후 학습 내용",
    "evening": "저녁 학습 내용",
    "review": "복습/정리 시간"
  },

  "weekly_schedule": [
    {"day": "월", "subjects": ["과목1", "과목2"], "focus": "집중 포인트", "hours": 3}
  ],

  "study_methods": [
    {
      "method": "학습법 이름 (예: 회독 전략)",
      "description": "구체적 설명 (합격 수기에서 인용)",
      "source_story": "참고한 합격 수기 번호 (예: 합격 수기 1)"
    }
  ],

  "difficulty_management": [
    "합격자들이 겪었던 어려움과 극복 방법을 사용자 상황에 맞게 조언 1",
    "조언 2"
  ],

  "key_strategies": [
    "합격자들의 핵심 전략을 사용자 상황에 맞게 정리한 전략 1",
    "전략 2"
  ],

  "specific_advice": [
    "사용자 데이터와 합격 수기를 종합한 구체적 조언 1 (출처: '합격 수기 N에 따르면...')",
    "조언 2"
  ],

  "motivation": "사용자에게 전하는 동기부여 메시지 (유사 환경 합격자의 사례를 언급하며 격려)"
}"""

    # -------------------------------------------------------------------------
    # 1) 강력 LLM용 상세 프롬프트 (GPT-4 / Claude 등)
    #    전체 학습 계획을 JSON 스키마 형태로 한 번에 생성.
    #    EXAONE 2.4B CPU 환경에서는 토큰 수 초과로 타임아웃 발생 → 사용 불가.
    # -------------------------------------------------------------------------
    @classmethod
    def build_prompt(
        cls,
        analysis_summary: str,
        rag_context: str,
        user_question: str,
        *,
        user_info: Optional[Dict[str, Any]] = None,
    ) -> str:
        """강력한 LLM(GPT-4 등)을 위한 상세 학습 계획 생성 프롬프트.

        전체 학습 계획 JSON을 한 번에 생성하도록 요청합니다.
        EXAONE 2.4B CPU 환경에서는 토큰 수(~2500 tokens)가 많아 타임아웃이
        발생하므로, build_summarization_prompt()를 대신 사용하세요.
        """
        parts = [cls.SYSTEM_ROLE, ""]

        # 규칙 (합격 수기 활용 강화)
        parts.append("===== 규칙 =====")
        parts.append(
            "1. [합격자 수기 원문]에서 사용자와 가장 환경이 유사한 합격자의 "
            "학습법을 최우선으로 참고하세요."
        )
        parts.append(
            "2. 과목별 학습 전략(subject_plans)은 합격자 수기의 [과목별 학습법]을 "
            "반드시 참고하여 구체적으로 작성하세요."
        )
        parts.append(
            "3. 일일 루틴(daily_routine)은 합격자 수기의 [일일 학습 계획]을 "
            "사용자 환경(직장인/전업/학생)에 맞게 조정하여 제안하세요."
        )
        parts.append(
            "4. 어려움 극복(difficulty_management)은 합격자들의 "
            "[어려웠던 점과 극복 방법]을 사용자 상황에 맞게 재해석하세요."
        )
        parts.append(
            "5. 핵심 전략(key_strategies)은 합격자들의 [핵심 합격 전략]을 "
            "사용자 수준(초시/재시, 정답률)에 맞게 조정하세요."
        )
        parts.append(
            "6. study_methods에서 합격 수기의 학습법을 인용할 때 "
            "'합격 수기 N' 형태로 출처를 밝혀주세요."
        )
        parts.append(
            "7. 사용자의 취약 과목에는 더 많은 시간을 배정하고, "
            "합격자 수기에서 해당 과목의 학습법이 있으면 반드시 인용하세요."
        )
        parts.append(
            "8. 직장인이면 출퇴근/점심 시간 활용, 초시생이면 기본 개념 중심, "
            "재시생이면 약점 보완 중심으로 차별화하세요."
        )
        parts.append(
            "9. 합격자의 회독수, 수험기간, 하루 공부시간을 참고하여 "
            "현실적인 목표를 설정하세요."
        )
        parts.append(
            "10. 사용자의 목표 수험기간(study_duration)과 합격 수기의 "
            "'총 수험기간'을 비교하여, 유사한 기간에 합격한 수기를 우선 참고하세요. "
            "단기(6개월 이내)면 핵심 위주 빠른 회독, "
            "중기(6개월~1년)면 기본→심화→모의고사 단계적 접근, "
            "장기(1년 이상)면 체계적 반복 학습과 회독수 관리를 중심으로 "
            "기간에 맞는 현실적인 계획을 세우세요."
        )
        parts.append("11. 답변은 한국어로 작성하고, 반드시 JSON 형식을 지켜주세요.")
        parts.append("")

        # 사용자 프로필 (있으면)
        if user_info:
            parts.append("===== 사용자 프로필 =====")
            if user_info.get("display_name"):
                parts.append(f"이름: {user_info['display_name']}")
            if user_info.get("age"):
                parts.append(f"나이: {user_info['age']}세")
            if user_info.get("employment_status"):
                emp_label = _EMP_LABEL_MAP.get(
                    user_info["employment_status"],
                    user_info["employment_status"],
                )
                parts.append(f"직장 상태: {emp_label}")
            if user_info.get("is_first_timer") is not None:
                parts.append(
                    f"초시 여부: "
                    f"{'초시생 (첫 시험)' if user_info['is_first_timer'] else '재시생 (경험 있음)'}"
                )
            if user_info.get("target_position"):
                parts.append(f"목표 직렬: {user_info['target_position']}")
            if user_info.get("daily_study_time"):
                hours = user_info["daily_study_time"] / 60
                parts.append(
                    f"일일 가용 학습 시간: {hours:.1f}시간 ({user_info['daily_study_time']}분)"
                )
            if user_info.get("study_duration"):
                parts.append(f"총 수험 기간(목표 기간): {user_info['study_duration']}")
            if user_info.get("base_score"):
                parts.append(f"초기 점수: {user_info['base_score']}점")
            if user_info.get("weak_subjects"):
                parts.append(
                    f"사용자 자가진단 취약 과목: {', '.join(user_info['weak_subjects'])}"
                )
            if user_info.get("strong_subjects"):
                parts.append(
                    f"사용자 자가진단 강점 과목: {', '.join(user_info['strong_subjects'])}"
                )
            parts.append("")

        # 분석 데이터
        parts.append("===== 사용자 풀이 분석 데이터 =====")
        parts.append(analysis_summary)
        parts.append("")

        # RAG 컨텍스트 (합격 수기 원문 포함) — 핵심 부분
        if rag_context:
            parts.append(
                "===== 합격자 수기 원문 및 멘토링 지식 (핵심 참고 자료) ====="
            )
            parts.append(
                "아래는 사용자와 환경이 유사한 실제 합격자들의 수기입니다. "
                "각 수기의 [과목별 학습법], [일일 학습 계획], [어려웠던 점과 극복 방법], "
                "[핵심 합격 전략]을 반드시 학습 계획에 반영하세요. "
                "특히 사용자의 취약 과목에 해당하는 학습법은 subject_plans에 인용하세요."
            )
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
        parts.append(
            "위 데이터를 종합하여, 합격자 수기의 실전 학습법을 최대한 반영한 "
            "종합적인 학습 계획을 생성해주세요:"
        )

        return "\n".join(parts)

    # -------------------------------------------------------------------------
    # 2) EXAONE 2.4B CPU용 경량 요약 프롬프트
    #    템플릿이 생성한 합격 수기 원문(daily_routine, difficulty, key_strategies)을
    #    단계별 번호 목록으로 요약하도록 요청합니다.
    #    입력 ~160 tokens + 출력 ~120 tokens = 총 ~280 tokens → 약 60~70초 소요.
    # -------------------------------------------------------------------------
    @classmethod
    def build_summarization_prompt(
        cls,
        base_plan: Dict[str, Any],
        analysis: Optional[Dict[str, Any]] = None,
        user_info: Optional[Dict[str, Any]] = None,
    ) -> str:
        """EXAONE 2.4B CPU용 경량 요약 프롬프트.

        템플릿 계획(base_plan)에 포함된 합격 수기 원문 텍스트를 받아
        각 항목을 단계별 번호 목록으로 요약하도록 요청합니다.

        Args:
            base_plan: _generate_template_plan()이 반환한 계획 dict.
                       daily_routine.description, difficulty_management,
                       key_strategies 필드의 원문을 사용합니다.
            analysis:  풀이 분석 데이터 (정답률 등 학생 정보에 활용).
            user_info: 사용자 프로필 (목표 직렬, 초시 여부 등).

        Returns:
            EXAONE에 전달할 프롬프트 문자열 (~500 chars).
        """
        import re as _re

        def _clip(text: str, n: int = 90) -> str:
            """원문 접두사 제거 후 n자로 잘라 반환."""
            t = _re.sub(r"\(합격 수기 \d+\)\s*", "", text or "").strip()
            return t[:n].rstrip() if len(t) > n else t

        parts = ["합격 수기 원문을 각 항목별로 번호 목록으로 짧게 요약하세요.", ""]

        # 일일 루틴 원문
        dr = base_plan.get("daily_routine")
        routine_raw = _clip(dr.get("description", "") if isinstance(dr, dict) else "")

        # 어려움 극복 원문 (첫 번째 항목)
        diff_list = base_plan.get("difficulty_management") or []
        diff_raw = _clip(diff_list[0]) if diff_list else ""

        # 핵심 전략 원문 (첫 번째 항목)
        strat_list = base_plan.get("key_strategies") or []
        strat_raw = _clip(strat_list[0]) if strat_list else ""

        if routine_raw:
            parts.append(f"[루틴원문] {routine_raw}")
        if diff_raw:
            parts.append(f"[어려움원문] {diff_raw}")
        if strat_raw:
            parts.append(f"[전략원문] {strat_raw}")

        # 원문이 하나도 없으면 학생 정보 기반 최소 프롬프트
        if not any([routine_raw, diff_raw, strat_raw]):
            info_parts: List[str] = []
            if user_info:
                pos = user_info.get("target_position", "")
                if pos:
                    is_first = user_info.get("is_first_timer")
                    suffix = "(초시)" if is_first else "(재시)" if is_first is False else ""
                    info_parts.append(f"목표:{pos}{suffix}")
                weak = user_info.get("weak_subjects") or []
                if weak:
                    info_parts.append(f"취약:{', '.join(weak[:2])}")
            if analysis and analysis.get("has_data"):
                info_parts.append(
                    f"정답률:{analysis.get('overall_accuracy', 0):.0f}%"
                )
            parts.append(
                "[학생] " + " / ".join(info_parts) if info_parts else "공무원 수험생"
            )

        parts.append("")
        parts.append("아래 형식으로 출력 (원문 없는 항목은 생략):")
        if routine_raw:
            parts.append("[루틴] 1. 항목 2. 항목 3. 항목")
        if diff_raw:
            parts.append("[어려움] 1. 항목 2. 항목")
        if strat_raw:
            parts.append("[전략] 1. 항목 2. 항목 3. 항목")

        return "\n".join(parts)

    # -------------------------------------------------------------------------
    # 3) RAG 검색 쿼리 생성
    # -------------------------------------------------------------------------
    @classmethod
    def build_rag_queries_from_analysis(
        cls,
        analysis: Dict[str, Any],
        *,
        user_info: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """분석 결과 + 사용자 프로필을 기반으로 RAG 검색 쿼리를 생성합니다.

        핵심: 사용자의 환경(직렬, 직장상태, 초시여부)과 취약 과목을
        조합하여 가장 관련성 높은 합격 수기를 검색합니다.
        """
        queries = []

        # 사용자 프로필 기반 쿼리 (분석 데이터 유무와 관계없이 생성)
        if user_info:
            target_pos = user_info.get("target_position")
            is_first = user_info.get("is_first_timer")
            emp_status = user_info.get("employment_status")
            user_weak = user_info.get("weak_subjects", []) or []
            study_duration = user_info.get("study_duration", "")

            # 복합 조건 쿼리 (가장 중요) — 수험기간 포함
            composite_parts = []
            if target_pos:
                composite_parts.append(target_pos)
            if emp_status:
                emp_label = _EMP_LABEL_MAP.get(emp_status, "")
                if emp_label:
                    composite_parts.append(
                        "직장인 병행" if emp_label == "재직" else emp_label
                    )
            if is_first is not None:
                composite_parts.append("초시" if is_first else "재시")
            if study_duration:
                composite_parts.append(f"수험기간 {study_duration}")
            if composite_parts:
                queries.append(
                    " ".join(composite_parts) + " 합격 수기 학습 전략"
                )

            # 목표 직렬 + 초시/재시 기반 쿼리
            if target_pos and is_first is not None:
                if is_first:
                    queries.append(
                        f"{target_pos} 초시생 합격 전략 학습법 일일 계획"
                    )
                else:
                    queries.append(
                        f"{target_pos} 재시생 실전 전략 약점 보완 합격"
                    )
            elif target_pos:
                queries.append(f"{target_pos} 합격 학습 전략 과목별 방법")

            # 직장인 + 학습 전략
            if emp_status and emp_status in ("EMPLOYED",):
                queries.append(
                    "직장인 공무원 시험 병행 학습법 시간 관리 일일 루틴"
                )

            # 사용자 자가진단 취약 과목 쿼리
            if user_weak:
                weak_combined = " ".join(user_weak[:3])
                queries.append(
                    f"{weak_combined} 취약 과목 학습법 극복 방법 합격 수기"
                )

            # 사용자 자가진단 강점 과목 — 심화 학습법 쿼리
            user_strong = user_info.get("strong_subjects", []) or []
            if user_strong:
                strong_combined = " ".join(user_strong[:2])
                queries.append(
                    f"{strong_combined} 고득점 전략 과목별 학습법 합격 수기"
                )

        if not analysis.get("has_data"):
            if not queries:
                return ["공무원 시험 학습 계획 과목별 학습법 합격 수기"]
            return queries

        # 분석 결과 기반: 취약 과목별 쿼리
        weak = analysis.get("weak_subjects", [])
        if weak:
            weak_subjects_str = " ".join([w["subject"] for w in weak[:3]])
            queries.append(
                f"{weak_subjects_str} 취약 보완 과목별 학습 전략 합격"
            )

        # 전체 정답률 기반 쿼리
        overall_acc = analysis.get("overall_accuracy", 0)
        if overall_acc < 50:
            queries.append("노베이스 기초부터 학습 전략 단기 합격 일일 계획")
        elif overall_acc < 70:
            queries.append("중간 실력 합격선 돌파 전략 효율적 회독 학습법")
        else:
            queries.append("고득점 마무리 실전 모의고사 전략 합격 수기")

        # 반복 오답이 있으면 관련 쿼리
        repeated = analysis.get("repeated_wrong", [])
        if repeated:
            wrong_subjects = list({rw["subject"] for rw in repeated[:3]})
            for subj in wrong_subjects[:2]:
                queries.append(f"{subj} 반복 오답 극복 학습법 수기")

        # 중복 제거
        seen = set()
        unique_queries = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                unique_queries.append(q)

        logger.info(
            f"[PromptBuilder] RAG 쿼리 {len(unique_queries)}개 생성: "
            f"{[q[:40] for q in unique_queries]}"
        )

        return unique_queries
