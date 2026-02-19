"""StudyPlan 요청 처리 Orchestrator (LangGraph 기반).

하이브리드 학습 계획 생성 파이프라인:
1. SolvingLogAnalyzer: 풀이 로그 분석 (SQL + Python)
2. MentoringRAG: 분석 기반 검색 쿼리로 합격 수기 검색
3. EXAONE: 분석 결과 + RAG 컨텍스트 → 개인화 학습 계획 생성
4. StudyPlanService: 생성된 계획을 study_plans 테이블에 저장

테이블 구조:
- Study_Plans: user_id FK, plan_json, version
"""

import json
import logging
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.domain.admin.models.transfers.user_transfer import (
    StudyPlanCreateRequest,
    StudyPlanUpdateRequest,
)
from backend.domain.admin.spokes.agents.analysis.solving_log_analyzer import (
    SolvingLogAnalyzer,
)
from backend.domain.admin.spokes.agents.analysis.study_plan_prompt_builder import (
    StudyPlanPromptBuilder,
)
from backend.domain.admin.spokes.agents.retrieval.mentoring_rag import (
    build_mentoring_context,
    search_mentoring_knowledge,
)
from backend.domain.admin.spokes.services.study_plan_service import StudyPlanService

logger = logging.getLogger(__name__)


# ============================================================================
# State 정의
# ============================================================================

class StudyPlanProcessingState(TypedDict, total=False):
    """StudyPlan 처리 상태."""

    request_text: str
    request_data: Dict[str, Any]
    action: str  # create, read, generate, update
    user_id: Optional[int]
    plan_id: Optional[int]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    metadata: Optional[Dict[str, Any]]
    # AI 생성용
    generated_plan: Optional[Dict[str, Any]]
    analysis: Optional[Dict[str, Any]]
    rag_context: Optional[str]


# ============================================================================
# StudyPlanFlow
# ============================================================================

class StudyPlanFlow:
    """StudyPlan 요청 처리 Orchestrator (LangGraph 기반)."""

    def __init__(self):
        """초기화."""
        self._service = StudyPlanService()
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """LangGraph StateGraph 빌드."""
        graph = StateGraph(StudyPlanProcessingState)

        # 노드 추가
        graph.add_node("validate", self._validate_node)
        graph.add_node("determine_action", self._determine_action_node)
        graph.add_node("process_create", self._process_create_node)
        graph.add_node("process_read", self._process_read_node)
        graph.add_node("process_generate", self._process_generate_node)
        graph.add_node("finalize", self._finalize_node)

        # 엣지 추가
        graph.add_edge(START, "validate")
        graph.add_edge("validate", "determine_action")
        graph.add_conditional_edges(
            "determine_action",
            self._route_action,
            {
                "create": "process_create",
                "read": "process_read",
                "generate": "process_generate",
            },
        )
        graph.add_edge("process_create", "finalize")
        graph.add_edge("process_read", "finalize")
        graph.add_edge("process_generate", "finalize")
        graph.add_edge("finalize", END)

        return graph.compile()

    async def _validate_node(
        self, state: StudyPlanProcessingState
    ) -> StudyPlanProcessingState:
        """데이터 검증 노드."""
        request_data = state.get("request_data", {})

        if not request_data:
            return {**state, "error": "요청 데이터가 비어있습니다."}

        user_id = request_data.get("user_id")
        if not user_id:
            return {**state, "error": "user_id가 필요합니다."}

        return state

    async def _determine_action_node(
        self, state: StudyPlanProcessingState
    ) -> StudyPlanProcessingState:
        """액션 판단 노드."""
        request_data = state.get("request_data", {})
        action = request_data.get("action", "read")

        logger.info(f"[StudyPlanFlow] 액션 판단: {action}")

        return {
            **state,
            "action": action,
            "user_id": request_data.get("user_id"),
            "plan_id": request_data.get("plan_id"),
        }

    def _route_action(self, state: StudyPlanProcessingState) -> str:
        """액션에 따른 라우팅."""
        action = state.get("action", "read")
        if action in ("create", "read", "generate"):
            return action
        return "read"

    async def _process_create_node(
        self, state: StudyPlanProcessingState
    ) -> StudyPlanProcessingState:
        """학습 계획 생성 노드 (Service 사용)."""
        request_data = state.get("request_data", {})
        user_id = state.get("user_id")

        try:
            request = StudyPlanCreateRequest(
                user_id=user_id,
                plan_json=request_data.get("plan_json", {}),
            )
            result = self._service.create_plan(request)
            return {**state, "result": result}

        except Exception as e:
            logger.error(f"[StudyPlanFlow] 학습 계획 생성 오류: {e}", exc_info=True)
            return {
                **state,
                "result": {"success": False, "error": str(e)},
                "error": str(e),
            }

    async def _process_read_node(
        self, state: StudyPlanProcessingState
    ) -> StudyPlanProcessingState:
        """학습 계획 조회 노드 (Service 사용)."""
        user_id = state.get("user_id")
        plan_id = state.get("plan_id")

        try:
            if plan_id:
                result = self._service.get_plan(plan_id)
            else:
                result = self._service.get_latest_plan(user_id)

            return {**state, "result": result}

        except Exception as e:
            logger.error(f"[StudyPlanFlow] 학습 계획 조회 오류: {e}", exc_info=True)
            return {
                **state,
                "result": {"success": False, "error": str(e)},
                "error": str(e),
            }

    async def _process_generate_node(
        self, state: StudyPlanProcessingState
    ) -> StudyPlanProcessingState:
        """AI 학습 계획 생성 노드 — 분석 + RAG + EXAONE 파이프라인.

        1단계: SolvingLogAnalyzer로 풀이 로그 분석
        2단계: 분석 결과 기반 RAG 쿼리 생성 → 합격 수기 검색
        3단계: 분석 결과 + RAG 컨텍스트를 EXAONE 프롬프트로 조합
        4단계: EXAONE으로 학습 계획 생성
        5단계: study_plans 테이블에 저장
        """
        request_data = state.get("request_data", {})
        request_text = state.get("request_text", "학습 계획을 세워줘")
        user_id = state.get("user_id")
        conn = request_data.get("_conn")
        llm = request_data.get("_llm")

        try:
            # ============================================================
            # Step 1: 풀이 로그 분석
            # ============================================================
            analysis = {"has_data": False}
            analysis_summary = "풀이 기록이 없어 분석할 수 없습니다."

            if conn is not None:
                try:
                    analyzer = SolvingLogAnalyzer(conn)
                    analysis = analyzer.analyze(user_id)
                    analysis_summary = SolvingLogAnalyzer.summarize_for_prompt(analysis)
                    logger.info(
                        f"[StudyPlanFlow] 풀이 로그 분석 완료: "
                        f"has_data={analysis.get('has_data')}"
                    )
                except Exception as e:
                    logger.warning(f"[StudyPlanFlow] 풀이 로그 분석 실패: {e}")

            # ============================================================
            # Step 2: 분석 기반 RAG 검색 쿼리 생성 + 합격 수기 검색
            # ============================================================
            rag_context = ""
            all_rag_results = []

            if conn is not None:
                try:
                    # 분석 결과에서 최적화된 검색 쿼리 생성
                    rag_queries = StudyPlanPromptBuilder.build_rag_queries_from_analysis(
                        analysis
                    )

                    # 각 쿼리로 멘토링 지식 검색
                    for query in rag_queries[:3]:  # 최대 3개 쿼리
                        results = search_mentoring_knowledge(
                            conn, query, top_k=2, similarity_threshold=0.25
                        )
                        all_rag_results.extend(results)

                    # 중복 제거 (id 기준) 및 유사도 내림차순 정렬
                    seen_ids = set()
                    unique_results = []
                    for r in all_rag_results:
                        if r["id"] not in seen_ids:
                            seen_ids.add(r["id"])
                            unique_results.append(r)
                    unique_results.sort(key=lambda x: x["similarity"], reverse=True)

                    # 상위 5개만 컨텍스트로 사용
                    rag_context = build_mentoring_context(
                        unique_results[:5], max_results=5
                    )

                    logger.info(
                        f"[StudyPlanFlow] RAG 검색 완료: "
                        f"{len(unique_results)}건 (쿼리 {len(rag_queries)}개)"
                    )
                except Exception as e:
                    logger.warning(f"[StudyPlanFlow] RAG 검색 실패: {e}")

            # ============================================================
            # Step 3: 사용자 프로필 정보 조회
            # ============================================================
            user_info = None
            if conn is not None:
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            SELECT display_name, daily_study_time, target_date, base_score
                            FROM users WHERE id = %s
                            """,
                            (user_id,),
                        )
                        row = cur.fetchone()
                        if row:
                            user_info = {
                                "display_name": row[0],
                                "daily_study_time": row[1],
                                "target_date": row[2].isoformat() if row[2] else None,
                                "base_score": row[3],
                            }
                except Exception as e:
                    logger.warning(f"[StudyPlanFlow] 사용자 정보 조회 실패: {e}")

            # ============================================================
            # Step 4: EXAONE으로 학습 계획 생성
            # ============================================================
            generated_plan = None
            generation_method = "template"

            if llm is not None:
                try:
                    # LLM이 로드되지 않았으면 로드
                    if not llm.is_loaded():
                        llm.load()

                    # 프롬프트 조합
                    prompt = StudyPlanPromptBuilder.build_prompt(
                        analysis_summary=analysis_summary,
                        rag_context=rag_context,
                        user_question=request_text,
                        user_info=user_info,
                    )

                    logger.info("[StudyPlanFlow] EXAONE에 학습 계획 생성 요청...")

                    # EXAONE 생성
                    raw_answer = llm.generate(
                        prompt,
                        max_new_tokens=2048,
                        temperature=0.7,
                        top_p=0.9,
                    )

                    # EXAONE 빈 응답 체크
                    if not raw_answer or not raw_answer.strip():
                        logger.warning(
                            "[StudyPlanFlow] EXAONE이 빈 응답을 반환, 템플릿으로 폴백"
                        )
                    else:
                        # JSON 파싱 시도
                        generated_plan = self._parse_plan_json(raw_answer)
                        generation_method = "exaone"
                        logger.info("[StudyPlanFlow] EXAONE 학습 계획 생성 완료")
                except Exception as e:
                    logger.warning(
                        f"[StudyPlanFlow] EXAONE 생성 실패, 템플릿으로 폴백: {e}"
                    )

            # EXAONE 실패 시 분석 데이터 기반 템플릿 폴백
            if generated_plan is None:
                generated_plan = self._generate_template_plan(analysis, user_info)
                generation_method = "template"

            # ============================================================
            # Step 5: 기존 학습 계획 전체 삭제 후 새로 저장
            # ============================================================
            # 기존 계획 삭제 (AI 플랜 재생성 시 이전 버전 모두 제거)
            delete_result = self._service.delete_user_plans(user_id)
            if delete_result.get("success"):
                deleted_count = delete_result.get("deleted_count", 0)
                if deleted_count > 0:
                    logger.info(
                        f"[StudyPlanFlow] 기존 학습 계획 {deleted_count}건 삭제 완료"
                    )

            plan_data = {
                **generated_plan,
                "generated_by": generation_method,
                "analysis_summary": analysis_summary if analysis.get("has_data") else None,
                "rag_results_count": len(all_rag_results),
            }

            request = StudyPlanCreateRequest(
                user_id=user_id,
                plan_json=plan_data,
            )
            result = self._service.create_plan(request)

            if result.get("success"):
                result["message"] = (
                    f"AI 학습 계획이 생성되었습니다. (방식: {generation_method})"
                )

            # 응답에 분석 요약 포함
            result["analysis"] = analysis if analysis.get("has_data") else None
            result["generation_method"] = generation_method

            return {
                **state,
                "result": result,
                "generated_plan": generated_plan,
                "analysis": analysis,
                "rag_context": rag_context,
            }

        except Exception as e:
            logger.error(
                f"[StudyPlanFlow] AI 학습 계획 생성 오류: {e}", exc_info=True
            )
            return {
                **state,
                "result": {"success": False, "error": str(e)},
                "error": str(e),
            }

    # ========================================================================
    # 유틸 메서드
    # ========================================================================

    def _parse_plan_json(self, raw_text: str) -> Optional[Dict[str, Any]]:
        """EXAONE의 응답에서 JSON 학습 계획을 파싱합니다."""
        try:
            # 전체 텍스트가 JSON인 경우
            return json.loads(raw_text)
        except json.JSONDecodeError:
            pass

        # ```json ... ``` 블록 추출 시도
        import re

        json_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", raw_text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # { ... } 블록 추출 시도
        brace_match = re.search(r"\{[\s\S]*\}", raw_text)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        # JSON 파싱 실패 시 텍스트 형태로 저장
        logger.warning("[StudyPlanFlow] JSON 파싱 실패, 텍스트 형태로 저장")
        return {
            "raw_answer": raw_text,
            "summary": raw_text[:500],
            "parse_failed": True,
        }

    def _generate_template_plan(
        self,
        analysis: Dict[str, Any],
        user_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """분석 데이터 기반 템플릿 학습 계획을 생성합니다.

        EXAONE이 사용 불가능할 때의 폴백입니다.
        """
        daily_minutes = 180  # 기본 3시간
        if user_info and user_info.get("daily_study_time"):
            daily_minutes = user_info["daily_study_time"]

        hours = daily_minutes / 60

        # 과목 우선순위 결정
        weak = analysis.get("weak_subjects", [])
        strong = analysis.get("strong_subjects", [])
        weak_names = [w["subject"] for w in weak]
        strong_names = [s["subject"] for s in strong]
        all_subjects = list({s["subject"] for s in analysis.get("subject_stats", [])})

        # 과목이 없으면 기본 과목
        if not all_subjects:
            all_subjects = ["한국사", "행정법", "행정학", "국어", "영어"]
            weak_names = all_subjects[:2]

        # 주간 스케줄 생성
        schedule = []
        days = ["월", "화", "수", "목", "금", "토", "일"]

        for i, day in enumerate(days):
            if day == "토":
                schedule.append({
                    "day": day,
                    "subjects": ["모의고사"],
                    "focus": "실전 연습 및 시간 관리 훈련",
                    "hours": round(hours + 1, 1),
                })
            elif day == "일":
                schedule.append({
                    "day": day,
                    "subjects": ["복습", "오답정리"],
                    "focus": "주간 오답 복습 및 개념 정리",
                    "hours": round(hours * 0.7, 1),
                })
            else:
                # 취약 과목 우선 배정
                day_subjects = []
                if weak_names:
                    day_subjects.append(weak_names[i % len(weak_names)])
                remaining = [s for s in all_subjects if s not in day_subjects]
                if remaining:
                    day_subjects.append(remaining[i % len(remaining)])

                focus = "취약 과목 집중 보강" if day_subjects[0] in weak_names else "균형 학습"
                schedule.append({
                    "day": day,
                    "subjects": day_subjects[:2],
                    "focus": focus,
                    "hours": round(hours, 1),
                })

        # 추천 메시지 생성
        recommendations = []

        if weak_names:
            recommendations.append(
                f"취약 과목({', '.join(weak_names)})에 학습 시간을 더 배분하세요."
            )

        repeated = analysis.get("repeated_wrong", [])
        if repeated:
            rep_subjects = list({rw["subject"] for rw in repeated[:3]})
            recommendations.append(
                f"반복 오답 과목({', '.join(rep_subjects)})의 기본 개념을 다시 점검하세요."
            )

        slow = analysis.get("slow_questions", [])
        if len(slow) >= 3:
            recommendations.append(
                "풀이 속도가 느린 유형이 있습니다. 시간을 재면서 연습하세요."
            )

        trend = analysis.get("trend", [])
        if len(trend) >= 2:
            last = trend[-1]["score"]
            first = trend[0]["score"]
            if last > first:
                recommendations.append(
                    f"점수가 {first:.0f}점 → {last:.0f}점으로 상승 중입니다. 현재 페이스를 유지하세요!"
                )
            elif last < first:
                recommendations.append(
                    "최근 점수가 하락 추세입니다. 컨디션 관리와 기본 개념 복습에 집중하세요."
                )

        if not recommendations:
            recommendations = [
                "매일 일정한 시간에 학습하세요.",
                "약점 과목을 집중적으로 보완하세요.",
                "주 1회 모의고사를 통해 실전 감각을 유지하세요.",
            ]

        return {
            "summary": self._generate_template_summary(analysis),
            "priority_subjects": weak_names if weak_names else all_subjects[:3],
            "weekly_schedule": schedule,
            "specific_advice": recommendations,
            "motivation": "꾸준히 노력하면 반드시 합격할 수 있습니다. 화이팅! 💪",
        }

    def _generate_template_summary(self, analysis: Dict[str, Any]) -> str:
        """분석 데이터 기반 요약을 생성합니다."""
        if not analysis.get("has_data"):
            return "아직 풀이 기록이 없습니다. 모의고사를 풀고 나면 맞춤 분석이 가능합니다."

        acc = analysis.get("overall_accuracy", 0)
        total = analysis.get("total_solved", 0)
        weak = analysis.get("weak_subjects", [])

        summary_parts = [f"총 {total}문제를 풀었고, 전체 정답률은 {acc:.1f}%입니다."]

        if weak:
            weak_strs = [f"{w['subject']}({w['accuracy']:.0f}%)" for w in weak]
            summary_parts.append(f"취약 과목은 {', '.join(weak_strs)}입니다.")

        if acc >= 80:
            summary_parts.append("전반적으로 우수한 성적이며, 실전 대비에 집중하면 좋겠습니다.")
        elif acc >= 60:
            summary_parts.append("기본기는 갖춰져 있으므로, 취약 과목 보강에 집중하세요.")
        else:
            summary_parts.append("기초 개념 학습과 오답 복습에 집중하는 것을 권장합니다.")

        return " ".join(summary_parts)

    async def _finalize_node(
        self, state: StudyPlanProcessingState
    ) -> StudyPlanProcessingState:
        """최종 정리 노드."""
        return state

    async def process_study_plan_request(
        self, request_text: str, request_data: dict
    ) -> dict:
        """StudyPlan 요청 처리.

        Args:
            request_text: 요청 텍스트
            request_data: 요청 데이터 (action, user_id, plan_id, _conn, _llm 등)

        Returns:
            처리 결과 딕셔너리
        """
        logger.info("[StudyPlanFlow] 요청 처리 시작")

        initial_state: StudyPlanProcessingState = {
            "request_text": request_text,
            "request_data": request_data,
            "action": None,
            "user_id": None,
            "plan_id": None,
            "result": None,
            "error": None,
            "metadata": None,
            "generated_plan": None,
            "analysis": None,
            "rag_context": None,
        }

        try:
            final_state = await self._graph.ainvoke(initial_state)
            result = final_state.get("result")
            return (
                result if result else {"success": False, "error": "처리 결과가 없습니다."}
            )
        except Exception as e:
            logger.error(f"[StudyPlanFlow] 처리 오류: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
