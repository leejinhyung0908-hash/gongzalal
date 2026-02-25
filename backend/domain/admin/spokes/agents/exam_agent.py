"""Exam 정책 기반 에이전트.

애매한 경우(정책 기반)에 사용되는 에이전트.
LLM을 사용하여 더 정교한 판단을 수행할 수 있음.

ADVICE 의도인 경우:
- Neon DB에서 합격 수기 검색 (RAG)
- 학습된 EXAONE 모델로 응답 생성
"""

import re
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field

try:
    from fastmcp import FastMCP
    _FASTMCP_AVAILABLE = True
except ImportError:
    _FASTMCP_AVAILABLE = False
    FastMCP = None

from backend.config import settings
from backend.dependencies import get_db_connection, get_llm
from backend.domain.admin.spokes.services.success_stories_rag import SuccessStoriesRAG
from backend.core.llm.providers.exaone_llm import ExaoneLLM

logger = logging.getLogger(__name__)


# 파싱 함수들 (exam_router와 중복이지만 순환 import 방지)
def _resolve_relative_year(text: str, now_year: int) -> Optional[int]:
    m = re.search(r"(?:(20)?(\d{2}))\s*년", text)
    if m:
        y2 = int(m.group(2))
        return 2000 + y2
    if "올해" in text:
        return now_year
    if "작년" in text:
        return now_year - 1
    if "재작년" in text or "그저께" in text:
        return now_year - 2
    return None


def _parse_exam_type(text: str) -> Optional[str]:
    if "국가직" in text:
        return "국가직"
    if "지방직" in text or "지방" in text:
        return "지방직"
    return None


def _parse_grade(text: str) -> str:
    m = re.search(r"(\d)\s*급", text)
    if m:
        return f"{m.group(1)}급"
    return "9급"


def _parse_question_no(text: str) -> Optional[int]:
    m = re.search(r"(\d{1,3})\s*번", text)
    if not m:
        return None
    return int(m.group(1))


def _parse_subject(text: str, conn) -> Optional[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT subject FROM exams ORDER BY subject")
        subjects = [str(r[0]) for r in cur.fetchall() if r and r[0]]
    for s in subjects:
        if s in text:
            return s
    return None


def _parse_job_series(text: str) -> Optional[str]:
    m = re.search(r"([가-힣]+행정직)", text)
    if m:
        return m.group(1)
    if "교육행정" in text:
        return "교육행정직"
    if "일반행정" in text:
        return "일반행정직"
    return None


class ExamAnswerRequest(BaseModel):
    question: str = Field(..., description="사용자 질문(예: 작년 회계학 3번 문제 정답 뭐야?)")


class ExamAnswerResponse(BaseModel):
    year: int
    exam_type: str
    job_series: str
    grade: str
    subject: str
    question_no: int
    answer_key: str


class ExamAgent:
    """Exam 정책 기반 에이전트."""

    def __init__(self, model_dir: Optional[Path] = None):
        """ExamAgent 초기화.

        Args:
            model_dir: EXAONE 모델 디렉토리 경로 (None이면 기본 경로 사용)
        """
        logger.info("[에이전트] ExamAgent 초기화")

        # EXAONE 모델 로드
        self.exaone_llm = self._load_exaone_model(model_dir)

        # FastMCP 클라이언트 생성 및 툴 설정
        if _FASTMCP_AVAILABLE:
            self.mcp = FastMCP(name="exam_agent_exaone")
            self._setup_exaone_tools()
        else:
            self.mcp = None
            logger.warning("[에이전트] FastMCP가 설치되지 않아 MCP 서버를 생성할 수 없습니다.")

        # RAG 서비스는 지연 로딩
        self._rag_service = None

        logger.info("[에이전트] ExamAgent 초기화 완료 (ExaOne, FastMCP)")

    def _get_default_model_dir(self) -> Path:
        """기본 EXAONE 모델 디렉토리 경로를 반환합니다.

        Returns:
            모델 디렉토리 Path
        """
        current_file = Path(__file__)
        # exam_agent.py 위치: backend/domain/admin/spokes/agents/exam_agent.py
        # 프로젝트 루트까지: 6단계 상위
        project_root = current_file.parent.parent.parent.parent.parent.parent
        model_dir = project_root / "artifacts" / "base-models" / "exaone"
        return model_dir

    def _load_exaone_model(self, model_dir: Optional[Path] = None):
        """EXAONE 모델을 로드합니다.

        중복 로드를 방지하기 위해 전역 싱글톤(get_llm → ModelLoader 캐시)을 사용합니다.
        서버 시작 시 main.py lifespan에서 이미 로드된 인스턴스를 재사용합니다.

        Args:
            model_dir: 모델 디렉토리 경로 (무시됨 — 싱글톤 사용)

        Returns:
            ExaoneLLM 인스턴스
        """
        try:
            from backend.dependencies import get_llm
            exaone_llm = get_llm()
            if not exaone_llm.is_loaded():
                exaone_llm.load()
            logger.info("[ExamAgent] EXAONE 모델 로드 완료 (싱글톤 공유)")
            return exaone_llm
        except Exception as e:
            logger.error(f"[ExamAgent] EXAONE 모델 로드 실패: {e}", exc_info=True)
            raise RuntimeError(f"EXAONE 모델 로드 실패: {e}") from e

    def _setup_exaone_tools(self) -> None:
        """EXAONE 모델을 위한 FastMCP 툴을 설정합니다."""
        if not _FASTMCP_AVAILABLE or self.mcp is None:
            return

        @self.mcp.tool()
        def exaone_generate_text(prompt: str, max_tokens: int = 512) -> Dict[str, Any]:
            """EXAONE 모델을 사용하여 텍스트를 생성합니다.

            Args:
                prompt: 생성할 텍스트의 프롬프트
                max_tokens: 최대 생성 토큰 수

            Returns:
                생성 결과 딕셔너리
            """
            try:
                if not self.exaone_llm.is_loaded():
                    self.exaone_llm.load()

                generated_text = self.exaone_llm.generate(
                    prompt=prompt,
                    max_new_tokens=max_tokens,
                    temperature=0.7,
                    top_p=0.9,
                )

                logger.info(f"[ExamAgent EXAONE 툴] 텍스트 생성 완료: {len(generated_text)}자")
                return {
                    "success": True,
                    "generated_text": generated_text,
                    "prompt": prompt,
                    "length": len(generated_text)
                }
            except Exception as e:
                logger.error(f"[ExamAgent EXAONE 툴] 텍스트 생성 실패: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.mcp.tool()
        def exaone_analyze_exam_question(question: str, context: Optional[str] = None) -> Dict[str, Any]:
            """EXAONE 모델을 사용하여 시험 문제를 분석합니다.

            Args:
                question: 분석할 시험 문제
                context: 추가 컨텍스트 (선택사항)

            Returns:
                분석 결과 딕셔너리
            """
            try:
                if not self.exaone_llm.is_loaded():
                    self.exaone_llm.load()

                # 프롬프트 구성
                if context:
                    prompt = f"""다음 공무원 시험 문제를 분석하고 전문적인 답변을 제공해주세요.

문제: {question}

추가 컨텍스트:
{context}

위 정보를 바탕으로 질문자에게 도움이 되는 상세한 분석을 제공해주세요."""
                else:
                    prompt = f"""다음 공무원 시험 문제를 분석하고 전문적인 답변을 제공해주세요.

문제: {question}

위 문제에 대해 상세한 분석과 답변을 제공해주세요."""

                analysis_text = self.exaone_llm.generate(
                    prompt=prompt,
                    max_new_tokens=512,
                    temperature=0.7,
                    top_p=0.9,
                )

                logger.info("[ExamAgent EXAONE 툴] 시험 문제 분석 완료")
                return {
                    "success": True,
                    "question": question,
                    "analysis": analysis_text,
                    "context_used": context is not None,
                }
            except Exception as e:
                logger.error(f"[ExamAgent EXAONE 툴] 시험 문제 분석 실패: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        self._setup_filesystem_tools()
        logger.info("[ExamAgent] EXAONE 툴 설정 완료")

    def _setup_filesystem_tools(self) -> None:
        """os와 pathlib 라이브러리를 사용한 파일 시스템 툴을 설정합니다."""
        if not _FASTMCP_AVAILABLE or self.mcp is None:
            return

        # 프로젝트 루트 경로 설정 (보안을 위해 제한)
        project_root = Path(__file__).parent.parent.parent.parent.parent.parent

        @self.mcp.tool()
        def path_exists(path: str) -> Dict[str, Any]:
            """경로가 존재하는지 확인합니다.

            Args:
                path: 확인할 경로 (상대 경로는 프로젝트 루트 기준)

            Returns:
                존재 여부 결과 딕셔너리
            """
            try:
                path_obj = Path(path)
                if not path_obj.is_absolute():
                    path_obj = project_root / path_obj

                # 보안: 프로젝트 루트 밖으로 나가는 것 방지
                try:
                    path_obj.resolve().relative_to(project_root.resolve())
                except ValueError:
                    return {
                        "success": False,
                        "error": "프로젝트 루트 밖의 경로는 접근할 수 없습니다"
                    }

                exists = path_obj.exists()
                is_file = path_obj.is_file() if exists else False
                is_dir = path_obj.is_dir() if exists else False

                return {
                    "success": True,
                    "path": str(path_obj),
                    "exists": exists,
                    "is_file": is_file,
                    "is_dir": is_dir
                }
            except Exception as e:
                logger.error(f"[ExamAgent 파일시스템 툴] 경로 확인 실패: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.mcp.tool()
        def list_directory(path: str = ".") -> Dict[str, Any]:
            """디렉토리 내용을 나열합니다.

            Args:
                path: 나열할 디렉토리 경로 (기본값: 현재 디렉토리)

            Returns:
                디렉토리 내용 딕셔너리
            """
            try:
                path_obj = Path(path)
                if not path_obj.is_absolute():
                    path_obj = project_root / path_obj

                # 보안: 프로젝트 루트 밖으로 나가는 것 방지
                try:
                    path_obj.resolve().relative_to(project_root.resolve())
                except ValueError:
                    return {
                        "success": False,
                        "error": "프로젝트 루트 밖의 경로는 접근할 수 없습니다"
                    }

                if not path_obj.exists():
                    return {
                        "success": False,
                        "error": "경로가 존재하지 않습니다"
                    }

                if not path_obj.is_dir():
                    return {
                        "success": False,
                        "error": "디렉토리가 아닙니다"
                    }

                items = []
                for item in path_obj.iterdir():
                    items.append({
                        "name": item.name,
                        "is_file": item.is_file(),
                        "is_dir": item.is_dir(),
                        "size": item.stat().st_size if item.is_file() else None
                    })

                return {
                    "success": True,
                    "path": str(path_obj),
                    "items": sorted(items, key=lambda x: (not x["is_dir"], x["name"])),
                    "count": len(items)
                }
            except Exception as e:
                logger.error(f"[ExamAgent 파일시스템 툴] 디렉토리 나열 실패: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.mcp.tool()
        def read_file(file_path: str, encoding: str = "utf-8") -> Dict[str, Any]:
            """파일 내용을 읽습니다.

            Args:
                file_path: 읽을 파일 경로
                encoding: 파일 인코딩 (기본값: utf-8)

            Returns:
                파일 내용 딕셔너리
            """
            try:
                path_obj = Path(file_path)
                if not path_obj.is_absolute():
                    path_obj = project_root / path_obj

                # 보안: 프로젝트 루트 밖으로 나가는 것 방지
                try:
                    path_obj.resolve().relative_to(project_root.resolve())
                except ValueError:
                    return {
                        "success": False,
                        "error": "프로젝트 루트 밖의 경로는 접근할 수 없습니다"
                    }

                if not path_obj.exists():
                    return {
                        "success": False,
                        "error": "파일이 존재하지 않습니다"
                    }

                if not path_obj.is_file():
                    return {
                        "success": False,
                        "error": "파일이 아닙니다"
                    }

                # 파일 크기 제한 (10MB)
                file_size = path_obj.stat().st_size
                if file_size > 10 * 1024 * 1024:
                    return {
                        "success": False,
                        "error": "파일이 너무 큽니다 (10MB 제한)"
                    }

                content = path_obj.read_text(encoding=encoding)

                return {
                    "success": True,
                    "path": str(path_obj),
                    "content": content,
                    "size": file_size,
                    "encoding": encoding
                }
            except Exception as e:
                logger.error(f"[ExamAgent 파일시스템 툴] 파일 읽기 실패: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.mcp.tool()
        def get_path_info(path: str) -> Dict[str, Any]:
            """경로의 상세 정보를 조회합니다.

            Args:
                path: 조회할 경로

            Returns:
                경로 정보 딕셔너리
            """
            try:
                path_obj = Path(path)
                if not path_obj.is_absolute():
                    path_obj = project_root / path_obj

                # 보안: 프로젝트 루트 밖으로 나가는 것 방지
                try:
                    path_obj.resolve().relative_to(project_root.resolve())
                except ValueError:
                    return {
                        "success": False,
                        "error": "프로젝트 루트 밖의 경로는 접근할 수 없습니다"
                    }

                if not path_obj.exists():
                    return {
                        "success": True,
                        "path": str(path_obj),
                        "exists": False,
                        "absolute_path": str(path_obj.resolve())
                    }

                stat_info = path_obj.stat()

                return {
                    "success": True,
                    "path": str(path_obj),
                    "absolute_path": str(path_obj.resolve()),
                    "exists": True,
                    "is_file": path_obj.is_file(),
                    "is_dir": path_obj.is_dir(),
                    "size": stat_info.st_size if path_obj.is_file() else None,
                    "created": stat_info.st_ctime,
                    "modified": stat_info.st_mtime,
                    "parent": str(path_obj.parent),
                    "name": path_obj.name,
                    "stem": path_obj.stem,
                    "suffix": path_obj.suffix
                }
            except Exception as e:
                logger.error(f"[ExamAgent 파일시스템 툴] 경로 정보 조회 실패: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.mcp.tool()
        def join_paths(*paths: str) -> Dict[str, Any]:
            """여러 경로를 결합합니다.

            Args:
                *paths: 결합할 경로들

            Returns:
                결합된 경로 딕셔너리
            """
            try:
                combined = Path(*paths)
                return {
                    "success": True,
                    "combined_path": str(combined),
                    "parts": list(combined.parts)
                }
            except Exception as e:
                logger.error(f"[ExamAgent 파일시스템 툴] 경로 결합 실패: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.mcp.tool()
        def get_environment_variable(name: str, default: Optional[str] = None) -> Dict[str, Any]:
            """환경 변수를 읽습니다.

            Args:
                name: 환경 변수 이름
                default: 기본값 (환경 변수가 없을 때)

            Returns:
                환경 변수 값 딕셔너리
            """
            try:
                value = os.getenv(name, default)
                return {
                    "success": True,
                    "name": name,
                    "value": value,
                    "exists": name in os.environ
                }
            except Exception as e:
                logger.error(f"[ExamAgent 파일시스템 툴] 환경 변수 읽기 실패: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.mcp.tool()
        def get_current_directory() -> Dict[str, Any]:
            """현재 작업 디렉토리를 반환합니다.

            Returns:
                현재 디렉토리 정보 딕셔너리
            """
            try:
                cwd = Path.cwd()
                return {
                    "success": True,
                    "current_directory": str(cwd),
                    "absolute_path": str(cwd.resolve())
                }
            except Exception as e:
                logger.error(f"[ExamAgent 파일시스템 툴] 현재 디렉토리 조회 실패: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        logger.info("[ExamAgent] 파일시스템 툴 설정 완료 (os, pathlib)")

    def _get_rag_service(self) -> SuccessStoriesRAG:
        """RAG 서비스 인스턴스 가져오기 (싱글톤)"""
        if self._rag_service is None:
            self._rag_service = SuccessStoriesRAG()
        return self._rag_service

    async def handle_request(
        self, request_text: str, request_data: dict, koelectra_result: dict
    ) -> dict:
        """정책 기반 요청 처리.

        Args:
            request_text: 요청 텍스트 (LLM 분석용)
            request_data: 요청 데이터 (question 등)
            koelectra_result: KoELECTRA 분석 결과

        Returns:
            처리 결과
        """
        # 의도 확인
        intent = koelectra_result.get("intent", {})
        intent_type = intent.get("intent", "DB_QUERY") if isinstance(intent, dict) else "DB_QUERY"

        # ADVICE 의도인 경우: RAG + EXAONE 사용
        if intent_type == "ADVICE":
            return await self._handle_advice_with_rag(request_text, request_data, koelectra_result)

        # 기존 로직: DB 조회 (DB_QUERY, EXPLAIN 등)
        return await self._handle_db_query(request_text, request_data, koelectra_result)

    async def _handle_advice_with_rag(
        self, request_text: str, request_data: dict, koelectra_result: dict
    ) -> dict:
        """학습 상담 요청 처리 (RAG + EXAONE).

        Args:
            request_text: 요청 텍스트
            request_data: 요청 데이터
            koelectra_result: KoELECTRA 분석 결과

        Returns:
            처리 결과
        """
        try:
            # 1. RAG: Neon DB에서 관련 합격 수기 검색
            rag_service = self._get_rag_service()
            stories = rag_service.search_similar_stories(
                query=request_text,
                top_k=3,
                min_similarity=0.5
            )

            if not stories:
                return {
                    "success": False,
                    "method": "policy_based_advice",
                    "intent": "ADVICE",
                    "error": "관련 합격 수기를 찾지 못했습니다.",
                }

            # 2. 컨텍스트 포맷팅
            context = rag_service.format_context_for_llm(stories)

            # 3. 자체 EXAONE 모델로 응답 생성
            if not self.exaone_llm.is_loaded():
                self.exaone_llm.load()

            # 프롬프트 구성 (학습 데이터 형식과 유사하게)
            prompt = f"""공무원 수험 멘토로서, 제공된 합격 수기를 바탕으로 질문자에게 공감하고 구체적인 학습 전략을 제시하세요. 답변은 항상 따뜻하고 전문적인 어조를 유지하세요.

질문: {request_text}

참고 자료 (합격 수기):
{context}

위 합격 수기들을 참고하여 질문자에게 도움이 되는 답변을 작성해주세요."""

            # 자체 EXAONE 모델로 응답 생성
            response = self.exaone_llm.generate(
                prompt=prompt,
                max_new_tokens=512,
                temperature=0.7,
                top_p=0.9,
            )

            return {
                "success": True,
                "method": "policy_based_advice",
                "intent": "ADVICE",
                "answer": {
                    "response": response,
                    "sources": [
                        {
                            "source": story.get("source"),
                            "similarity": story.get("similarity", 0),
                            "exam_info": story.get("exam_info", {})
                        }
                        for story in stories
                    ]
                },
                "rag_context": context,
            }

        except Exception as e:
            return {
                "success": False,
                "method": "policy_based_advice",
                "intent": "ADVICE",
                "error": f"응답 생성 중 오류가 발생했습니다: {str(e)}",
            }

    async def _handle_db_query(
        self, request_text: str, request_data: dict, koelectra_result: dict
    ) -> dict:
        """DB 조회 요청 처리 (기존 로직).

        Args:
            request_text: 요청 텍스트
            request_data: 요청 데이터
            koelectra_result: KoELECTRA 분석 결과

        Returns:
            처리 결과
        """
        # ExamAnswerRequest로 변환
        req = ExamAnswerRequest(**request_data)

        # 기존 exam_router의 로직 재사용
        conn = get_db_connection()
        now_year = datetime.now().year
        year = _resolve_relative_year(req.question, now_year) or now_year
        exam_type = _parse_exam_type(req.question) or "지방직"
        grade = _parse_grade(req.question)
        subject = _parse_subject(req.question, conn)
        qno = _parse_question_no(req.question)
        job_series = _parse_job_series(req.question)

        if subject is None:
            return {
                "success": False,
                "method": "policy_based",
                "error": "과목명을 인식하지 못했습니다. (예: 회계학/행정법총론)",
            }
        if qno is None:
            return {
                "success": False,
                "method": "policy_based",
                "error": "문항 번호를 인식하지 못했습니다. (예: 3번)",
            }

        # DB 조회 (exams + questions 조인)
        try:
            with conn.cursor() as cur:
                if job_series:
                    cur.execute(
                        """
                        SELECT e.year, e.exam_type, e.series, e.grade, e.subject, q.question_no, q.answer_key
                        FROM questions q
                        JOIN exams e ON q.exam_id = e.id
                        WHERE e.year=%s AND e.exam_type=%s AND e.series=%s AND e.grade=%s AND e.subject=%s AND q.question_no=%s
                        LIMIT 1
                        """,
                        (year, exam_type, job_series, grade, subject, qno),
                    )
                else:
                    cur.execute(
                        """
                        SELECT e.year, e.exam_type, e.series, e.grade, e.subject, q.question_no, q.answer_key
                        FROM questions q
                        JOIN exams e ON q.exam_id = e.id
                        WHERE e.year=%s AND e.exam_type=%s AND e.grade=%s AND e.subject=%s AND q.question_no=%s
                        LIMIT 1
                        """,
                        (year, exam_type, grade, subject, qno),
                    )

                row = cur.fetchone()

                if not row:
                    return {
                        "success": False,
                        "method": "policy_based",
                        "error": "해당 조건의 문항을 찾지 못했습니다. (연도, 시험구분, 직렬, 급수, 과목, 문항을 기입해서 알려주세요. 예: 25년 지방 일반행정 9급 한국사 17번)",
                    }

                answer = ExamAnswerResponse(
                    year=int(row[0]),
                    exam_type=str(row[1]),
                    job_series=str(row[2] or ""),
                    grade=str(row[3] or ""),
                    subject=str(row[4]),
                    question_no=int(row[5]),
                    answer_key=str(row[6]),
                )

                return {
                    "success": True,
                    "method": "policy_based",
                    "koelectra_result": koelectra_result,
                    "answer": answer.model_dump(),
                }
        except Exception as exc:
            return {
                "success": False,
                "method": "policy_based",
                "error": str(exc),
            }
