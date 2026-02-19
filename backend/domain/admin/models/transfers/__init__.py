"""Admin 도메인 Transfer(Pydantic) 모델 모음.

새 테이블 구조에 맞춘 Pydantic 모델들을 export 합니다.
"""

# 기존 모델 (호환성 유지)
from backend.domain.admin.models.transfers.chat_model import (  # noqa: F401
    ChatRequest,
    ChatResponse,
    QLoRARequest,
    QLoRAResponse,
)
from backend.domain.admin.models.transfers.base_model import (  # noqa: F401
    GatewayRequest,
    GatewayResponse,
)
from backend.domain.admin.models.transfers.state_model import (  # noqa: F401
    RequestHistoryState,
    SessionStateState,
)

# 새 테이블 구조 모델
# Exam 관련
from backend.domain.admin.models.transfers.exam_transfer import (  # noqa: F401
    ExamTransfer,
    ExamCreateRequest,
    ExamUpdateRequest,
    ExamSearchRequest,
)

# Question 관련
from backend.domain.admin.models.transfers.question_transfer import (  # noqa: F401
    QuestionTransfer,
    QuestionWithExamTransfer,
    QuestionCreateRequest,
    QuestionUpdateRequest,
    QuestionSearchRequest,
    QuestionImageTransfer,
    QuestionAnswerResponse,
)

# User 관련
from backend.domain.admin.models.transfers.user_transfer import (  # noqa: F401
    UserTransfer,
    UserCreateRequest,
    UserUpdateRequest,
    UserResponse,
    StudyPlanTransfer,
    StudyPlanCreateRequest,
    StudyPlanUpdateRequest,
    UserSolvingLogTransfer,
    UserSolvingLogCreateRequest,
    UserSolvingLogResponse,
)

# Commentary 관련
from backend.domain.admin.models.transfers.commentary_transfer import (  # noqa: F401
    CommentaryTransfer,
    CommentaryCreateRequest,
    CommentaryUpdateRequest,
    CommentaryResponse,
    SuccessStoryCreateRequest,
    SuccessStorySearchRequest,
    AudioNoteTransfer,
    AudioNoteCreateRequest,
    AudioNoteResponse,
)


__all__ = [
    # 기존 모델
    "ChatRequest",
    "ChatResponse",
    "QLoRARequest",
    "QLoRAResponse",
    "GatewayRequest",
    "GatewayResponse",
    "RequestHistoryState",
    "SessionStateState",
    # Exam
    "ExamTransfer",
    "ExamCreateRequest",
    "ExamUpdateRequest",
    "ExamSearchRequest",
    # Question
    "QuestionTransfer",
    "QuestionWithExamTransfer",
    "QuestionCreateRequest",
    "QuestionUpdateRequest",
    "QuestionSearchRequest",
    "QuestionImageTransfer",
    "QuestionAnswerResponse",
    # User
    "UserTransfer",
    "UserCreateRequest",
    "UserUpdateRequest",
    "UserResponse",
    "StudyPlanTransfer",
    "StudyPlanCreateRequest",
    "StudyPlanUpdateRequest",
    "UserSolvingLogTransfer",
    "UserSolvingLogCreateRequest",
    "UserSolvingLogResponse",
    # Commentary
    "CommentaryTransfer",
    "CommentaryCreateRequest",
    "CommentaryUpdateRequest",
    "CommentaryResponse",
    "SuccessStoryCreateRequest",
    "SuccessStorySearchRequest",
    "AudioNoteTransfer",
    "AudioNoteCreateRequest",
    "AudioNoteResponse",
]
