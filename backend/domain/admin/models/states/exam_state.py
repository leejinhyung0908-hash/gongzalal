#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exam(시험) 상태 정의 (State Machine용)

새 테이블 구조:
- Exams: 시험 메타데이터
- Questions: 개별 문제 정보
"""

from enum import Enum
from typing import TypedDict, Optional, Dict, Any, List

from backend.domain.shared.models.states.base_state import BaseProcessingState


class ExamProcessingState(TypedDict):
    """Exam 처리 상태 (LangGraph용)."""

    # 요청 데이터
    request_text: Optional[str]
    request_data: Optional[Dict[str, Any]]

    # 게이트웨이 분류 결과
    gateway: Optional[str]  # "RULE_BASED", "POLICY_BASED", "BLOCK"
    gateway_confidence: Optional[float]

    # 의도 분류 결과 (POLICY_BASED인 경우)
    intent_result: Optional[Dict[str, Any]]

    # 엔티티 추출 결과
    entities: Optional[Dict[str, Any]]

    # 전략 판단 결과
    strategy: Optional[str]  # "rule_based", "policy_based"

    # KoELECTRA 분석 결과
    koelectra_result: Optional[Dict[str, Any]]

    # 처리 결과
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    metadata: Optional[Dict[str, Any]]


class ExamState(TypedDict):
    """Exam 테이블 데이터 상태.

    `backend/domain/admin/models/bases/exam.py`의
    Exam SQLAlchemy 모델을 참조하여 작성한 TypedDict입니다.
    """

    # 기본 식별자
    id: int

    # 시험 메타
    year: int
    exam_type: str
    series: Optional[str]
    grade: Optional[str]
    subject: str

    # 벡터 임베딩 (1024차원, KURE-v1)
    exam_vector: Optional[List[float]]

    # 타임스탬프 (ISO 형식 문자열)
    created_at: Optional[str]
    updated_at: Optional[str]


class QuestionState(TypedDict):
    """Question 테이블 데이터 상태.

    `backend/domain/admin/models/bases/question.py`의
    Question SQLAlchemy 모델을 참조하여 작성한 TypedDict입니다.
    """

    # 기본 식별자
    id: int

    # 외래키
    exam_id: int

    # 문제 메타
    question_no: int
    question_text: str
    sub_category: Optional[str]
    answer_key: str
    ind: Optional[bool]
    source_pdf: Optional[str]
    extra_json: Optional[Dict[str, Any]]

    # 타임스탬프 (ISO 형식 문자열)
    created_at: Optional[str]
    updated_at: Optional[str]


class QuestionImageState(TypedDict):
    """QuestionImage 테이블 데이터 상태.

    `backend/domain/admin/models/bases/question_image.py`의
    QuestionImage SQLAlchemy 모델을 참조하여 작성한 TypedDict입니다.
    """

    # 기본 식별자
    id: int
    question_id: int

    # 이미지 데이터
    file_path: str
    coordinates_json: Optional[Dict[str, Any]]
    image_type: Optional[str]

    # 타임스탬프
    created_at: Optional[str]
