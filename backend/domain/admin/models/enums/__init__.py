"""ENUM 타입 정의.

데이터베이스에서 사용하는 ENUM 타입들을 정의합니다.
"""

from __future__ import annotations

import enum


class EmploymentStatus(str, enum.Enum):
    """사용자 직장 상태."""

    EMPLOYED = "재직"
    UNEMPLOYED = "무직"
    STUDENT = "학생"
    SELF_EMPLOYED = "자영업"
    OTHER = "기타"


class CommentaryType(str, enum.Enum):
    """해설 유형."""

    HANDWRITTEN = "수기"           # 일반 수기 해설
    SUCCESS_STORY = "합격수기"     # 합격 수기 (합격자 경험담)
    EXPLANATION = "해설"           # 문제 해설
    MENTORING = "멘토링"           # AI 멘토링 응답

