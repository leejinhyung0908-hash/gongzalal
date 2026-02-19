"""Admin API v1 package.

새 테이블 구조에 맞춘 라우터들:
- exam_router: Exams 테이블
- question_router: Questions 테이블
- user_router: Users 테이블
- commentary_router: Commentaries 테이블
- study_plan_router: Study_Plans 테이블
- solving_log_router: User_Solving_Logs 테이블
- audio_note_router: Audio_Notes 테이블
"""

# 기존 라우터
from . import chat_router  # noqa: F401
from . import mcp_router  # noqa: F401
from . import exam_router  # noqa: F401
from . import user_router  # noqa: F401
from . import commentary_router  # noqa: F401

# 새 라우터
from . import question_router  # noqa: F401
from . import study_plan_router  # noqa: F401
from . import solving_log_router  # noqa: F401
from . import audio_note_router  # noqa: F401
from . import mentoring_knowledge_router  # noqa: F401
from . import auth_router  # noqa: F401

__all__ = [
    "chat_router",
    "mcp_router",
    "exam_router",
    "user_router",
    "commentary_router",
    "question_router",
    "study_plan_router",
    "solving_log_router",
    "audio_note_router",
    "mentoring_knowledge_router",
    "auth_router",
]
