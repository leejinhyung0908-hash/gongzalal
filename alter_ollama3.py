"""ORM 클래스 생성 스크립트 (통합 벡터 컬럼 전용).

EXAONE 모델을 사용하여 기존 SQLAlchemy 모델 파일을 읽고,
pgvector Vector(1536) 컬럼이 통합된 ORM 클래스를 재생성합니다.

사용법:
    python alter_ollama3.py                     # 전체 테이블 처리
    python alter_ollama3.py --table questions    # 특정 테이블만 처리
    python alter_ollama3.py --list               # 대상 테이블 목록 확인
"""

from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from pathlib import Path
import argparse

model_path = "artifacts/base-models/exaone"

# ─────────────────────────────────────────────────────────────
# 테이블 → 벡터 컬럼 매핑
# ─────────────────────────────────────────────────────────────
TABLE_VECTOR_MAP = [
    {
        "class_name": "Exam",
        "table_name": "exams",
        "vector_column": "exam_vector",
        "vector_comment": "시험 콘텐츠 임베딩 벡터",
        "source_file": "backend/domain/admin/models/bases/exam.py",
    },
    {
        "class_name": "Question",
        "table_name": "questions",
        "vector_column": "question_vector",
        "vector_comment": "문제 텍스트 임베딩 벡터",
        "source_file": "backend/domain/admin/models/bases/question.py",
    },
    {
        "class_name": "QuestionImage",
        "table_name": "question_images",
        "vector_column": "image_vector",
        "vector_comment": "이미지 임베딩 벡터",
        "source_file": "backend/domain/admin/models/bases/question_image.py",
    },
    {
        "class_name": "Commentary",
        "table_name": "commentaries",
        "vector_column": "commentary_vector",
        "vector_comment": "해설 텍스트 임베딩 벡터",
        "source_file": "backend/domain/admin/models/bases/commentary.py",
    },
    {
        "class_name": "User",
        "table_name": "users",
        "vector_column": "user_vector",
        "vector_comment": "사용자 프로필 임베딩 벡터",
        "source_file": "backend/domain/admin/models/bases/user.py",
    },
    {
        "class_name": "UserSolvingLog",
        "table_name": "user_solving_logs",
        "vector_column": "solving_vector",
        "vector_comment": "풀이 패턴 임베딩 벡터",
        "source_file": "backend/domain/admin/models/bases/user_solving_log.py",
    },
    {
        "class_name": "AudioNote",
        "table_name": "audio_notes",
        "vector_column": "audio_vector",
        "vector_comment": "오디오 콘텐츠 임베딩 벡터",
        "source_file": "backend/domain/admin/models/bases/audio_note.py",
    },
    {
        "class_name": "StudyPlan",
        "table_name": "study_plans",
        "vector_column": "plan_vector",
        "vector_comment": "학습 계획 임베딩 벡터",
        "source_file": "backend/domain/admin/models/bases/study_plan.py",
    },
]


def load_exaone():
    """ExaOne 모델과 토크나이저를 로드합니다.

    Returns:
        (tokenizer, model) 튜플
    """
    print("[ExaOne] 모델 로딩 중...")
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True
    )
    print("[ExaOne] 모델 로드 완료 ✅")
    return tokenizer, model


def generate_code_with_exaone(
    tokenizer, model, prompt: str, max_new_tokens: int = 2000
) -> str:
    """ExaOne 모델을 사용하여 코드를 생성합니다.

    Args:
        tokenizer: 토크나이저
        model: ExaOne 모델
        prompt: 코드 생성 프롬프트
        max_new_tokens: 최대 생성 토큰 수

    Returns:
        생성된 코드 문자열
    """
    messages = [
        {
            "role": "system",
            "content": (
                "You are EXAONE model from LG AI Research, a helpful assistant "
                "specialized in generating Python SQLAlchemy ORM code. "
                "Output ONLY pure Python code without any markdown formatting, "
                "code fences, or explanations."
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
        temperature=0.7,
        top_p=0.9,
        eos_token_id=tokenizer.eos_token_id,
        pad_token_id=tokenizer.pad_token_id,
    )

    # 프롬프트 부분 제외하고 생성된 토큰만 디코딩
    input_length = input_ids.shape[-1]
    generated_tokens = outputs[0][input_length:]
    generated_text = tokenizer.decode(generated_tokens, skip_special_tokens=True)

    # 코드 블록 추출
    if "```python" in generated_text:
        code_start = generated_text.find("```python") + 9
        code_end = generated_text.find("```", code_start)
        if code_end != -1:
            return generated_text[code_start:code_end].strip()
        return generated_text[code_start:].strip()
    elif "```" in generated_text:
        code_start = generated_text.find("```") + 3
        code_end = generated_text.find("```", code_start)
        if code_end != -1:
            return generated_text[code_start:code_end].strip()
        return generated_text[code_start:].strip()

    return generated_text.strip()


def build_prompt(table_info: dict, source_code: str) -> str:
    """테이블 정보와 소스 코드를 기반으로 프롬프트를 생성합니다.

    Args:
        table_info: TABLE_VECTOR_MAP의 개별 항목
        source_code: 기존 모델 파일의 소스 코드

    Returns:
        ExaOne에 전달할 프롬프트 문자열
    """
    return f"""다음 기존 SQLAlchemy ORM 모델 코드를 수정하여, pgvector의 Vector 컬럼이 통합된 완전한 파일을 출력하세요.

=== 기존 모델 코드 ===
{source_code}

=== 수정 요구사항 ===
1. 벡터 컬럼 추가:
   - 컬럼명: {table_info['vector_column']}
   - 타입: Vector(1536), nullable=True
   - 설명: {table_info['vector_comment']}

2. pgvector import 추가 (try-except 패턴):
   try:
       from pgvector.sqlalchemy import Vector  # type: ignore
   except ImportError:
       Vector = None  # type: ignore

3. 벡터 컬럼 정의 패턴 (if Vector is not None 분기):
   if Vector is not None:
       {table_info['vector_column']}: Mapped[Optional[List[float]]] = mapped_column(
           Vector(1536), nullable=True
       )
   else:
       {table_info['vector_column']}: Mapped[Optional[List[float]]] = mapped_column(nullable=True)  # type: ignore[assignment]

4. typing에 List가 import되어 있는지 확인하고, 없으면 추가

=== 절대 변경하지 말 것 ===
- 기존 컬럼, 관계(relationship), __tablename__, docstring 구조
- 기존 import 문 구조 (추가만 허용, 삭제/변경 금지)
- Enum import, TYPE_CHECKING 블록
- relationship의 back_populates 값
- cascade 설정
- __repr__ 메서드

=== 벡터 컬럼 위치 ===
- 타임스탬프(created_at, updated_at) 바로 위에 배치
- "# 벡터 임베딩" 주석 섹션을 만들어서 구분

=== 출력 형식 ===
기존 코드를 그대로 복사한 후 위의 수정사항만 적용한 완전한 Python 파일을 출력하세요.
코드 블록(```python ... ```) 없이 순수 Python 코드만 출력하세요.
중요: '...' 같은 축약/플레이스홀더를 절대 포함하지 마세요. 파일 전체를 끝까지 완성해서 출력하세요."""


def post_process_code(code: str) -> str:
    """ExaOne 생성 코드의 공통 실수를 자동 수정합니다.

    주요 수정 사항:
    - sqlalchemy.dialects.postgresql에서 Vector를 잘못 import하는 패턴 제거
    - sqlalchemy에서 List, Column 등을 잘못 import하는 패턴 제거
    - pgvector try-except 블록이 없으면 추가

    Args:
        code: ExaOne이 생성한 코드 문자열

    Returns:
        수정된 코드 문자열
    """
    import re

    lines = code.splitlines()
    new_lines = []
    has_pgvector_import = False

    for line in lines:
        # 1) sqlalchemy.dialects.postgresql import에서 Vector 제거
        #    예: from sqlalchemy.dialects.postgresql import JSONB, Vector
        if "sqlalchemy.dialects.postgresql" in line and "Vector" in line:
            # Vector만 import하는 경우 → 줄 전체 제거
            if re.match(r"^\s*from sqlalchemy\.dialects\.postgresql import\s+Vector\s*$", line):
                continue
            # 다른 것과 함께 import하는 경우 → Vector만 제거
            line = re.sub(r",\s*Vector", "", line)
            line = re.sub(r"Vector,\s*", "", line)

        # 2) sqlalchemy에서 List, Column 등 잘못 import하는 패턴 수정
        #    예: from sqlalchemy import DateTime, ForeignKey, SmallInteger, String, List, Column, func
        if "from sqlalchemy import" in line or "from sqlalchemy " in line:
            if ", List" in line and "typing" not in line:
                line = re.sub(r",\s*List", "", line)
            if ", Column" in line and "mapped_column" in code:
                line = re.sub(r",\s*Column", "", line)

        # 3) pgvector import 존재 여부 확인
        if "from pgvector.sqlalchemy import Vector" in line:
            has_pgvector_import = True

        new_lines.append(line)

    # 4) pgvector import가 없으면 추가 (Base import 바로 위에)
    if not has_pgvector_import:
        final_lines = []
        inserted = False
        for line in new_lines:
            # "from backend.domain.shared.bases import Base" 바로 위에 삽입
            if not inserted and "from backend.domain.shared.bases import Base" in line:
                final_lines.append("")
                final_lines.append("# pgvector 지원")
                final_lines.append("try:")
                final_lines.append("    from pgvector.sqlalchemy import Vector  # type: ignore")
                final_lines.append("except ImportError:")
                final_lines.append("    Vector = None  # type: ignore")
                final_lines.append("")
                inserted = True
            final_lines.append(line)
        new_lines = final_lines

    result = "\n".join(new_lines)

    # 5) Vector 컬럼이 있는데 List가 typing import에 없으면 추가
    if "List[float]" in result:
        # typing import 라인 찾기
        typing_match = re.search(r"(from typing import .+)", result)
        if typing_match:
            typing_line = typing_match.group(1)
            if "List" not in typing_line:
                new_typing_line = typing_line.rstrip().rstrip(")")
                # 괄호가 있는 경우와 없는 경우 처리
                if ")" in typing_line:
                    new_typing_line = typing_line.replace(")", ", List)")
                else:
                    new_typing_line = typing_line + ", List"
                result = result.replace(typing_line, new_typing_line)

    # 6) 중복 빈 줄 정리 (3줄 이상 연속 빈 줄 → 2줄로)
    result = re.sub(r"\n{3,}", "\n\n", result)

    return result


def validate_generated_code(code: str, table_info: dict) -> None:
    """생성된 코드가 완전한지 검증합니다.

    Args:
        code: 생성된 코드 문자열
        table_info: 테이블 정보

    Raises:
        ValueError: 코드가 불완전하거나 필수 요소가 누락된 경우
    """
    if not code or len(code.strip()) < 200:
        raise ValueError("생성 코드가 너무 짧습니다 (최소 200자 필요).")

    # '...'이 코드 라인(주석/문자열 아닌 곳)에 있는지 확인
    for line in code.splitlines():
        stripped = line.strip()
        # 주석이나 문자열 내부의 ...은 무시
        if stripped.startswith("#") or stripped.startswith('"') or stripped.startswith("'"):
            continue
        # 순수 코드 라인에 단독 ... 이 있으면 플레이스홀더
        if stripped == "..." or stripped == "pass":
            continue
        if "..." in stripped and not stripped.startswith("#"):
            # 문자열 리터럴 내부인지 추가 확인
            comment_pos = stripped.find("#")
            if comment_pos != -1:
                code_part = stripped[:comment_pos]
                comment_part = stripped[comment_pos:]
                if "..." in comment_part and "..." not in code_part:
                    continue  # 주석 안에만 있으면 통과
            # 인라인 주석이 아닌 순수 코드에 ... 이 있으면 실패
            if "..." in stripped.split("#")[0]:
                raise ValueError(f"생성 코드에 '...' 플레이스홀더가 포함되어 있습니다: {stripped}")

    if "TODO" in code or "tbd" in code.lower():
        raise ValueError("생성 코드에 TODO나 TBD가 포함되어 있습니다.")

    required_elements = [
        "from __future__ import annotations",
        f"class {table_info['class_name']}",
        f'__tablename__ = "{table_info["table_name"]}"',
        table_info["vector_column"],
        "Vector",
        "from pgvector.sqlalchemy import Vector",
        "def __repr__",
    ]

    missing = [elem for elem in required_elements if elem not in code]
    if missing:
        raise ValueError(f"필수 요소가 누락되었습니다: {missing}")

    # 잘못된 import 패턴 검출
    if "sqlalchemy.dialects.postgresql import" in code and "Vector" in code.split("sqlalchemy.dialects.postgresql")[1].split("\n")[0]:
        raise ValueError("Vector가 sqlalchemy.dialects.postgresql에서 import되고 있습니다. pgvector.sqlalchemy에서 import해야 합니다.")


def process_table(tokenizer, model, table_info: dict, dry_run: bool = False) -> bool:
    """단일 테이블에 대해 벡터 통합 코드를 생성합니다.

    Args:
        tokenizer: ExaOne 토크나이저
        model: ExaOne 모델
        table_info: TABLE_VECTOR_MAP의 개별 항목
        dry_run: True면 파일 저장 없이 코드만 출력

    Returns:
        성공 여부
    """
    source_file = Path(table_info["source_file"])

    if not source_file.exists():
        print(f"  ❌ 소스 파일을 찾을 수 없습니다: {source_file}")
        return False

    source_code = source_file.read_text(encoding="utf-8")

    # 이미 벡터 컬럼이 있는지 확인
    if table_info["vector_column"] in source_code and "Vector" in source_code:
        print(f"  ⏭️  이미 {table_info['vector_column']} 컬럼이 존재합니다. 건너뜁니다.")
        return True

    print(f"  🔄 프롬프트 생성 중...")
    prompt = build_prompt(table_info, source_code)

    print(f"  🧠 ExaOne 코드 생성 중...")
    generated_code = generate_code_with_exaone(tokenizer, model, prompt)

    # 후처리: ExaOne의 공통 실수 자동 수정
    generated_code = post_process_code(generated_code)
    print(f"  🔧 후처리 완료 (잘못된 import 자동 수정)")

    print(f"\n{'='*60}")
    print(f"  === 생성된 코드 ({table_info['class_name']}) ===")
    print(f"{'='*60}")
    print(generated_code)
    print(f"{'='*60}\n")

    # 검증
    try:
        validate_generated_code(generated_code, table_info)
        print(f"  ✅ 코드 검증 통과")
    except ValueError as e:
        print(f"  ❌ 코드 검증 실패: {e}")
        print(f"  💡 다시 실행하거나 수동으로 수정하세요.")
        return False

    # 파일 저장
    if not dry_run:
        source_file.write_text(generated_code, encoding="utf-8")
        print(f"  💾 저장 완료: {source_file}")
    else:
        print(f"  🔍 [DRY RUN] 저장하지 않음: {source_file}")

    return True


def main():
    """메인 함수."""
    parser = argparse.ArgumentParser(
        description="ExaOne 모델로 모든 테이블에 Vector(1536) 컬럼을 통합 생성합니다."
    )
    parser.add_argument(
        "--table",
        type=str,
        default=None,
        help="특정 테이블만 처리 (예: questions, exams, users)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="대상 테이블 목록 출력",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="파일 저장 없이 생성된 코드만 출력",
    )

    args = parser.parse_args()

    # 테이블 목록 출력
    if args.list:
        print("\n📋 대상 테이블 목록:")
        print(f"{'테이블':<25} {'벡터 컬럼명':<20} {'소스 파일'}")
        print("-" * 80)
        for t in TABLE_VECTOR_MAP:
            print(f"{t['table_name']:<25} {t['vector_column']:<20} {t['source_file']}")
        print()
        return

    # 대상 필터링
    if args.table:
        targets = [
            t for t in TABLE_VECTOR_MAP
            if t["table_name"] == args.table or t["class_name"].lower() == args.table.lower()
        ]
        if not targets:
            print(f"❌ 테이블을 찾을 수 없습니다: {args.table}")
            print("   --list 옵션으로 대상 목록을 확인하세요.")
            return
    else:
        targets = TABLE_VECTOR_MAP

    print("=" * 60)
    print(" 🚀 EXAONE 통합 벡터 컬럼 생성기")
    print("=" * 60)
    print(f" 대상: {len(targets)}개 테이블")
    print(f" 벡터 차원: 1536 (pgvector)")
    if args.dry_run:
        print(" 모드: DRY RUN (파일 저장 안 함)")
    print("=" * 60)

    # ExaOne 모델 로드 (1회)
    tokenizer, exaone_model = load_exaone()

    # 각 테이블 처리
    success_count = 0
    fail_count = 0

    for i, table_info in enumerate(targets, 1):
        print(f"\n[{i}/{len(targets)}] 📦 {table_info['class_name']} ({table_info['table_name']})")
        print(f"  벡터 컬럼: {table_info['vector_column']}")

        ok = process_table(tokenizer, exaone_model, table_info, dry_run=args.dry_run)
        if ok:
            success_count += 1
        else:
            fail_count += 1

    # 결과 요약
    print("\n" + "=" * 60)
    print(f" 📊 결과: 성공 {success_count}개 / 실패 {fail_count}개")
    print("=" * 60)

    if success_count > 0 and not args.dry_run:
        print("\n✅ 다음 단계:")
        print("  1. 생성된 코드 확인")
        print("  2. alembic revision --autogenerate -m 'add_vector_columns'")
        print("  3. alembic upgrade head")


if __name__ == "__main__":
    main()

