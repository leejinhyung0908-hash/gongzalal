"""Admin 도메인 레포지토리.

새 테이블 구조에 맞춘 Repository 패턴 구현:
- ExamRepository: 시험/문제 데이터
- CommentaryRepository: 해설/합격수기 데이터
- UserRepository: 사용자 데이터
- StudyPlanRepository: 학습 계획 데이터
- SolvingLogRepository: 풀이 기록/오답노트 데이터
- AudioNoteRepository: 오디오 해설 데이터
"""

from backend.domain.admin.hub.repositories.exam_repository import ExamRepository
from backend.domain.admin.hub.repositories.commentary_repository import CommentaryRepository
from backend.domain.admin.hub.repositories.user_repository import UserRepository
from backend.domain.admin.hub.repositories.study_plan_repository import StudyPlanRepository
from backend.domain.admin.hub.repositories.solving_log_repository import SolvingLogRepository
from backend.domain.admin.hub.repositories.audio_note_repository import AudioNoteRepository

__all__ = [
    "ExamRepository",
    "CommentaryRepository",
    "UserRepository",
    "StudyPlanRepository",
    "SolvingLogRepository",
    "AudioNoteRepository",
]

