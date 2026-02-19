#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Commentary(해설/합격수기) 상태 정의 (State Machine용)

새 테이블 구조:
- Commentaries: 문제 해설 + 합격 수기
- Audio_Notes: TTS 오디오 파일
"""

from enum import Enum
from typing import TypedDict, Optional, Dict, Any, List

from backend.domain.shared.models.states.base_state import BaseProcessingState


class CommentaryState(str, Enum):
    """해설/수기 단위 상태."""

    # 아직 아무 것도 하지 않음(레코드가 없을 수도 있음)
    NEW = "new"

    # 풀이/학습 흐름
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"      # 선택지 제출(정오답 판정 가능)
    REVIEWED = "reviewed"        # 해설 작성/복습 완료

    # 관리
    BOOKMARKED = "bookmarked"
    ARCHIVED = "archived"

    # 승인 상태 (합격 수기용)
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"


class CommentaryTypeState(str, Enum):
    """해설 유형 (DB ENUM과 동기화)."""

    HANDWRITTEN = "수기"
    SUCCESS_STORY = "합격수기"
    EXPLANATION = "해설"
    MENTORING = "멘토링"


class CommentaryProcessingState(BaseProcessingState):
    """Commentary 처리 상태 (LangGraph용)."""

    # KoELECTRA 분석 결과
    spam_prob: Optional[float]
    label: Optional[str]
    confidence: Optional[str]

    # 전략 판단 결과
    strategy: Optional[str]  # "rule_based", "policy_based"


class CommentaryDataState(TypedDict):
    """Commentary 테이블 데이터 상태.

    `backend/domain/admin/models/bases/commentary.py`의
    Commentary SQLAlchemy 모델을 참조하여 작성한 TypedDict입니다.
    """

    # 기본 식별자
    id: int
    user_id: Optional[int]
    question_id: Optional[int]

    # 해설 데이터
    body: str
    type: Optional[str]

    # 합격 수기 전용 필드
    success_period: Optional[str]
    target_exam: Optional[str]
    final_score: Optional[int]
    approved: bool

    # 벡터 임베딩 (1024차원, KURE-v1)
    commentary_vector: Optional[List[float]]

    # 타임스탬프
    created_at: Optional[str]
    updated_at: Optional[str]


class AudioNoteState(TypedDict):
    """AudioNote 테이블 데이터 상태.

    `backend/domain/admin/models/bases/audio_note.py`의
    AudioNote SQLAlchemy 모델을 참조하여 작성한 TypedDict입니다.
    """

    # 기본 식별자
    id: int
    commentary_id: int

    # 오디오 데이터
    file_path: str
    voice_type: Optional[str]
    duration: Optional[int]

    # 타임스탬프
    created_at: Optional[str]
