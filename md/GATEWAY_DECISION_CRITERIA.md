# 1차 게이트웨이 규칙/정책 기반 판단 기준

## 📊 개요

1차 게이트웨이에서는 **KoELECTRA 모델의 `spam_prob` 값**을 기준으로 요청을 **규칙 기반(Rule-based)** 또는 **정책 기반(Policy-based)**으로 분기합니다.

## 🔍 핵심 개념

### `spam_prob`의 의미

`spam_prob`는 원래 스팸 필터 모델(KoELECTRA)의 출력이지만, 여기서는 **요청의 명확성(Clarity)**을 측정하는 지표로 재사용됩니다:

- **낮은 spam_prob (< 0.3)**: 요청이 **명확하고 구조화됨** → 규칙 기반 처리
- **높은 spam_prob (> 0.8)**: 요청이 **명확하지만 부정적/의심스러움** → 규칙 기반 처리 (차단)
- **중간 spam_prob (0.3 ~ 0.8)**: 요청이 **애매하고 모호함** → 정책 기반 처리 (LLM 분석 필요)

## 📐 임계치 설정

### MCP Controller (게이트웨이)

```python
# backend/domain/admin/orchestrators/mcp_controller.py
SPAM_PROB_LOW = 0.3   # 이 미만이면 즉시 ALLOW
SPAM_PROB_HIGH = 0.8  # 이 초과면 즉시 DENY
```

**분기 로직:**
```
spam_prob < 0.3  → gateway_action = "deliver" (즉시 전달, EXAONE 불필요)
spam_prob > 0.8  → gateway_action = "block" (즉시 차단, EXAONE 불필요)
0.3 ≤ spam_prob ≤ 0.8 → gateway_action = "analyze" (EXAONE 분석 필요)
```

### Exam/User/Commentary Flow (Orchestrator)

```python
# backend/domain/admin/orchestrators/exam_flow.py
RULE_BASED_THRESHOLD_LOW = 0.3   # 이하: 규칙 기반
RULE_BASED_THRESHOLD_HIGH = 0.8  # 이상: 규칙 기반
```

**분기 로직:**
```
spam_prob < 0.3  → 규칙 기반 (exam_service) - 명확한 요청
spam_prob > 0.8  → 규칙 기반 (exam_service) - 명확하지만 의심스러운 요청
0.3 ≤ spam_prob ≤ 0.8 → 정책 기반 (exam_agent) - 애매한 요청, LLM 분석 필요
```

## 🎯 판단 기준 상세

### 1. 규칙 기반 (Rule-based) 처리

**조건:** `spam_prob < 0.3` 또는 `spam_prob > 0.8`

**특징:**
- ✅ **빠른 처리**: 정규식, DB 조회 등으로 즉시 처리
- ✅ **명확한 요청**: 구조화된 형식의 요청
- ✅ **예측 가능**: 항상 동일한 결과

**예시:**
- ✅ `spam_prob = 0.1`: "작년 회계학 3번 정답 뭐야?" → 명확한 구조
- ✅ `spam_prob = 0.9`: 명백한 스팸/악성 요청 → 즉시 차단

**처리 방식:**
- `exam_service.py`: 정규식으로 연도/과목/문항번호 파싱 → DB 조회
- `user_service.py`: 구조화된 사용자 정보 처리
- `commentary_service.py`: 명확한 해설 요청 처리

### 2. 정책 기반 (Policy-based) 처리

**조건:** `0.3 ≤ spam_prob ≤ 0.8`

**특징:**
- 🤔 **애매한 요청**: 모호하거나 비구조화된 요청
- 🧠 **LLM 분석 필요**: 의미 이해 및 해석 필요
- ⏱️ **느린 처리**: LLM 추론 시간 필요

**예시:**
- 🤔 `spam_prob = 0.5`: "어떤 문제가 어려웠어?" → 모호한 질문
- 🤔 `spam_prob = 0.6`: "회계 관련해서 질문이 있는데..." → 불완전한 요청

**처리 방식:**
- `exam_agent.py`: LLM으로 요청 의도 파악 → 구조화 → 처리
- `user_agent.py`: LLM으로 사용자 의도 분석
- `commentary_agent.py`: LLM으로 해설 생성 요청 해석

## 🔄 처리 흐름

### Exam 요청 처리 예시

```
사용자 요청: "작년 회계학 3번 정답 뭐야?"

1. KoELECTRA 분석
   └─ spam_prob = 0.15 (명확한 구조)
   └─ label = "ham"
   └─ threshold_zone = "low"

2. 분기 판단
   └─ spam_prob < 0.3 → 규칙 기반

3. 규칙 기반 처리 (exam_service)
   └─ 정규식으로 파싱:
      - 연도: "작년" → 2024
      - 과목: "회계학"
      - 문항: "3번"
   └─ DB 조회
   └─ 결과 반환
```

```
사용자 요청: "어떤 문제가 어려웠어?"

1. KoELECTRA 분석
   └─ spam_prob = 0.55 (모호한 질문)
   └─ label = "uncertain"
   └─ threshold_zone = "ambiguous"

2. 분기 판단
   └─ 0.3 ≤ spam_prob ≤ 0.8 → 정책 기반

3. 정책 기반 처리 (exam_agent)
   └─ LLM으로 의도 파악
   └─ 대화 맥락 분석
   └─ 적절한 응답 생성
```

## 📊 KoELECTRA 출력 형식

```python
{
    "spam_prob": 0.45,           # 0.0 ~ 1.0 사이의 확률
    "label": "uncertain",        # "ham" | "spam" | "uncertain"
    "confidence": "medium",      # "low" | "medium" | "high"
    "method": "koelectra",       # "koelectra" | "keyword"
    "threshold_zone": "ambiguous" # "low" | "ambiguous" | "high"
}
```

### Label 결정 로직

```python
if spam_prob < 0.35:
    label = "ham"
    confidence = "high" if spam_prob < 0.2 else "medium"
elif spam_prob > 0.75:
    label = "spam"
    confidence = "high" if spam_prob > 0.9 else "medium"
else:
    label = "uncertain"
    confidence = "medium"
```

## 🎨 시각적 표현

```
spam_prob 값에 따른 분기:

0.0 ────────────────────────────────────────────────── 1.0
│                                                      │
│  [규칙 기반]        [정책 기반]        [규칙 기반]   │
│  (명확)            (애매)            (명확/의심)    │
│                                                      │
0.0 ──────── 0.3 ─────────────────── 0.8 ─────────── 1.0
           ↑                              ↑
      RULE_BASED_THRESHOLD_LOW    RULE_BASED_THRESHOLD_HIGH
```

## 🔧 설정 변경

임계치를 변경하려면 다음 파일들을 수정하세요:

1. **MCP Controller**: `backend/domain/admin/orchestrators/mcp_controller.py`
   ```python
   SPAM_PROB_LOW = 0.3   # 변경 가능
   SPAM_PROB_HIGH = 0.8  # 변경 가능
   ```

2. **Orchestrator**: `backend/domain/admin/orchestrators/exam_flow.py`
   ```python
   RULE_BASED_THRESHOLD_LOW = 0.3   # 변경 가능
   RULE_BASED_THRESHOLD_HIGH = 0.8  # 변경 가능
   ```

3. **KoELECTRA 필터**: `backend/domain/admin/agents/analysis/spam_detector.py`
   ```python
   SPAM_PROB_LOW = 0.35   # 변경 가능
   SPAM_PROB_HIGH = 0.75  # 변경 가능
   ```

## 💡 왜 spam_prob를 사용하나?

1. **빠른 판단**: KoELECTRA는 가벼운 모델로 빠르게 추론 가능
2. **명확성 측정**: 구조화된 요청은 낮은 spam_prob, 모호한 요청은 중간 spam_prob
3. **비용 절감**: 명확한 요청은 LLM 호출 없이 처리 가능
4. **재사용**: 이미 학습된 스팸 필터 모델 활용

## ⚠️ 주의사항

1. **임계치 조정**: 도메인에 따라 최적 임계치가 다를 수 있음
2. **모델 품질**: KoELECTRA 모델의 학습 데이터에 따라 성능 차이
3. **False Positive**: 명확한 요청이 중간 구간으로 분류될 수 있음
4. **False Negative**: 애매한 요청이 규칙 기반으로 처리될 수 있음

## 📈 모니터링

각 요청의 `spam_prob`와 분기 결과를 로그로 확인:

```python
print(f"[ExamFlow] KoELECTRA 결과: spam_prob={spam_prob:.2f}, "
      f"label={label}, confidence={confidence}")
print(f"[ExamFlow] 규칙 기반 처리로 라우팅 → exam_service")
# 또는
print(f"[ExamFlow] 정책 기반 처리로 라우팅 → exam_agent")
```

이를 통해 임계치를 최적화할 수 있습니다.

