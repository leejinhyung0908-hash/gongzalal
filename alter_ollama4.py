"""MentoringKnowledge 테이블 생성 스크립트.

EXAONE 모델을 사용하여 합격 수기 기반 멘토링 Q&A 지식 저장용
SQLAlchemy ORM 모델을 설계/재생성합니다.

사용법:
    python alter_ollama4.py                  # 모델 생성
    python alter_ollama4.py --dry-run        # 파일 저장 없이 코드만 출력
    python alter_ollama4.py --show-prompt    # 프롬프트만 출력
"""

from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from pathlib import Path
import argparse
import re
import textwrap

model_path = "artifacts/base-models/exaone"

# ─────────────────────────────────────────────────────────────
# 대상 테이블 정보
# ─────────────────────────────────────────────────────────────
TABLE_INFO = {
    "class_name": "MentoringKnowledge",
    "table_name": "mentoring_knowledge",
    "vector_column": "knowledge_vector",
    "vector_comment": "멘토링 Q&A 임베딩 벡터 (RAG 검색용)",
    "source_file": "backend/domain/admin/models/bases/mentoring_knowledge.py",
}

# ─────────────────────────────────────────────────────────────
# Few-shot 예시: 프로젝트에서 실제 작동하는 Exam 모델
# EXAONE에게 "이런 스타일로 작성하라"는 참조로 제공
# ─────────────────────────────────────────────────────────────
FEW_SHOT_EXAMPLE = '''"""Exams 테이블 (SQLAlchemy 모델).

시험 메타데이터를 저장합니다.

관계:
- Questions: 1:N (exam_id FK로 연결, 시험별 여러 문제)
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

try:
    from pgvector.sqlalchemy import Vector  # type: ignore
except ImportError:
    Vector = None  # type: ignore

from sqlalchemy import DateTime, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.domain.shared.bases import Base

if TYPE_CHECKING:
    from backend.domain.admin.models.bases.question import Question


class Exam(Base):
    """시험 메타데이터 테이블."""

    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    exam_type: Mapped[str] = mapped_column(String(50), nullable=False)
    series: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    grade: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    subject: Mapped[str] = mapped_column(String(50), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    if Vector is not None:
        exam_vector: Mapped[Optional[List[float]]] = mapped_column(
            Vector(1536), nullable=True
        )
    else:
        exam_vector: Mapped[Optional[List[float]]] = mapped_column(nullable=True)  # type: ignore[assignment]

    questions: Mapped[List["Question"]] = relationship(
        back_populates="exam",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Exam(id={self.id}, year={self.year}, subject=\\'{self.subject}\\')>"
'''

# merged_training_data.jsonl 구조 샘플 (프롬프트에 포함)
JSONL_SAMPLE = """{
  "instruction": "공무원 수험 멘토로서, 제공된 합격 수기를 바탕으로 질문자에게 공감하고 구체적인 학습 전략을 제시하세요.",
  "input": {
    "question": "전업 수험생으로 공부하는데 하루 일과를 어떻게 구성해야 할까요?",
    "intent": "ADVICE",
    "context": "합격자 수기: 1년~1년 6개월 수험기간, 일일 학습 계획: 국가직 합격을 목표로..."
  },
  "output": {
    "thought_process": "1. 전업 수험생의 일일 계획 질문임을 인지. 2. 합격 수기 분석. 3. 구체적인 일일 루틴 제시.",
    "response": "전업 수험생이시군요! 시간이 많다고 해서 방심하면 안 됩니다..."
  }
}"""

# ─────────────────────────────────────────────────────────────
# 정답 코드 (EXAONE 생성 실패 시 폴백으로 사용)
# ─────────────────────────────────────────────────────────────
REFERENCE_CODE = '''\
"""MentoringKnowledge 테이블 (SQLAlchemy 모델).

합격 수기 기반 멘토링 Q&A 지식을 저장합니다.
LLM 학습용 instruction-tuning 데이터(질문, 의도, 맥락, 사고과정, 응답)를
구조적으로 보관하여 RAG 검색 및 학습 계획 생성에 활용합니다.

관계:
- 독립 참조 테이블 (FK 없음)
- 서비스 레벨에서 user_solving_logs(입력) → RAG 검색 → study_plans(출력)
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.domain.shared.bases import Base

try:
    from pgvector.sqlalchemy import Vector  # type: ignore
except ImportError:
    Vector = None  # type: ignore


class MentoringKnowledge(Base):
    """멘토링 지식 테이블 — 합격 수기 기반 Q&A 지식 저장소."""

    __tablename__ = "mentoring_knowledge"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # 시스템 프롬프트 (instruction)
    instruction: Mapped[str] = mapped_column(Text, nullable=False)

    # 사용자 질문
    question: Mapped[str] = mapped_column(Text, nullable=False)

    # 의도 분류 (예: 'ADVICE', 'STRATEGY')
    intent: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # 합격 수기 원문 (context)
    context: Mapped[str] = mapped_column(Text, nullable=False)

    # AI 사고 과정 (thought_process)
    thought_process: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # AI 응답 (response)
    response: Mapped[str] = mapped_column(Text, nullable=False)

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ─────────────────────────────────────────────────────────────
    # 벡터 임베딩 (RAG 검색용)
    # ─────────────────────────────────────────────────────────────
    if Vector is not None:
        knowledge_vector: Mapped[Optional[List[float]]] = mapped_column(
            Vector(1536), nullable=True
        )
    else:
        knowledge_vector: Mapped[Optional[List[float]]] = mapped_column(nullable=True)  # type: ignore[assignment]

    def __repr__(self) -> str:
        q_preview = self.question[:30] if self.question else ""
        return f"<MentoringKnowledge(id={self.id}, question='{q_preview}...')>"
'''


def load_exaone():
    """ExaOne 모델과 토크나이저를 로드합니다."""
    print("[ExaOne] 모델 로딩 중...")
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )
    print("[ExaOne] 모델 로드 완료 ✅")
    return tokenizer, model


def generate_code_with_exaone(
    tokenizer, model, prompt: str, max_new_tokens: int = 3000
) -> str:
    """ExaOne 모델을 사용하여 코드를 생성합니다."""
    messages = [
        {
            "role": "system",
            "content": (
                "You are EXAONE model from LG AI Research, a helpful assistant "
                "specialized in generating Python SQLAlchemy ORM code.\n\n"
                "ABSOLUTE RULES:\n"
                "1. Output ONLY pure Python code. No markdown, no code fences, no explanations.\n"
                "2. Use ONLY 'Mapped[type]' type hints and 'mapped_column()' function.\n"
                "3. NEVER use Column(), declarative_base(), create_engine, sessionmaker.\n"
                "4. Import Base from backend.domain.shared.bases, NOT from declarative_base().\n"
                "5. Output the COMPLETE file from start to end. NEVER use '...' to abbreviate.\n"
                "6. Do NOT add any Example usage code at the end."
            ),
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]

    input_ids = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt",
    ).to(model.device)

    outputs = model.generate(
        input_ids,
        max_new_tokens=max_new_tokens,
        do_sample=True,
        temperature=0.3,       # 낮은 온도: 더 결정론적 출력
        top_p=0.85,
        repetition_penalty=1.1,
        eos_token_id=tokenizer.eos_token_id,
        pad_token_id=tokenizer.pad_token_id,
    )

    input_length = input_ids.shape[-1]
    generated_tokens = outputs[0][input_length:]
    generated_text = tokenizer.decode(generated_tokens, skip_special_tokens=True)

    return extract_code_from_response(generated_text)


def extract_code_from_response(text: str) -> str:
    """EXAONE 응답에서 Python 코드를 추출합니다.

    여러 형태의 출력 포맷을 처리:
    - ```python ... ``` 코드 블록
    - ``` ... ``` 코드 블록
    - 순수 Python 코드 (코드 블록 없이)
    """
    # 1) ```python ... ``` 코드 블록
    match = re.search(r"```python\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # 2) ``` ... ``` 코드 블록
    match = re.search(r"```\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # 3) 코드 블록 없이 순수 Python 코드
    #    코드의 시작을 찾음: docstring 또는 import 문
    lines = text.strip().splitlines()
    code_start = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('"""') or stripped.startswith("from ") or stripped.startswith("import "):
            code_start = i
            break

    if code_start >= 0:
        code_lines = lines[code_start:]
        # 코드가 아닌 설명문이 뒤에 붙었으면 자르기
        code_end = len(code_lines)
        for i in range(len(code_lines) - 1, -1, -1):
            stripped = code_lines[i].strip()
            if stripped and not stripped.startswith("#"):
                # Python 코드 또는 빈 줄이 아닌 자연어 설명 감지
                if re.match(r"^[A-Z가-힣].*[.。]$", stripped):
                    code_end = i
                    continue
                break
        return "\n".join(code_lines[:code_end]).strip()

    return text.strip()


def build_prompt(source_code: str, prev_errors: list[str] | None = None) -> str:
    """MentoringKnowledge 모델 생성용 프롬프트를 빌드합니다.

    Args:
        source_code: 기존 모델 파일의 소스 코드
        prev_errors: 이전 시도에서 발생한 검증 에러 목록 (재시도 시)
    """
    # 에러 피드백 섹션 (재시도 시에만 포함)
    error_feedback = ""
    if prev_errors:
        error_list = "\n".join(f"  - {e}" for e in prev_errors)
        error_feedback = f"""
=== ⚠️ 이전 시도에서 발생한 에러 (이번에는 반드시 수정) ===
{error_list}

위 에러를 반드시 해결하세요. 특히:
- "declarative_base" 관련 에러 → from backend.domain.shared.bases import Base 사용
- "Column()" 관련 에러 → mapped_column() 사용
- "누락" 관련 에러 → 해당 요소를 반드시 포함
"""

    return f"""아래의 [참조 예시]와 동일한 스타일로 MentoringKnowledge 모델을 작성하세요.

=== [참조 예시] 프로젝트에서 실제 사용 중인 Exam 모델 ===
{FEW_SHOT_EXAMPLE}

=== [대상 데이터] merged_training_data.jsonl 구조 ===
{JSONL_SAMPLE}

=== [기존 코드] 이 코드를 기반으로 수정/완성 ===
{source_code}
{error_feedback}
=== [필수 규칙] ===

1. import 순서 (정확히 이 순서로):
   from __future__ import annotations
   from datetime import datetime
   from typing import List, Optional
   try:
       from pgvector.sqlalchemy import Vector  # type: ignore
   except ImportError:
       Vector = None  # type: ignore
   from sqlalchemy import DateTime, String, Text, func
   from sqlalchemy.orm import Mapped, mapped_column
   from backend.domain.shared.bases import Base

2. 클래스 정의:
   class MentoringKnowledge(Base):
       __tablename__ = "mentoring_knowledge"

3. 컬럼 정의 (모두 Mapped + mapped_column 형식):
   id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
   instruction: Mapped[str] = mapped_column(Text, nullable=False)
   question: Mapped[str] = mapped_column(Text, nullable=False)
   intent: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
   context: Mapped[str] = mapped_column(Text, nullable=False)
   thought_process: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
   response: Mapped[str] = mapped_column(Text, nullable=False)
   created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

4. 벡터 컬럼 (참조 예시의 exam_vector와 동일한 if/else 패턴):
   if Vector is not None:
       knowledge_vector: Mapped[Optional[List[float]]] = mapped_column(Vector(1536), nullable=True)
   else:
       knowledge_vector: Mapped[Optional[List[float]]] = mapped_column(nullable=True)

5. __repr__ 메서드 포함

=== [절대 금지] ===
- declarative_base() 사용 금지
- Column() 사용 금지 (mapped_column만 사용)
- create_engine, sessionmaker, Table, MetaData 금지
- Example usage 코드 금지
- '...' 축약 금지 — 파일 전체를 끝까지 완성

=== [출력] ===
[참조 예시]의 Exam 모델과 동일한 스타일로, 위 규칙을 적용한 완전한 Python 파일만 출력하세요.
코드 블록 없이 순수 Python 코드만 출력하세요."""


def post_process_code(code: str) -> str:
    """ExaOne 생성 코드의 공통 실수를 자동 수정합니다.

    EXAONE이 자주 하는 실수를 단계적으로 수정:
    1. declarative_base() → Base import로 교체
    2. Column() → mapped_column() 변환
    3. 불필요한 import 제거 (create_engine, sessionmaker 등)
    4. pgvector 패턴 교정
    5. 파일 끝 쓰레기 코드 제거
    6. 누락 import 추가
    """
    lines = code.splitlines()
    new_lines: list[str] = []

    # ── 상태 추적 ──
    has_pgvector_import = False
    has_base_import = False
    has_future_annotations = False
    has_mapped_import = False
    has_typing_import = False
    in_example_section = False  # 예제 코드 영역 진입 여부
    in_if_main = False          # if __name__ == "__main__" 블록 진입 여부

    for line in lines:
        stripped = line.strip()

        # ── 0. 예제 코드 / if __name__ 블록 이후는 모두 버림 ──
        if in_example_section or in_if_main:
            continue
        if stripped.startswith("# Example") or stripped.startswith("# Usage"):
            in_example_section = True
            continue
        if stripped.startswith("if __name__"):
            in_if_main = True
            continue

        # ── 1. 불필요한 import 제거 ──
        if "declarative_base" in line:
            continue
        if re.match(r"^\s*Base\s*=\s*declarative_base\s*\(", stripped):
            continue
        if "sessionmaker" in line and "import" in line:
            continue
        if "create_engine" in line and "import" in line:
            # create_engine만 import하는 경우
            if re.match(r"^\s*from\s+sqlalchemy\s+import\s+create_engine\s*$", stripped):
                continue
            # 다른 것과 함께 import하는 경우 → create_engine만 제거
            line = re.sub(r",\s*create_engine", "", line)
            line = re.sub(r"create_engine\s*,\s*", "", line)
        if re.match(r"^\s*from\s+sqlalchemy\s+import\s+Table\b", stripped):
            continue
        if "MetaData" in line and "import" in line:
            line = re.sub(r",\s*MetaData", "", line)
            line = re.sub(r"MetaData\s*,\s*", "", line)
        if "from sqlalchemy.dialects.postgresql import Array" in line:
            continue

        # ── 2. sqlalchemy.dialects.postgresql의 Vector 제거 ──
        if "sqlalchemy.dialects.postgresql" in line and "Vector" in line:
            if re.match(
                r"^\s*from\s+sqlalchemy\.dialects\.postgresql\s+import\s+Vector\s*$",
                stripped,
            ):
                continue
            line = re.sub(r",\s*Vector", "", line)
            line = re.sub(r"Vector\s*,\s*", "", line)

        # ── 3. sqlalchemy import에서 Column, List 제거 ──
        if "from sqlalchemy import" in line:
            # Column 제거
            if "Column" in line:
                line = re.sub(r",\s*Column\b", "", line)
                line = re.sub(r"\bColumn\s*,\s*", "", line)
            # List 제거 (typing에서 import해야 함)
            if "List" in line and "typing" not in line:
                line = re.sub(r",\s*List\b", "", line)
                line = re.sub(r"\bList\s*,\s*", "", line)
            # 나머지 불필요 항목 정리
            for unwanted in ["create_engine", "Table", "MetaData"]:
                if unwanted in line:
                    line = re.sub(rf",\s*{unwanted}\b", "", line)
                    line = re.sub(rf"\b{unwanted}\s*,\s*", "", line)
            # import 뒤에 아무것도 안 남으면 줄 삭제
            if re.match(r"^\s*from\s+sqlalchemy\s+import\s*$", line.rstrip()):
                continue

        # ── 4. Column() → mapped_column() 변환 ──
        # 예: name = Column(String(50), nullable=False)
        #   → name: Mapped[str] = mapped_column(String(50), nullable=False)
        col_match = re.match(
            r"^(\s+)(\w+)\s*=\s*Column\((.+)\)\s*$", line
        )
        if col_match:
            indent = col_match.group(1)
            col_name = col_match.group(2)
            col_args = col_match.group(3)
            # 타입 추론
            mapped_type = _infer_mapped_type(col_args)
            line = f"{indent}{col_name}: Mapped[{mapped_type}] = mapped_column({col_args})"

        # ── 5. 파일 끝 쓰레기 제거 ──
        if re.match(r"^#\s*(engine|Session|session)\s*=", stripped):
            continue
        if re.match(r"^#\s*Note:", stripped):
            continue
        if re.match(r"^(engine|Session|session)\s*=", stripped):
            continue

        # ── 6. 상태 추적 ──
        if "from pgvector.sqlalchemy import Vector" in line:
            has_pgvector_import = True
        if "from backend.domain.shared.bases import Base" in line:
            has_base_import = True
        if "from __future__ import annotations" in line:
            has_future_annotations = True
        if "from sqlalchemy.orm import" in line and "mapped_column" in line:
            has_mapped_import = True
        if "from typing import" in line:
            has_typing_import = True

        new_lines.append(line)

    # ── 7. 클래스 상속 교정: class MentoringKnowledge(Base) 확인 ──
    for i, line in enumerate(new_lines):
        # MentoringKnowledge(DeclarativeBase) 등 잘못된 상속 수정
        m = re.match(
            r"^(class\s+MentoringKnowledge)\((?!Base\b)(\w+)\)\s*:", line
        )
        if m:
            new_lines[i] = f"{m.group(1)}(Base):"

    # ── 8. 누락 import 추가 ──

    # from __future__ import annotations
    if not has_future_annotations:
        insert_idx = _find_first_import_line(new_lines)
        new_lines.insert(insert_idx, "from __future__ import annotations")
        new_lines.insert(insert_idx + 1, "")

    # from sqlalchemy.orm import Mapped, mapped_column
    if not has_mapped_import:
        for i, line in enumerate(new_lines):
            if "from sqlalchemy.orm import" in line:
                if "mapped_column" not in line:
                    parts = [p.strip() for p in line.split("import")[1].split(",")]
                    if "Mapped" not in parts:
                        parts.append("Mapped")
                    if "mapped_column" not in parts:
                        parts.append("mapped_column")
                    new_lines[i] = f"from sqlalchemy.orm import {', '.join(parts)}"
                has_mapped_import = True
                break
        if not has_mapped_import:
            idx = _find_insert_after(new_lines, "from sqlalchemy import")
            new_lines.insert(idx, "from sqlalchemy.orm import Mapped, mapped_column")

    # from backend.domain.shared.bases import Base
    if not has_base_import:
        idx = _find_insert_after(new_lines, "from sqlalchemy")
        new_lines.insert(idx, "")
        new_lines.insert(idx + 1, "from backend.domain.shared.bases import Base")

    # pgvector try-except
    if not has_pgvector_import:
        # Base import 또는 sqlalchemy import 이후에 추가
        target_marker = "from backend.domain.shared.bases import Base"
        if target_marker not in "\n".join(new_lines):
            target_marker = "from sqlalchemy"
        idx = _find_insert_after(new_lines, target_marker)
        pgvector_block = [
            "",
            "try:",
            "    from pgvector.sqlalchemy import Vector  # type: ignore",
            "except ImportError:",
            "    Vector = None  # type: ignore",
        ]
        for j, pg_line in enumerate(pgvector_block):
            new_lines.insert(idx + j, pg_line)

    # from typing import List, Optional
    result_text = "\n".join(new_lines)
    if "List[float]" in result_text and not has_typing_import:
        idx = _find_insert_after(new_lines, "from __future__")
        new_lines.insert(idx, "from typing import List, Optional")
    elif "List[float]" in result_text and has_typing_import:
        # List가 typing import에 없으면 추가
        for i, line in enumerate(new_lines):
            if "from typing import" in line and "List" not in line:
                if ")" in line:
                    new_lines[i] = line.replace(")", ", List)")
                else:
                    new_lines[i] = line.rstrip() + ", List"
                break

    # ── 9. 중복 빈 줄 정리 ──
    result = "\n".join(new_lines)
    result = re.sub(r"\n{3,}", "\n\n", result)

    # ── 10. 파일 끝 정리 ──
    result = result.rstrip() + "\n"

    return result


def _infer_mapped_type(col_args: str) -> str:
    """Column() 인자로부터 Mapped 타입을 추론합니다."""
    is_nullable = "nullable=True" in col_args
    col_args_lower = col_args.lower()

    if "text" in col_args_lower:
        base = "str"
    elif "string" in col_args_lower:
        base = "str"
    elif "integer" in col_args_lower or "smallinteger" in col_args_lower:
        base = "int"
    elif "boolean" in col_args_lower:
        base = "bool"
    elif "datetime" in col_args_lower:
        base = "datetime"
    elif "float" in col_args_lower:
        base = "float"
    else:
        base = "str"

    if is_nullable:
        return f"Optional[{base}]"
    return base


def _find_first_import_line(lines: list[str]) -> int:
    """첫 번째 import 문의 인덱스를 찾습니다. docstring 이후."""
    in_docstring = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if '"""' in stripped:
            count = stripped.count('"""')
            if count >= 2:
                # 한 줄 docstring
                continue
            in_docstring = not in_docstring
            continue
        if in_docstring:
            continue
        if stripped.startswith("from ") or stripped.startswith("import "):
            return i
    return 0


def _find_insert_after(lines: list[str], marker: str) -> int:
    """marker를 포함하는 마지막 줄의 다음 인덱스를 반환합니다."""
    last_idx = 0
    for i, line in enumerate(lines):
        if marker in line:
            last_idx = i + 1
    return last_idx


def validate_generated_code(code: str) -> list[str]:
    """생성된 코드를 검증하고 문제 목록을 반환합니다.

    Returns:
        문제 목록 (빈 리스트면 통과)
    """
    issues: list[str] = []

    if not code or len(code.strip()) < 200:
        issues.append("생성 코드가 너무 짧습니다 (최소 200자 필요).")
        return issues

    # ── 플레이스홀더 검사 ──
    for line_no, line in enumerate(code.splitlines(), 1):
        stripped = line.strip()
        # 주석이나 문자열 시작 줄은 건너뜀
        if stripped.startswith("#") or stripped.startswith('"') or stripped.startswith("'"):
            continue
        if stripped == "..." or stripped == "pass":
            continue
        if "..." in stripped:
            # 문자열 리터럴 내부의 ... 은 허용 (f-string 포함)
            no_strings = re.sub(
                r"""(f?"{3}[\s\S]*?"{3}|f?'{3}[\s\S]*?'{3}|f?"[^"]*"|f?'[^']*')""",
                "", stripped,
            )
            # 주석 부분 제외
            code_part = no_strings.split("#")[0]
            if "..." in code_part:
                issues.append(f"L{line_no}: 플레이스홀더 '...' 발견: {stripped}")

    if "TODO" in code or "tbd" in code.lower():
        issues.append("TODO나 TBD가 포함되어 있습니다.")

    # ── 필수 요소 검사 ──
    required = {
        "from __future__ import annotations": "from __future__ import annotations",
        "class MentoringKnowledge": "class MentoringKnowledge 선언",
        '__tablename__ = "mentoring_knowledge"': "__tablename__ 정의",
        "knowledge_vector": "knowledge_vector 컬럼",
        "from pgvector.sqlalchemy import Vector": "pgvector import",
        "mapped_column": "mapped_column 사용",
        "Mapped[": "Mapped 타입 힌트",
        "from backend.domain.shared.bases import Base": "Base import",
        "def __repr__": "__repr__ 메서드",
        "instruction": "instruction 컬럼",
        "question": "question 컬럼",
        "context": "context 컬럼",
        "response": "response 컬럼",
    }

    for pattern, desc in required.items():
        if pattern not in code:
            issues.append(f"누락: {desc} ({pattern})")

    # ── 금지 패턴 검사 ──
    forbidden = {
        "declarative_base": "declarative_base() 사용 (금지)",
        "create_engine": "create_engine import (불필요)",
        "sessionmaker": "sessionmaker import (불필요)",
    }

    for pattern, desc in forbidden.items():
        if pattern in code:
            issues.append(f"금지 패턴: {desc}")

    # Column() 사용 검사
    if re.search(r"=\s*Column\(", code):
        issues.append("구식 Column() 사용 (mapped_column()으로 교체 필요)")

    # (Base) 상속 확인
    if re.search(r"class\s+MentoringKnowledge\s*\(", code):
        if not re.search(r"class\s+MentoringKnowledge\s*\(\s*Base\s*\)", code):
            issues.append("MentoringKnowledge가 Base를 상속하지 않습니다.")

    return issues


def process_with_fallback(tokenizer, model, source_code: str, dry_run: bool) -> str:
    """EXAONE 생성 → 후처리 → 검증, 실패 시 최대 3회 재시도 후 참조 코드 사용.

    Returns:
        최종 코드 문자열
    """
    max_retries = 3
    prev_errors: list[str] | None = None

    for attempt in range(1, max_retries + 1):
        print(f"\n🧠 ExaOne 코드 생성 중... (시도 {attempt}/{max_retries})")

        prompt = build_prompt(source_code, prev_errors=prev_errors)
        generated_code = generate_code_with_exaone(tokenizer, model, prompt)

        print(f"  📝 원본 생성 코드 길이: {len(generated_code)}자")

        # 후처리
        generated_code = post_process_code(generated_code)
        print("  🔧 후처리 완료")

        # 출력
        print(f"\n{'='*60}")
        print(f"  === 생성된 코드 (시도 {attempt}) ===")
        print(f"{'='*60}")
        print(generated_code)
        print(f"{'='*60}\n")

        # 검증
        issues = validate_generated_code(generated_code)

        if not issues:
            print("✅ 코드 검증 통과!")
            return generated_code

        print(f"⚠️  검증 이슈 {len(issues)}건:")
        for issue in issues:
            print(f"   - {issue}")

        # 다음 시도에 에러 피드백 전달
        prev_errors = issues

        if attempt < max_retries:
            print(f"🔄 에러 피드백을 포함하여 재시도합니다...")

    # 모든 시도 실패 → 참조 코드 사용
    print(f"\n{'='*60}")
    print(f"⚠️  {max_retries}회 시도 모두 검증 실패.")
    print("📋 참조 코드(REFERENCE_CODE)를 사용합니다.")
    print(f"{'='*60}")

    fallback = REFERENCE_CODE
    print(fallback)
    print(f"{'='*60}\n")
    print("✅ 참조 코드 검증 생략 (사전 검증 완료)")

    return fallback


def main():
    """메인 함수."""
    parser = argparse.ArgumentParser(
        description="ExaOne 모델로 MentoringKnowledge 테이블을 설계합니다."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="파일 저장 없이 생성된 코드만 출력",
    )
    parser.add_argument(
        "--show-prompt",
        action="store_true",
        help="프롬프트만 출력 (모델 로드 없이)",
    )
    args = parser.parse_args()

    source_file = Path(TABLE_INFO["source_file"])

    # 기존 소스 코드 읽기
    if source_file.exists():
        source_code = source_file.read_text(encoding="utf-8")
        print(f"📂 기존 파일 발견: {source_file} ({len(source_code)}자)")
    else:
        source_code = "# 기존 파일 없음 — 새로 생성"
        print(f"📂 기존 파일 없음: {source_file} (새로 생성)")

    # 프롬프트만 출력 모드
    if args.show_prompt:
        prompt = build_prompt(source_code)
        print("\n" + "=" * 60)
        print(" 📝 EXAONE 프롬프트")
        print("=" * 60)
        print(prompt)
        print("=" * 60)
        return

    print("=" * 60)
    print(" 🚀 EXAONE MentoringKnowledge 테이블 설계기")
    print("=" * 60)
    print(f" 대상: {TABLE_INFO['class_name']} ({TABLE_INFO['table_name']})")
    print(f" 벡터 컬럼: {TABLE_INFO['vector_column']} (1536차원)")
    print(f" 출력 파일: {TABLE_INFO['source_file']}")
    print(f" 전략: 최대 3회 생성 시도 (에러 피드백 포함) → 실패 시 참조 코드")
    print(f" 생성 파라미터: temperature=0.3, top_p=0.85, max_tokens=3000")
    if args.dry_run:
        print(" 모드: DRY RUN (파일 저장 안 함)")
    print("=" * 60)

    # ExaOne 모델 로드
    tokenizer, exaone_model = load_exaone()

    # 생성 + 검증 + 폴백
    final_code = process_with_fallback(
        tokenizer, exaone_model, source_code, dry_run=args.dry_run
    )

    # 파일 저장
    if not args.dry_run:
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_text(final_code, encoding="utf-8")
        print(f"💾 저장 완료: {source_file}")
        print()
        print("✅ 다음 단계:")
        print("  1. 생성된 코드 확인")
        print("  2. alembic revision --autogenerate -m 'update_mentoring_knowledge'")
        print("  3. alembic upgrade head")
    else:
        print(f"🔍 [DRY RUN] 저장하지 않음: {source_file}")


if __name__ == "__main__":
    main()
