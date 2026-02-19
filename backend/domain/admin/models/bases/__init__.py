"""SQLAlchemy 모델 bases 모듈.

모든 테이블 모델들을 export 합니다.
"""

from backend.domain.shared.bases import Base, TimestampMixin  # noqa: F401

# 사용자 관련
from backend.domain.admin.models.bases.user import User  # noqa: F401

# 시험/문제 관련
from backend.domain.admin.models.bases.exam import Exam  # noqa: F401
from backend.domain.admin.models.bases.question import Question  # noqa: F401
from backend.domain.admin.models.bases.question_image import QuestionImage  # noqa: F401

# 학습 계획 관련
from backend.domain.admin.models.bases.study_plan import StudyPlan  # noqa: F401

# 사용자 활동 관련
from backend.domain.admin.models.bases.user_solving_log import UserSolvingLog  # noqa: F401

# 해설 관련
from backend.domain.admin.models.bases.commentary import Commentary  # noqa: F401
from backend.domain.admin.models.bases.audio_note import AudioNote  # noqa: F401

# 멘토링 지식
from backend.domain.admin.models.bases.mentoring_knowledge import MentoringKnowledge  # noqa: F401

__all__ = [
    "Base",
    "TimestampMixin",
    "User",
    "Exam",
    "Question",
    "QuestionImage",
    "StudyPlan",
    "UserSolvingLog",
    "Commentary",
    "AudioNote",
    "MentoringKnowledge",
]
