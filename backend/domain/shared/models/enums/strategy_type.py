"""데이터 처리 전략 타입 Enum 정의."""

from enum import Enum

class StrategyType(str, Enum):
"""데이터 처리 전략 타입."""

POLICY = "policy" # 정책 기반 처리
RULE = "rule" # 규칙 기반 처리
