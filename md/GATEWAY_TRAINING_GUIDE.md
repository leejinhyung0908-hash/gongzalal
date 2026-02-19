# KoELECTRA 게이트웨이 분류기 학습 가이드

## 📋 개요

KoELECTRA 모델을 **게이트웨이 라우팅 분류기**로 학습하여, 1차 게이트웨이에서 규칙기반/정책기반을 판단합니다.

## 🎯 학습 목표

3가지 게이트웨이 라우팅으로 분류:
- **RULE_BASED** (0): 규칙 기반 처리 → `exam_service` (DB 조회)
- **POLICY_BASED** (1): 정책 기반 처리 → `exam_agent` (LLM 사용)
- **BLOCK** (2): 차단 → 서비스 범위 밖

## 📊 데이터 준비

### 1단계: 의도 분류 데이터 생성

```bash
# 각 의도별 100개씩 총 400개 생성
python backend/tools/prepare_intent_training_data.py template \
    --output data/intent_training_data_400.jsonl \
    --samples 100
```

### 2단계: 게이트웨이 데이터셋으로 변환

```bash
# 모든 형식으로 변환 (KoELECTRA, SFT, Chat)
python backend/tools/convert_intent_to_gateway_dataset.py \
    --input data/intent_training_data_400.jsonl \
    --output-dir data/spamdata \
    --format all \
    --split
```

**변환 결과:**
- `intent_training_data_400.gateway.koelectra.jsonl`: KoELECTRA 학습용
- `intent_training_data_400.gateway.koelectra.train.jsonl`: 학습 데이터
- `intent_training_data_400.gateway.koelectra.val.jsonl`: 검증 데이터
- `intent_training_data_400.gateway.sft.jsonl`: SFT 형식
- `intent_training_data_400.gateway.chat.jsonl`: Chat 형식 (EXAONE용)

**데이터 분포:**
- RULE_BASED: 100개 (25.0%) - DB_QUERY
- POLICY_BASED: 200개 (50.0%) - EXPLAIN, ADVICE
- BLOCK: 100개 (25.0%) - OUT_OF_DOMAIN

## 🚀 KoELECTRA 학습

### 기본 학습

```bash
python backend/tools/train_gateway_classifier.py \
    --data data/spamdata/intent_training_data_400.gateway.koelectra.train.jsonl \
    --output artifacts/lora-adapters/koelectra-gateway \
    --epochs 5 \
    --batch-size 16 \
    --learning-rate 2e-5
```

### 고급 옵션

```bash
python backend/tools/train_gateway_classifier.py \
    --data data/spamdata/intent_training_data_400.gateway.koelectra.train.jsonl \
    --output artifacts/lora-adapters/koelectra-gateway \
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

## 📈 학습 결과 확인

학습 완료 후 출력 예시:

```
학습 완료!
최종 성능:
  Accuracy: 0.9500
  Precision: 0.9450
  Recall: 0.9500
  F1: 0.9475

게이트웨이별 성능:
  RULE_BASED:
    Precision: 0.9800
    Recall: 0.9600
    F1: 0.9700
  POLICY_BASED:
    Precision: 0.9200
    Recall: 0.9400
    F1: 0.9300
  BLOCK:
    Precision: 0.9500
    Recall: 0.9600
    F1: 0.9550
```

## 🔧 모델 사용

### 1. 환경 변수 설정

`.env` 파일에 추가:

```bash
KOELECTRA_GATEWAY_LORA_PATH=./artifacts/lora-adapters/koelectra-gateway/run_20260122_120000
```

### 2. 코드 수정

`spam_detector.py`에 게이트웨이 분류 함수 추가:

```python
def classify_gateway_route(text: str) -> dict:
    """게이트웨이 라우팅 분류 (KoELECTRA 사용)"""
    from backend.domain.admin.agents.analysis.spam_detector import mcp_tool_koelectra_filter

    # KoELECTRA로 게이트웨이 분류 (3-class)
    result = mcp_tool_koelectra_gateway_classifier.invoke({"text": text})

    label_id = result.get("predicted_label", 0)
    confidence = result.get("confidence", 0.5)

    gateway_map = {
        0: "RULE_BASED",
        1: "POLICY_BASED",
        2: "BLOCK"
    }

    return {
        "gateway": gateway_map.get(label_id, "POLICY_BASED"),
        "confidence": confidence,
        "label_id": label_id
    }
```

### 3. ExamFlow에서 사용

```python
# exam_flow_v2.py에서
gateway_result = classify_gateway_route(request_text)

if gateway_result["gateway"] == "RULE_BASED":
    # exam_service로 라우팅
    return await self._handle_db_query(...)
elif gateway_result["gateway"] == "POLICY_BASED":
    # exam_agent로 라우팅
    return await self._handle_explain(...)
else:  # BLOCK
    # 차단 메시지
    return await self._handle_out_of_domain(...)
```

## 📊 데이터 형식

### KoELECTRA 형식

```json
{"text": "2024년 지방직 9급 회계학 3번 정답 뭐야?", "label": "RULE_BASED"}
{"text": "신뢰보호의 원칙이 왜 적용 안 돼?", "label": "POLICY_BASED"}
{"text": "오늘 날씨 어때?", "label": "BLOCK"}
```

### SFT 형식

```json
{
  "instruction": "다음 시험 관련 질문을 분석하여 처리 방식을 판단하고 JSON 형식으로만 답하세요.",
  "input": {
    "question": "2024년 지방직 9급 회계학 3번 정답 뭐야?",
    "intent": "DB_QUERY"
  },
  "output": {
    "action": "RULE_BASED",
    "reason": "명확한 데이터 조회 요청으로 규칙 기반 처리 가능",
    "confidence": 0.95,
    "intent": "DB_QUERY"
  }
}
```

### Chat 형식 (EXAONE용)

```json
{
  "messages": [
    {
      "role": "user",
      "content": "다음 시험 관련 질문을 분석하여 처리 방식을 판단하고, 다음 JSON 형식으로만 답변하세요:\n\n{\n  \"action\": \"RULE_BASED\" 또는 \"POLICY_BASED\" 또는 \"BLOCK\",\n  \"reason\": \"판정 근거\",\n  \"confidence\": 0.0~1.0 사이의 신뢰도,\n  \"intent\": \"의도\"\n}\n\n중요: JSON 형식으로만 답변하세요. 다른 텍스트는 포함하지 마세요.\n\n시험 관련 질문:\n2024년 지방직 9급 회계학 3번 정답 뭐야?"
    },
    {
      "role": "assistant",
      "content": "{\"action\": \"RULE_BASED\", \"reason\": \"명확한 데이터 조회 요청으로 규칙 기반 처리 가능\", \"confidence\": 0.95, \"intent\": \"DB_QUERY\"}"
    }
  ]
}
```

## 🎯 성능 목표

- **Accuracy**: 0.90 이상
- **F1 Score**: 0.85 이상 (각 클래스별)
- **처리 속도**: 50ms 이내 (GPU 기준)

## ⚠️ 주의사항

1. **데이터 불균형**: POLICY_BASED가 50%로 많으므로, 필요시 데이터 증강 고려
2. **임계치 조정**: RULE_BASED와 POLICY_BASED의 경계가 모호할 수 있음
3. **정기 재학습**: 새로운 질문 패턴이 생기면 주기적으로 재학습

## 🔄 전체 워크플로우

```
1. 의도 분류 데이터 생성
   python prepare_intent_training_data.py template --samples 100
   ↓
2. 게이트웨이 데이터셋으로 변환
   python convert_intent_to_gateway_dataset.py --format all --split
   ↓
3. KoELECTRA 학습
   python train_gateway_classifier.py --data ... --output ...
   ↓
4. 모델 평가 및 검증
   ↓
5. 프로덕션 배포
   (환경 변수 설정)
   ↓
6. 모니터링 및 피드백 수집
   ↓
7. 재학습 (주기적)
```

## 📝 체크리스트

- [ ] 의도 분류 데이터 생성 완료
- [ ] 게이트웨이 데이터셋 변환 완료
- [ ] 학습/검증 데이터 분할 완료
- [ ] KoELECTRA 모델 학습 완료
- [ ] 성능 목표 달성 확인
- [ ] 환경 변수 설정 완료
- [ ] 코드 통합 완료
- [ ] 프로덕션 테스트 완료

