# KoELECTRA 의도 분류기 학습 가이드

## 📋 개요

KoELECTRA 모델을 **의도 분류(Intent Classification)**용으로 재학습하여, 규칙 기반 분류보다 더 정확한 의도 판단을 수행합니다.

## 🎯 학습 목표

4가지 의도로 분류:
- **DB_QUERY** (0): 명확한 데이터 조회 요청
- **EXPLAIN** (1): 해설 및 추론 요청
- **ADVICE** (2): 학습 상담/가이드 요청
- **OUT_OF_DOMAIN** (3): 서비스 범위 밖

## 📊 데이터 준비

### 1단계: 데이터 수집

#### 방법 1: 실제 사용자 질문 수집 (권장)

```bash
# DB에서 실제 질문 가져오기
python tools/prepare_intent_training_data.py collect \
    --output data/raw_questions.jsonl \
    --limit 1000
```

#### 방법 2: 템플릿 데이터 생성 (초기 테스트용)

```bash
# 각 의도별 100개씩 총 400개 생성
python tools/prepare_intent_training_data.py template \
    --output data/template_questions.jsonl \
    --samples 100

# 또는 다른 개수 지정
python tools/prepare_intent_training_data.py template \
    --output data/template_questions.jsonl \
    --samples 50  # 각 의도별 50개씩
```

### 2단계: 데이터 레이블링

#### 자동 레이블링 (초기)

```bash
# 규칙 기반으로 자동 레이블링
python tools/prepare_intent_training_data.py label \
    --input data/raw_questions.jsonl \
    --output data/labeled_questions.jsonl
```

#### 수동 검토 (필수)

자동 레이블링된 데이터 중 신뢰도가 낮은 항목(`needs_review: true`)은 반드시 수동 검토해야 합니다.

**JSONL 형식:**
```json
{"text": "2024년 지방직 9급 회계학 3번 정답 뭐야?", "intent": "DB_QUERY"}
{"text": "신뢰보호의 원칙이 왜 적용 안 돼?", "intent": "EXPLAIN"}
{"text": "직장인인데 하루 4시간 공부로 합격 가능할까?", "intent": "ADVICE"}
{"text": "오늘 날씨 어때?", "intent": "OUT_OF_DOMAIN"}
```

### 3단계: 데이터 검증

```bash
# 데이터셋 통계 확인
python tools/prepare_intent_training_data.py stats \
    --input data/labeled_questions.jsonl
```

**권장 데이터 수:**
- 각 의도별 최소 **50개 이상** (권장: 100-200개)
- 총 데이터: **400-800개** 이상
- 클래스 불균형 최소화 (각 클래스 비율 20-30%)

## 🚀 학습 실행

### 기본 학습

```bash
python tools/train_intent_classifier.py \
    --data data/labeled_questions.jsonl \
    --output artifacts/lora-adapters/koelectra-intent \
    --epochs 5 \
    --batch-size 16 \
    --learning-rate 2e-5
```

### 고급 옵션

```bash
python tools/train_intent_classifier.py \
    --data data/labeled_questions.jsonl \
    --output artifacts/lora-adapters/koelectra-intent \
    --base-model monologg/koelectra-small-v3-discriminator \
    --epochs 10 \
    --batch-size 32 \
    --learning-rate 1e-5 \
    --lora-r 16 \
    --lora-alpha 32 \
    --lora-dropout 0.1 \
    --train-split 0.8 \
    --max-length 256
```

### 파라미터 설명

| 파라미터 | 기본값 | 설명 |
|---------|--------|------|
| `--data` | 필수 | 학습 데이터 JSONL 파일 경로 |
| `--output` | `./artifacts/lora-adapters/koelectra-intent` | 출력 디렉토리 |
| `--base-model` | `monologg/koelectra-small-v3-discriminator` | 베이스 모델 |
| `--epochs` | `5` | 학습 에포크 수 |
| `--batch-size` | `16` | 배치 크기 |
| `--learning-rate` | `2e-5` | 학습률 |
| `--lora-r` | `8` | LoRA rank (높을수록 모델 용량 증가) |
| `--lora-alpha` | `16` | LoRA alpha (스케일링 파라미터) |
| `--lora-dropout` | `0.1` | LoRA dropout |
| `--train-split` | `0.8` | 학습/평가 데이터 분할 비율 |
| `--max-length` | `256` | 최대 시퀀스 길이 |

## 📈 학습 결과 확인

학습 완료 후 출력 예시:

```
학습 완료!
최종 성능:
  Accuracy: 0.9234
  Precision: 0.9156
  Recall: 0.9234
  F1: 0.9194

의도별 성능:
  DB_QUERY:
    Precision: 0.9500
    Recall: 0.9600
    F1: 0.9550
  EXPLAIN:
    Precision: 0.8900
    Recall: 0.8800
    F1: 0.8850
  ...
```

## 🔧 모델 사용

### 1. 환경 변수 설정

`.env` 파일에 추가:

```bash
KOELECTRA_INTENT_LORA_PATH=./artifacts/lora-adapters/koelectra-intent/run_20260122_120000
```

### 2. 코드 수정

`intent_classifier.py`에 모델 기반 분류 함수 추가:

```python
def classify_intent_model_based(text: str, entities: ExamEntities) -> ExamIntent:
    """모델 기반 의도 분류 (KoELECTRA 사용)"""
    from backend.domain.admin.agents.analysis.spam_detector import mcp_tool_koelectra_filter

    # KoELECTRA로 의도 분류 (4-class)
    result = mcp_tool_koelectra_intent_classifier.invoke({"text": text})

    intent_id = result.get("predicted_label", 0)
    confidence = result.get("confidence", 0.5)

    intent_map = {
        0: "DB_QUERY",
        1: "EXPLAIN",
        2: "ADVICE",
        3: "OUT_OF_DOMAIN"
    }

    return {
        "intent": intent_map.get(intent_id, "DB_QUERY"),
        "confidence": confidence,
        "is_complex": intent_id in [1, 2],  # EXPLAIN, ADVICE는 복잡
        "entities_found": get_found_entities(entities),
        "missing_entities": get_missing_entities(entities)
    }
```

## 📊 데이터 수집 전략

### 실제 사용 데이터 수집

1. **로그 분석**: 실제 API 요청 로그에서 질문 추출
2. **사용자 피드백**: 잘못 분류된 케이스 수집
3. **A/B 테스트**: 규칙 기반 vs 모델 기반 비교 데이터

### 데이터 증강 (Data Augmentation)

```python
# 동의어 치환
"정답 뭐야?" → "정답 알려줘", "정답은?", "답이 뭐야?"

# 문장 구조 변형
"2024년 지방직 9급 회계학 3번" → "회계학 3번 문제, 2024년 지방직 9급"
```

## 🎯 성능 목표

- **Accuracy**: 0.90 이상
- **F1 Score**: 0.85 이상 (각 클래스별)
- **처리 속도**: 50ms 이내 (GPU 기준)

## ⚠️ 주의사항

1. **데이터 품질**: 잘못 레이블링된 데이터는 모델 성능을 크게 저하시킵니다.
2. **클래스 불균형**: OUT_OF_DOMAIN이 너무 많으면 다른 클래스 성능이 떨어질 수 있습니다.
3. **과적합 방지**: Early stopping과 dropout을 적절히 설정하세요.
4. **정기 재학습**: 새로운 질문 패턴이 생기면 주기적으로 재학습하세요.

## 🔄 학습 파이프라인

```
1. 데이터 수집
   ↓
2. 자동 레이블링 (규칙 기반)
   ↓
3. 수동 검토 및 수정
   ↓
4. 데이터 검증 (통계 확인)
   ↓
5. 모델 학습
   ↓
6. 평가 및 검증
   ↓
7. 프로덕션 배포
   ↓
8. 모니터링 및 피드백 수집
   ↓
9. 재학습 (주기적)
```

## 📝 체크리스트

- [ ] 각 의도별 최소 50개 이상 데이터 수집
- [ ] 데이터 레이블링 및 검증 완료
- [ ] 클래스 불균형 확인 및 조정
- [ ] 학습 파라미터 튜닝
- [ ] 평가 데이터셋으로 성능 확인
- [ ] 프로덕션 환경에서 A/B 테스트
- [ ] 모니터링 및 피드백 수집 체계 구축

## 🐛 문제 해결

### 학습이 수렴하지 않는 경우
- 학습률 낮추기 (`--learning-rate 1e-5`)
- 배치 크기 조정
- 데이터 품질 확인

### 특정 클래스 성능이 낮은 경우
- 해당 클래스 데이터 증강
- 클래스 가중치 조정
- 더 많은 데이터 수집

### 과적합 발생
- Dropout 증가 (`--lora-dropout 0.2`)
- Early stopping patience 증가
- 데이터 증강

