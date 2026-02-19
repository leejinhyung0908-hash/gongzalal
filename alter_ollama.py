"""ORM 클래스 생성 스크립트.

EXAONE 모델을 사용하여 SQLAlchemy 모델을 참조하여
임베딩 테이블 ORM 클래스를 생성합니다.
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

    # 생성된 코드 추출
    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

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


def generate_exam_question_embedding():
    """ExamQuestionEmbedding ORM 클래스를 생성합니다."""
    output_file = "backend/domain/admin/models/bases/exam_question_embeddings.py"

    # exam_questions.py 파일 읽기
    exam_questions_file = Path("backend/domain/admin/models/bases/exam_questions.py")
    exam_questions_content = exam_questions_file.read_text(encoding="utf-8")

    # 프롬프트 작성
    prompt = f"""다음 SQLAlchemy ExamQuestion 모델을 참고하여 ExamQuestionEmbedding ORM 클래스를 작성하세요.

=== ExamQuestion 모델 코드 ===
{exam_questions_content}

=== Alembic 마이그레이션 테이블 스키마 ===
테이블명: exam_question_embeddings
컬럼:
- id: BigInteger, PK, autoincrement=True, nullable=False, comment='임베딩 레코드 고유 식별자'
- exam_question_id: BigInteger, FK -> exam_questions.id, nullable=False, unique=True, ondelete='CASCADE', comment='시험 문항 ID'
- embedding: Vector(1536), nullable=False, comment='1536차원 임베딩 벡터 (OpenAI text-embedding-3-small)'
- created_at: TIMESTAMP(timezone=True), server_default=now(), nullable=False, comment='레코드 생성 시간'
- updated_at: TIMESTAMP(timezone=True), server_default=now(), nullable=False, comment='레코드 수정 시간'

=== 요구사항 ===
1. Base 클래스: from backend.domain.shared.bases import Base, TimestampMixin 사용
2. pgvector: from pgvector.sqlalchemy import Vector 사용 (try-except로 안전하게)
3. SQLAlchemy imports: BigInteger, ForeignKey, UniqueConstraint, relationship, Mapped, mapped_column
4. 타임스탬프: TimestampMixin 사용 (created_at, updated_at 자동 포함)
5. relationship: exam_question (back_populates="embedding_record") 설정
6. exam_questions.py의 코딩 스타일과 일관성 유지:
   - Mapped 타입 힌트 사용
   - mapped_column 사용
   - 주석 형식 유지
   - __future__ import annotations 사용
7. Vector는 try-except로 안전하게 import (Vector가 None일 경우 대비)
8. __tablename__ = "exam_question_embeddings" 사용
9. Python 코드만 출력 (주석이나 설명 없이 순수 코드만)
10. docstring은 ExamQuestion 모델과 유사한 형식으로 작성
11. exam_question_id는 unique=True 설정
12. ForeignKey에 ondelete="CASCADE" 설정
13. UniqueConstraint를 __table_args__에 추가

=== 출력 형식 ===
파일 전체 코드를 출력하세요. import 문부터 시작하여 완전한 Python 파일 형태로 작성하세요."""

    generated_code = generate_code_with_exaone(prompt)

    print("\n=== 생성된 코드 ===")
    print(generated_code)
    print("\n=== 코드 생성 완료 ===\n")

    # 파일에 저장
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(generated_code, encoding="utf-8")

    print(f"[완료] 코드가 {output_file}에 저장되었습니다.")


def main():
    """메인 함수."""
    parser = argparse.ArgumentParser(
        description="ExaOne 모델을 사용하여 SQLAlchemy ORM 클래스를 생성합니다."
    )
    parser.add_argument(
        "--type",
        type=str,
        choices=["exam"],
        default="exam",
        help="생성할 임베딩 모델 타입 (exam: ExamQuestionEmbedding)"
    )

    args = parser.parse_args()

    if args.type == "exam":
        generate_exam_question_embedding()
    else:
        print(f"알 수 없는 타입: {args.type}")


if __name__ == "__main__":
    main()
