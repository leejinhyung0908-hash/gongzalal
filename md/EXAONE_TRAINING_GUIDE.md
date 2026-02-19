# EXAONE 모델 Fine-tuning 가이드

합격 수기 데이터를 EXAONE 모델에 학습시키는 방법입니다.

## 📊 현재 데이터 현황

### 학습 데이터 (JSONL)
- **gongdanki**: 942개
- **megagong**: 3,968개
- **통합**: 4,910개
- **형식**: Instruction + Input + Output (Chain-of-Thought 포함)

### Neon DB (RAG용)
- **gongdanki**: 원문 JSON + KURE-v1 embedding (1024차원)
- **megagong**: 원문 JSON + KURE-v1 embedding (1024차원)
- **용도**: 정확한 근거 검색 (RAG)

## ✅ 학습 준비 완료 체크리스트

### 1. 데이터 확인
- [x] `success_stories_training.jsonl` (942개)
- [x] `megagong_stories_training.jsonl` (3,968개)
- [x] 통합 파일 생성 (`merged_training_data.jsonl`)

### 2. 데이터 형식 확인
현재 데이터 형식:
```json
{
  "instruction": "공무원 수험 멘토로서, 제공된 합격 수기를 바탕으로 질문자에게 공감하고 구체적인 학습 전략을 제시하세요. 답변은 항상 따뜻하고 전문적인 어조를 유지하세요.",
  "input": {
    "question": "전업 수험생으로 공부하는데 하루 일과를 어떻게 구성해야 할까요?",
    "intent": "ADVICE",
    "context": "합격자 수기: 1년~1년 6개월 수험기간, 일일 학습 계획: ..."
  },
  "output": {
    "thought_process": "1. 전업 수험생의 일일 계획 질문임을 인지. 2. 합격 수기 1번의 daily_plan 분석. ...",
    "response": "전업 수험생이시군요! 시간이 많다고 해서 방심하면 안 됩니다. ..."
  }
}
```

### 3. EXAONE 학습 형식 확인 필요

EXAONE 모델이 요구하는 형식에 따라 변환이 필요할 수 있습니다:

#### 옵션 A: 현재 형식 그대로 사용
- Instruction 형식으로 사용 가능한지 확인 필요

#### 옵션 B: Chat 형식으로 변환
```json
{
  "messages": [
    {
      "role": "user",
      "content": "전업 수험생으로 공부하는데 하루 일과를 어떻게 구성해야 할까요?"
    },
    {
      "role": "assistant",
      "content": "전업 수험생이시군요! 시간이 많다고 해서 방심하면 안 됩니다. ..."
    }
  ]
}
```

## 🚀 학습 실행 방법

### 6GB VRAM (RTX 3050) 최적화 (권장)

**Windows:**
```bash
train_exaone_6gb_vram.bat
```

**Linux/Mac:**
```bash
bash train_exaone_6gb_vram.sh
```

**또는 직접 실행:**
```bash
python train_exaone_success_stories.py \
    --data data/success_stories/merged_training_data.jsonl \
    --output artifacts/lora-adapters/exaone-success-stories \
    --epochs 3 \
    --batch-size 1 \
    --learning-rate 2e-4 \
    --max-length 1024 \
    --gradient-accumulation-steps 8 \
    --use-4bit
```

### 기본 학습 (8GB+ VRAM)

```bash
# 통합 파일로 학습
python train_exaone_success_stories.py \
    --data data/success_stories/merged_training_data.jsonl \
    --output artifacts/lora-adapters/exaone-success-stories \
    --epochs 3 \
    --batch-size 4 \
    --learning-rate 2e-4 \
    --max-length 2048
```

### 고급 옵션

```bash
# 더 많은 에포크, 더 큰 배치
python train_exaone_success_stories.py \
    --data data/success_stories/merged_training_data.jsonl \
    --output artifacts/lora-adapters/exaone-success-stories \
    --base-model artifacts/base-models/exaone \
    --epochs 5 \
    --batch-size 8 \
    --learning-rate 1e-4 \
    --lora-r 32 \
    --lora-alpha 64 \
    --max-length 2048 \
    --train-split 0.9
```

### 개별 파일 사용

```bash
# gongdanki만 학습
python train_exaone_success_stories.py \
    --data data/success_stories/gongdanki/success_stories_training.jsonl \
    --output artifacts/lora-adapters/exaone-gongdanki

# megagong만 학습
python train_exaone_success_stories.py \
    --data data/success_stories/megagong/megagong_stories_training.jsonl \
    --output artifacts/lora-adapters/exaone-megagong
```

## 📝 파라미터 설명

| 파라미터 | 기본값 | 설명 |
|---------|--------|------|
| `--data` | 필수 | 학습 데이터 JSONL 파일 경로 |
| `--output` | `artifacts/lora-adapters/exaone-success-stories` | 출력 디렉토리 |
| `--base-model` | `artifacts/base-models/exaone` | 베이스 모델 경로 |
| `--epochs` | `3` | 학습 에포크 수 |
| `--batch-size` | `4` | 배치 크기 (GPU 메모리에 따라 조정) |
| `--learning-rate` | `2e-4` | 학습률 |
| `--lora-r` | `16` | LoRA rank (높을수록 모델 용량 증가) |
| `--lora-alpha` | `32` | LoRA alpha (스케일링 파라미터) |
| `--lora-dropout` | `0.1` | LoRA dropout |
| `--max-length` | `2048` | 최대 시퀀스 길이 |
| `--train-split` | `0.9` | 학습/검증 데이터 분할 비율 |
| `--gradient-accumulation-steps` | `4` | Gradient accumulation steps |

## ⚠️ 주의사항

### 시스템 요구사항

| VRAM | 배치 크기 | Gradient Accumulation | 권장 설정 |
|------|----------|----------------------|----------|
| **6GB** (RTX 3050) | 1 | 8 | `--batch-size 1 --gradient-accumulation-steps 8 --use-4bit --max-length 1024` |
| 8GB | 2 | 4 | `--batch-size 2 --gradient-accumulation-steps 4 --use-4bit --max-length 1536` |
| 12GB+ | 4 | 4 | `--batch-size 4 --gradient-accumulation-steps 4 --max-length 2048` |

### 6GB VRAM 최적화 설정

- **배치 크기**: 1 (메모리 절약)
- **Gradient Accumulation**: 8 (실제 배치 크기 = 1 × 8 = 8)
- **4-bit 양자화**: 활성화 (메모리 사용량 약 50% 감소)
- **최대 길이**: 1024 (2048보다 짧게 설정)
- **예상 학습 시간**: 약 2-4시간 (에포크당 40-80분)

### 기타 주의사항

1. **데이터 품질**:
   - 총 4,910개는 충분한 양입니다 (100-300개 권장 범위를 초과)
   - 고품질 데이터이므로 학습 효과가 좋을 것으로 예상

2. **학습 시간**:
   - 데이터 양에 비례하여 학습 시간이 소요됩니다
   - 6GB VRAM: 배치 크기 1로 인해 학습 시간이 더 걸릴 수 있음

3. **검증 데이터**:
   - 학습 데이터의 10-20%를 검증용으로 분리 권장
   - 예: 4,910개 → 학습 4,419개, 검증 491개

4. **필수 패키지**:
   ```bash
   pip install transformers peft datasets accelerate bitsandbytes
   ```

## 🔍 학습 전 최종 확인

1. **데이터 통합 확인**
   ```bash
   python merge_training_data.py
   ```

2. **데이터 형식 검증**
   - 모든 필수 필드 존재 확인
   - JSON 형식 올바른지 확인

3. **EXAONE 형식 확인**
   - EXAONE 학습 플랫폼/문서에서 요구 형식 확인
   - 필요시 형식 변환

## 📚 참고

- **EXAONE 학습용 (JSONL)**: 말투와 논리를 배우는 교과서
  - `merged_training_data.jsonl` (4,910개)
  - 모델에 학습시켜 말투와 사고 과정 학습

- **Neon DB (RAG)**: 정확한 근거를 찾는 도서관
  - 원문 JSON + embedding 벡터
  - 실제 답변 생성 시 근거 검색에 사용

