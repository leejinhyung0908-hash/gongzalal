"""풀이 로그 분석 모듈.

user_solving_logs + questions + exams 테이블을 조인하여
사용자의 약점/강점, 시간 분석, 성취도 추이 등을 산출합니다.

LLM 없이 순수 SQL + Python 연산으로 동작합니다.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import psycopg

logger = logging.getLogger(__name__)


class SolvingLogAnalyzer:
    """사용자 풀이 로그 분석기.

    user_solving_logs를 questions/exams와 조인하여
    과목별 정답률, 취약 과목, 시간 분석, 반복 오답 등
    구조화된 분석 JSON을 산출합니다.
    """

    def __init__(self, conn: psycopg.Connection):
        self._conn = conn

    # ========================================================================
    # 메인 분석 메서드
    # ========================================================================

    def analyze(self, user_id: int) -> Dict[str, Any]:
        """사용자의 풀이 로그를 종합 분석합니다.

        Args:
            user_id: 사용자 ID

        Returns:
            구조화된 분석 결과 JSON
        """
        logger.info(f"[SolvingLogAnalyzer] 분석 시작: user_id={user_id}")

        try:
            # 1) 전체 요약 통계
            overall = self._get_overall_stats(user_id)
            if overall["total_solved"] == 0:
                logger.info(f"[SolvingLogAnalyzer] 풀이 데이터 없음: user_id={user_id}")
                return {
                    "user_id": user_id,
                    "analysis_date": datetime.now().isoformat(),
                    "total_solved": 0,
                    "has_data": False,
                    "message": "풀이 기록이 없습니다. 모의고사를 먼저 풀어주세요.",
                }

            # 2) 과목별 분석
            subject_stats = self._get_subject_stats(user_id)

            # 3) 취약/강점 과목 도출
            weak_subjects = self._extract_weak_subjects(subject_stats)
            strong_subjects = self._extract_strong_subjects(subject_stats)

            # 4) 시간 과다 소요 문항
            slow_questions = self._get_slow_questions(user_id)

            # 5) 반복 오답 문항
            repeated_wrong = self._get_repeated_wrong(user_id)

            # 6) 최근 모의고사 추이
            trend = self._get_score_trend(user_id)

            # 7) 오답 과목 분포
            wrong_distribution = self._get_wrong_subject_distribution(user_id)

            result = {
                "user_id": user_id,
                "analysis_date": datetime.now().isoformat(),
                "has_data": True,
                # 전체 요약
                "total_solved": overall["total_solved"],
                "overall_accuracy": overall["accuracy"],
                "overall_avg_time": overall["avg_time"],
                # 과목별 상세
                "subject_stats": subject_stats,
                "weak_subjects": weak_subjects,
                "strong_subjects": strong_subjects,
                # 문항 수준 인사이트
                "slow_questions": slow_questions,
                "repeated_wrong": repeated_wrong,
                # 추이
                "trend": trend,
                # 오답 분포
                "wrong_distribution": wrong_distribution,
            }

            logger.info(
                f"[SolvingLogAnalyzer] 분석 완료: user_id={user_id}, "
                f"총 {overall['total_solved']}문제, 정답률 {overall['accuracy']:.1f}%"
            )
            return result

        except Exception as e:
            logger.error(f"[SolvingLogAnalyzer] 분석 실패: {e}", exc_info=True)
            return {
                "user_id": user_id,
                "analysis_date": datetime.now().isoformat(),
                "has_data": False,
                "error": str(e),
            }

    # ========================================================================
    # 1. 전체 요약 통계
    # ========================================================================

    def _get_overall_stats(self, user_id: int) -> Dict[str, Any]:
        """전체 풀이 통계를 조회합니다."""
        with self._conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) AS total_solved,
                    COUNT(CASE WHEN l.selected_answer = q.answer_key THEN 1 END) AS correct_count,
                    AVG(l.time_spent) AS avg_time
                FROM user_solving_logs l
                JOIN questions q ON l.question_id = q.id
                WHERE l.user_id = %s
                  AND l.selected_answer IS NOT NULL
                """,
                (user_id,),
            )
            row = cur.fetchone()

        total = row[0] or 0
        correct = row[1] or 0
        avg_time = round(float(row[2]), 1) if row[2] else 0.0
        accuracy = round(correct / total * 100, 1) if total > 0 else 0.0

        return {
            "total_solved": total,
            "correct_count": correct,
            "wrong_count": total - correct,
            "accuracy": accuracy,
            "avg_time": avg_time,
        }

    # ========================================================================
    # 2. 과목별 분석
    # ========================================================================

    def _get_subject_stats(self, user_id: int) -> List[Dict[str, Any]]:
        """과목별 정답률, 평균 풀이 시간, 총 풀이 수를 산출합니다."""
        with self._conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    e.subject,
                    COUNT(*) AS total,
                    COUNT(CASE WHEN l.selected_answer = q.answer_key THEN 1 END) AS correct,
                    AVG(l.time_spent) AS avg_time,
                    MIN(l.time_spent) AS min_time,
                    MAX(l.time_spent) AS max_time
                FROM user_solving_logs l
                JOIN questions q ON l.question_id = q.id
                JOIN exams e ON q.exam_id = e.id
                WHERE l.user_id = %s
                  AND l.selected_answer IS NOT NULL
                GROUP BY e.subject
                ORDER BY e.subject
                """,
                (user_id,),
            )
            rows = cur.fetchall()

        results = []
        for r in rows:
            total = r[1]
            correct = r[2]
            accuracy = round(correct / total * 100, 1) if total > 0 else 0.0
            avg_time = round(float(r[3]), 1) if r[3] else 0.0

            results.append({
                "subject": r[0],
                "total": total,
                "correct": correct,
                "wrong": total - correct,
                "accuracy": accuracy,
                "avg_time": avg_time,
                "min_time": r[4],
                "max_time": r[5],
            })

        return results

    # ========================================================================
    # 3. 취약/강점 과목 도출
    # ========================================================================

    def _extract_weak_subjects(
        self, subject_stats: List[Dict[str, Any]], top_n: int = 3
    ) -> List[Dict[str, Any]]:
        """정답률이 낮은 취약 과목 Top N을 추출합니다."""
        # 최소 5문제 이상 푼 과목만 대상
        filtered = [s for s in subject_stats if s["total"] >= 5]
        sorted_by_accuracy = sorted(filtered, key=lambda x: x["accuracy"])
        return sorted_by_accuracy[:top_n]

    def _extract_strong_subjects(
        self, subject_stats: List[Dict[str, Any]], top_n: int = 3
    ) -> List[Dict[str, Any]]:
        """정답률이 높은 강점 과목 Top N을 추출합니다."""
        filtered = [s for s in subject_stats if s["total"] >= 5]
        sorted_by_accuracy = sorted(filtered, key=lambda x: x["accuracy"], reverse=True)
        return sorted_by_accuracy[:top_n]

    # ========================================================================
    # 4. 시간 과다 소요 문항
    # ========================================================================

    def _get_slow_questions(
        self, user_id: int, multiplier: float = 1.5, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """평균 풀이 시간의 multiplier배를 초과한 문항을 조회합니다."""
        with self._conn.cursor() as cur:
            # 사용자의 평균 풀이 시간 조회
            cur.execute(
                """
                SELECT AVG(time_spent)
                FROM user_solving_logs
                WHERE user_id = %s AND time_spent IS NOT NULL
                """,
                (user_id,),
            )
            avg_row = cur.fetchone()
            avg_time = float(avg_row[0]) if avg_row and avg_row[0] else 60.0

            threshold = avg_time * multiplier

            # 기준치를 초과한 문항 조회
            cur.execute(
                """
                SELECT
                    l.question_id,
                    e.subject,
                    q.question_no,
                    l.time_spent,
                    CASE WHEN l.selected_answer = q.answer_key THEN true ELSE false END AS is_correct,
                    l.created_at
                FROM user_solving_logs l
                JOIN questions q ON l.question_id = q.id
                JOIN exams e ON q.exam_id = e.id
                WHERE l.user_id = %s
                  AND l.time_spent > %s
                ORDER BY l.time_spent DESC
                LIMIT %s
                """,
                (user_id, threshold, limit),
            )
            rows = cur.fetchall()

        results = []
        for r in rows:
            results.append({
                "question_id": r[0],
                "subject": r[1],
                "question_no": r[2],
                "time_spent": r[3],
                "is_correct": r[4],
                "threshold": round(threshold, 1),
                "created_at": r[5].isoformat() if r[5] else None,
            })

        return results

    # ========================================================================
    # 5. 반복 오답 문항
    # ========================================================================

    def _get_repeated_wrong(
        self, user_id: int, min_count: int = 2, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """동일 문항을 2회 이상 틀린 반복 오답 목록을 조회합니다."""
        with self._conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    l.question_id,
                    e.subject,
                    q.question_no,
                    q.question_text,
                    COUNT(*) AS wrong_count
                FROM user_solving_logs l
                JOIN questions q ON l.question_id = q.id
                JOIN exams e ON q.exam_id = e.id
                WHERE l.user_id = %s
                  AND l.selected_answer IS NOT NULL
                  AND l.selected_answer != q.answer_key
                GROUP BY l.question_id, e.subject, q.question_no, q.question_text
                HAVING COUNT(*) >= %s
                ORDER BY COUNT(*) DESC
                LIMIT %s
                """,
                (user_id, min_count, limit),
            )
            rows = cur.fetchall()

        results = []
        for r in rows:
            text_preview = r[3][:80] + "..." if r[3] and len(r[3]) > 80 else r[3]
            results.append({
                "question_id": r[0],
                "subject": r[1],
                "question_no": r[2],
                "question_preview": text_preview,
                "wrong_count": r[4],
            })

        return results

    # ========================================================================
    # 6. 최근 모의고사 점수 추이
    # ========================================================================

    def _get_score_trend(
        self, user_id: int, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """날짜별 모의고사 점수 추이를 산출합니다.

        같은 날에 풀린 문항들을 하나의 세션으로 간주하여
        날짜별 정답률을 계산합니다.
        """
        with self._conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    DATE(l.created_at) AS solve_date,
                    COUNT(*) AS total,
                    COUNT(CASE WHEN l.selected_answer = q.answer_key THEN 1 END) AS correct,
                    AVG(l.time_spent) AS avg_time
                FROM user_solving_logs l
                JOIN questions q ON l.question_id = q.id
                WHERE l.user_id = %s
                  AND l.selected_answer IS NOT NULL
                GROUP BY DATE(l.created_at)
                HAVING COUNT(*) >= 5
                ORDER BY DATE(l.created_at) DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
            rows = cur.fetchall()

        results = []
        for r in rows:
            total = r[1]
            correct = r[2]
            score = round(correct / total * 100, 1) if total > 0 else 0.0
            results.append({
                "date": r[0].isoformat() if r[0] else None,
                "total": total,
                "correct": correct,
                "score": score,
                "avg_time": round(float(r[3]), 1) if r[3] else 0.0,
            })

        # 시간순 정렬 (오래된 것 먼저)
        results.reverse()
        return results

    # ========================================================================
    # 7. 오답 과목 분포
    # ========================================================================

    def _get_wrong_subject_distribution(self, user_id: int) -> List[Dict[str, Any]]:
        """오답 문항의 과목별 분포를 산출합니다."""
        with self._conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    e.subject,
                    COUNT(*) AS wrong_count
                FROM user_solving_logs l
                JOIN questions q ON l.question_id = q.id
                JOIN exams e ON q.exam_id = e.id
                WHERE l.user_id = %s
                  AND l.selected_answer IS NOT NULL
                  AND l.selected_answer != q.answer_key
                GROUP BY e.subject
                ORDER BY COUNT(*) DESC
                """,
                (user_id,),
            )
            rows = cur.fetchall()

        total_wrong = sum(r[1] for r in rows) if rows else 0
        results = []
        for r in rows:
            pct = round(r[1] / total_wrong * 100, 1) if total_wrong > 0 else 0.0
            results.append({
                "subject": r[0],
                "wrong_count": r[1],
                "percentage": pct,
            })

        return results

    # ========================================================================
    # 유틸: 분석 결과를 자연어 요약으로 변환
    # ========================================================================

    @staticmethod
    def summarize_for_prompt(analysis: Dict[str, Any]) -> str:
        """분석 결과를 EXAONE 프롬프트에 넣을 자연어 요약으로 변환합니다.

        LLM 토큰을 절약하기 위해 Python 문자열 포맷팅으로 처리합니다.

        Args:
            analysis: analyze() 메서드의 반환값

        Returns:
            자연어 요약 문자열
        """
        if not analysis.get("has_data"):
            return "풀이 기록이 없어 분석할 수 없습니다."

        parts = []

        # 1) 전체 요약
        parts.append(
            f"총 {analysis['total_solved']}문제 풀이, "
            f"전체 정답률 {analysis['overall_accuracy']:.1f}%, "
            f"평균 풀이 시간 {analysis['overall_avg_time']:.0f}초"
        )

        # 2) 취약 과목
        weak = analysis.get("weak_subjects", [])
        if weak:
            weak_strs = [
                f"{w['subject']}({w['accuracy']:.0f}%, 평균 {w['avg_time']:.0f}초)"
                for w in weak
            ]
            parts.append(f"취약 과목: {', '.join(weak_strs)}")

        # 3) 강점 과목
        strong = analysis.get("strong_subjects", [])
        if strong:
            strong_strs = [
                f"{s['subject']}({s['accuracy']:.0f}%)"
                for s in strong
            ]
            parts.append(f"강점 과목: {', '.join(strong_strs)}")

        # 4) 시간 과다 문항
        slow = analysis.get("slow_questions", [])
        if slow:
            slow_strs = [
                f"{sq['subject']} {sq['question_no']}번({sq['time_spent']}초, {'정답' if sq['is_correct'] else '오답'})"
                for sq in slow[:5]
            ]
            parts.append(f"시간 과다 문항: {', '.join(slow_strs)}")

        # 5) 반복 오답
        repeated = analysis.get("repeated_wrong", [])
        if repeated:
            rep_strs = [
                f"{rw['subject']} {rw['question_no']}번({rw['wrong_count']}회 오답)"
                for rw in repeated[:5]
            ]
            parts.append(f"반복 오답 문항: {', '.join(rep_strs)}")

        # 6) 점수 추이
        trend = analysis.get("trend", [])
        if len(trend) >= 2:
            first_score = trend[0]["score"]
            last_score = trend[-1]["score"]
            diff = last_score - first_score
            direction = "상승" if diff > 0 else ("하락" if diff < 0 else "유지")
            parts.append(
                f"최근 점수 추이: {first_score:.0f}점 → {last_score:.0f}점 ({direction}, {abs(diff):.1f}점)"
            )

        # 7) 오답 과목 분포
        wrong_dist = analysis.get("wrong_distribution", [])
        if wrong_dist:
            dist_strs = [
                f"{wd['subject']}({wd['wrong_count']}개, {wd['percentage']:.0f}%)"
                for wd in wrong_dist[:5]
            ]
            parts.append(f"오답 과목 분포: {', '.join(dist_strs)}")

        return "\n- ".join(["[사용자 풀이 분석]"] + parts)

