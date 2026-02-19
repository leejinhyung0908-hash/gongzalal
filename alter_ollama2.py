"""ORM 클래스 생성 스크립트 (CommentaryEmbedding 전용).

EXAONE 모델을 사용하여 SQLAlchemy 모델을 참조하여
Commentary 임베딩 테이블 ORM 클래스를 생성합니다.
"""

from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from pathlib import Path
import argparse

model_path = "artifacts/base-models/exaone"


def generate_code_with_exaone(prompt: str, max_new_tokens: int = 1200) -> str:
    """ExaOne 모델을 사용하여 코드를 생성합니다.

    Args:
        prompt: 코드 생성 프롬프트
        max_new_tokens: 최대 생성 토큰 수

    Returns:
        생성된 코드 문자열
    """
    # 모델 로드
    print("[ExaOne] 모델 로딩 중...")
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True
    )

    print("[ExaOne] 코드 생성 중...")
    # ExaOne 모델의 chat template 사용 (권장 방식)
    messages = [
        {
            "role": "system",
            "content": "You are EXAONE model from LG AI Research, a helpful assistant specialized in generating Python SQLAlchemy ORM code."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]

    input_ids = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt"
    ).to(model.device)

    outputs = model.generate(
        input_ids,
        max_new_tokens=max_new_tokens,
        do_sample=True,
        temperature=0.7,
        top_p=0.9,
        eos_token_id=tokenizer.eos_token_id,
        pad_token_id=tokenizer.pad_token_id
    )

    # 생성된 코드 추출 (프롬프트 부분 제거)
    # input_ids 길이 이후의 생성된 토큰만 디코딩
    input_length = input_ids.shape[-1]
    generated_tokens = outputs[0][input_length:]
    generated_text = tokenizer.decode(generated_tokens, skip_special_tokens=True)

    # 응답에서 사용자 프롬프트 부분 제거 (chat template 사용 시)
    if "assistant" in generated_text.lower() or "답변" in generated_text:
        # chat template 응답에서 실제 코드 부분만 추출
        if "```python" in generated_text:
            code_start = generated_text.find("```python") + 9
            code_end = generated_text.find("```", code_start)
            if code_end != -1:
                generated_code = generated_text[code_start:code_end].strip()
            else:
                generated_code = generated_text[code_start:].strip()
        elif "```" in generated_text:
            code_start = generated_text.find("```") + 3
            code_end = generated_text.find("```", code_start)
            if code_end != -1:
                generated_code = generated_text[code_start:code_end].strip()
            else:
                generated_code = generated_text[code_start:].strip()
        else:
            # assistant 응답 부분만 추출
            if "assistant" in generated_text.lower():
                parts = generated_text.split("assistant", 1)
                if len(parts) > 1:
                    generated_code = parts[-1].strip()
                else:
                    generated_code = generated_text
            else:
                generated_code = generated_text
    else:
        generated_code = generated_text

    return generated_code


def _validate_commentary_embeddings_code(code: str) -> None:
    """CommentaryEmbedding 코드가 완전한지 검증합니다.

    Args:
        code: 생성된 코드 문자열

    Raises:
        ValueError: 코드가 불완전하거나 필수 요소가 누락된 경우
    """
    if not code or len(code.strip()) < 200:
        raise ValueError("생성 코드가 너무 짧습니다 (최소 200자 필요).")

    # 플레이스홀더나 축약 표시 확인
    if "..." in code:
        raise ValueError("생성 코드에 '...' 플레이스홀더가 포함되어 있습니다.")

    if "TODO" in code or "tbd" in code.lower():
        raise ValueError("생성 코드에 TODO나 TBD가 포함되어 있습니다.")

    # 필수 요소 확인
    required_elements = [
        "from __future__ import annotations",
        "from typing import Optional, List",
        "from sqlalchemy import BigInteger, ForeignKey, UniqueConstraint",
        "from sqlalchemy.orm import Mapped, mapped_column, relationship",
        "from backend.domain.shared.bases import Base, TimestampMixin",
        "from pgvector.sqlalchemy import Vector",
        "class CommentaryEmbedding",
        '__tablename__ = "commentary_embeddings"',
        'ForeignKey("commentaries.id"',
        'UniqueConstraint("commentary_id"',
        'back_populates="embedding_record"',
        "commentary_id",
        "embedding",
    ]

    missing = [elem for elem in required_elements if elem not in code]
    if missing:
        raise ValueError(f"필수 요소가 누락되었습니다: {missing}")


def generate_commentary_embedding():
    """CommentaryEmbedding ORM 클래스를 생성합니다."""
    output_file = "backend/domain/admin/models/bases/commentary_embeddings.py"

    # commentaries.py 파일 읽기
    commentaries_file = Path("backend/domain/admin/models/bases/commentaries.py")
    commentaries_content = commentaries_file.read_text(encoding="utf-8")

    # exam_question_embeddings.py 참고용으로 읽기 (템플릿으로 사용)
    exam_question_embeddings_file = Path("backend/domain/admin/models/bases/exam_question_embeddings.py")
    exam_question_embeddings_content = ""
    if exam_question_embeddings_file.exists():
        exam_question_embeddings_content = exam_question_embeddings_file.read_text(encoding="utf-8")

    # 프롬프트 작성
    # ExamQuestionEmbedding을 정확히 복사하되, exam_question_id를 commentary_id로 변경하는 방식으로 작성
    prompt = f"""다음 ExamQuestionEmbedding 모델을 정확히 참고하여 CommentaryEmbedding ORM 클래스를 작성하세요.

=== 참고: ExamQuestionEmbedding 모델 코드 (이것을 정확히 복사하여 수정) ===
{exam_question_embeddings_content}

=== Commentary 모델 코드 (relationship 확인용) ===
{commentaries_content}

=== 작업 지시 ===
ExamQuestionEmbedding 코드를 기반으로 다음만 변경하세요:
1. 클래스명: `ExamQuestionEmbedding` → `CommentaryEmbedding`
2. __tablename__: `"exam_question_embeddings"` → `"commentary_embeddings"`
3. 외래키 컬럼명: `exam_question_id` → `commentary_id`
4. ForeignKey: `ForeignKey("exam_questions.id", ...)` → `ForeignKey("commentaries.id", ...)`
5. UniqueConstraint 이름: `"uq_exam_question_embeddings_exam_question_id"` → `"uq_commentary_embeddings_commentary_id"`
6. relationship 변수명: `exam_question` → `commentary`
7. relationship 타입: `Mapped["ExamQuestion"]` → `Mapped["Commentary"]`
8. docstring: "ExamQuestion 임베딩 테이블" → "Commentary 임베딩 테이블"

=== 절대 변경하지 말 것 ===
- import 문 구조 (정확히 동일하게 유지)
- Vector import 방식 (try-except 구조)
- TimestampMixin 사용 (created_at, updated_at 직접 정의하지 않음)
- Vector 타입 처리 방식 (if Vector is not None: 구조)
- relationship의 back_populates="embedding_record" (변경하지 않음)
- cascade="all, delete-orphan" (변경하지 않음)
- 타입 힌트 스타일 (Mapped, List, Optional)
- 주석 형식

=== 출력 형식 ===
ExamQuestionEmbedding 코드를 복사한 후 위의 8가지 변경사항만 적용한 완전한 Python 파일을 출력하세요.
코드 블록(```python ... ```) 없이 순수 Python 코드만 출력하세요.
중요: 결과에 '...' 같은 축약/플레이스홀더를 절대로 포함하지 마세요. 파일 전체를 끝까지 완성해서 출력하세요."""

    generated_code = generate_code_with_exaone(prompt, max_new_tokens=1500)

    print("\n=== 생성된 코드 ===")
    print(generated_code)
    print("\n=== 코드 생성 완료 ===\n")

    # 코드 검증
    try:
        _validate_commentary_embeddings_code(generated_code)
    except ValueError as e:
        print(f"[실패] 생성된 코드가 불완전합니다: {e}")
        print("[힌트] 다시 실행하거나 max_new_tokens를 늘려보세요.")
        return

    # 파일에 저장
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(generated_code, encoding="utf-8")

    print(f"[완료] 코드가 {output_file}에 저장되었습니다.")


def main():
    """메인 함수."""
    parser = argparse.ArgumentParser(
        description="ExaOne 모델을 사용하여 CommentaryEmbedding ORM 클래스를 생성합니다."
    )

    args = parser.parse_args()

    generate_commentary_embedding()


if __name__ == "__main__":
    main()

