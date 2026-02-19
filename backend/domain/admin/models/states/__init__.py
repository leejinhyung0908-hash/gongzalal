"""Admin 도메인 상태(Enum/TypedDict) 모음.

새 테이블 구조에 맞춘 상태 정의들을 export 합니다.
"""

# User 관련 상태
from backend.domain.admin.models.states.user_state import (  # noqa: F401
    UserState,
    EmploymentStatusState,
    UserProcessingState,
    UserDataState,
    StudyPlanState,
    UserSolvingLogState,
)

# Exam/Question 관련 상태
from backend.domain.admin.models.states.exam_state import (  # noqa: F401
    ExamProcessingState,
    ExamState,
    QuestionState,
    QuestionImageState,
)

# Commentary 관련 상태
from backend.domain.admin.models.states.commentary_state import (  # noqa: F401
    CommentaryState,
    CommentaryTypeState,
    CommentaryProcessingState,
    CommentaryDataState,
    AudioNoteState,
)

# Chat 관련 상태
from backend.domain.admin.models.states.chat_state import (  # noqa: F401
    ChatProcessingState,
)

__all__ = [
    # User
    "UserState",
    "EmploymentStatusState",
    "UserProcessingState",
    "UserDataState",
    "StudyPlanState",
    "UserSolvingLogState",
    # Exam/Question
    "ExamProcessingState",
    "ExamState",
    "QuestionState",
    "QuestionImageState",
    # Commentary
    "CommentaryState",
    "CommentaryTypeState",
    "CommentaryProcessingState",
    "CommentaryDataState",
    "AudioNoteState",
    # Chat
    "ChatProcessingState",
]
