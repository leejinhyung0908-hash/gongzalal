"""데이터베이스 저장 결과 상태 스키마 정의."""

from typing import List, Dict, Any, TypedDict

class DatabaseResult(TypedDict):
"""데이터베이스 저장 결과 상세 정보.

모든 도메인(Player, Team, Stadium, Schedule)의 상태 스키마에서
데이터베이스 저장 결과를 표현하기 위해 사용하는 공통 TypedDict.
"""

success_count: int # 성공한 레코드 수
failure_count: int # 실패한 레코드 수
success_ids: List[int]  # 성공한 레코드 ID 목록
failure_ids: List[int]  # 실패한 레코드 ID 목록
errors: List[Dict[str, Any]]  # 실패한 레코드의 에러 정보
