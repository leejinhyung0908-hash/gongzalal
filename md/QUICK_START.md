# 의도 기반 라우팅 시스템 빠른 시작 가이드

## 🚀 활성화 방법

### 1. 환경 변수 설정

`.env` 파일에 다음을 추가:

```bash
# 의도 기반 라우팅 활성화
USE_INTENT_BASED_ROUTING=true
```

### 2. 서버 재시작

```bash
uvicorn backend.main:app --host localhost --port 8000 --reload
```

## 📊 의도 분류 결과 확인

서버 로그에서 다음과 같은 메시지를 확인할 수 있습니다:

```
[ExamFlow] 의도 기반 라우팅 활성화 (ExamFlowV2)
[ExamFlowV2] 의도: DB_QUERY, 신뢰도: 0.90, 복잡도: False, 엔티티: ['year', 'subject', 'question_no']
[ExamFlowV2] DB_QUERY → exam_service로 라우팅
```

## 🧪 테스트 예시

### DB_QUERY (명확한 조회)

```bash
curl -X POST http://localhost:8000/api/v1/admin/exam/flow \
  -H "Content-Type: application/json" \
  -d '{"question": "2024년 지방직 9급 교육행정직 회계학 3번 정답 뭐야?"}'
```

**예상 결과:**
- `intent: "DB_QUERY"`
- `confidence: 0.9`
- `is_complex: false`
- `exam_service`로 라우팅

### EXPLAIN (해설 요청)

```bash
curl -X POST http://localhost:8000/api/v1/admin/exam/flow \
  -H "Content-Type: application/json" \
  -d '{"question": "신뢰보호의 원칙이 이 판례에서 왜 적용 안 돼?"}'
```

**예상 결과:**
- `intent: "EXPLAIN"`
- `confidence: 0.8`
- `is_complex: true`
- `exam_agent`로 라우팅 (LLM 사용)

### ADVICE (학습 상담)

```bash
curl -X POST http://localhost:8000/api/v1/admin/exam/flow \
  -H "Content-Type: application/json" \
  -d '{"question": "직장인인데 하루 4시간 공부로 합격 가능할까?"}'
```

**예상 결과:**
- `intent: "ADVICE"`
- `confidence: 0.8`
- `is_complex: true`
- `exam_agent`로 라우팅 (LLM 사용)

### OUT_OF_DOMAIN (도메인 외)

```bash
curl -X POST http://localhost:8000/api/v1/admin/exam/flow \
  -H "Content-Type: application/json" \
  -d '{"question": "오늘 날씨 어때?"}'
```

**예상 결과:**
- `intent: "OUT_OF_DOMAIN"`
- `success: false`
- `user_message`: 도메인 외 안내 메시지

## 🔄 기존 시스템으로 복귀

`.env` 파일에서:

```bash
USE_INTENT_BASED_ROUTING=false
```

또는 환경 변수 제거 후 서버 재시작.

## 📝 주요 변경 사항

1. **의도 분류**: spam_prob → intent (DB_QUERY, EXPLAIN, ADVICE, OUT_OF_DOMAIN)
2. **엔티티 추출**: 모듈화 및 개선
3. **명확한 분기**: 의도별 명확한 처리 경로
4. **사용자 안내**: 누락된 정보에 대한 명확한 안내

## 🐛 문제 해결

### 의도가 잘못 분류되는 경우

`backend/domain/admin/agents/analysis/intent_classifier.py`의 키워드 목록을 조정하세요.

### 엔티티 추출 실패

`backend/domain/admin/agents/analysis/entity_extractor.py`의 파싱 로직을 개선하세요.

### 로그 확인

서버 로그에서 `[ExamFlowV2]`로 시작하는 메시지를 확인하여 분기 과정을 추적할 수 있습니다.

