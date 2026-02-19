# 전체 플로우 테스트 가이드

## 📋 개요

학습된 KoELECTRA 게이트웨이 분류기와 Neon DB를 사용하여 전체 플로우를 테스트합니다.

**테스트 플로우:**
```
사용자 입력: "2025년 국가직 행정법총론 3번 알려줘"
  ↓
프론트엔드 (Next.js)
  ↓
백엔드 API (/api/v1/admin/exam/flow)
  ↓
KoELECTRA 게이트웨이 분류기 → RULE_BASED
  ↓
Rule Parser (엔티티 추출)
  ↓
Neon DB 조회
  ↓
응답 생성 (템플릿)
  ↓
프론트엔드에 응답
```

## 🔧 사전 준비

### 1. 환경 변수 확인

`.env` 파일에 다음 설정이 있는지 확인:

```bash
# Neon DB 연결
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=require

# KoELECTRA 게이트웨이 분류기 경로 (자동 설정됨)
KOELECTRA_GATEWAY_LORA_PATH=./artifacts/lora-adapters/koelectra-gateway/run_20260122_154846
```

### 2. 학습된 모델 확인

```bash
# 모델 경로 확인
ls artifacts/lora-adapters/koelectra-gateway/run_20260122_154846/

# 다음 파일들이 있어야 함:
# - adapter_config.json
# - adapter_model.safetensors
# - tokenizer_config.json
# - tokenizer.json
```

### 3. Neon DB 데이터 확인

Neon Console에서 `exam_questions` 테이블에 데이터가 있는지 확인:

```sql
SELECT COUNT(*) FROM exam_questions;
-- 예상: 180개 이상

SELECT DISTINCT year, exam_type, subject
FROM exam_questions
LIMIT 10;
```

## 🚀 단계별 테스트

### 단계 1: 백엔드 서버 실행

```powershell
# conda 환경 활성화
conda activate torch313

# 프로젝트 루트로 이동
cd C:\Users\hi\Desktop\private

# 백엔드 서버 실행
uvicorn backend.main:app --host localhost --port 8000 --reload
```

**예상 출력:**
```
INFO:     Uvicorn running on http://localhost:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Application startup complete.
```

### 단계 2: 백엔드 API 직접 테스트

**PowerShell에서 테스트:**

```powershell
# 테스트 요청
$body = @{
    question = "2025년 국가직 행정법총론 3번 알려줘"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/exam/flow" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

**예상 응답:**
```json
{
  "success": true,
  "answer": {
    "year": 2025,
    "exam_type": "국가직",
    "job_series": "일반행정직",
    "grade": "9급",
    "subject": "행정법총론",
    "question_no": 3,
    "answer_key": "3"
  },
  "method": "rule_based"
}
```

**로그 확인:**
백엔드 콘솔에서 다음 로그를 확인:

```
[ExamFlow] 게이트웨이 분류기 결과: gateway=RULE_BASED, confidence=0.95, label_id=0
[ExamFlow] 규칙 기반 처리로 라우팅 → exam_service
[ExamService] 엔티티 추출 완료: year=2025, exam_type=국가직, subject=행정법총론, question_no=3
[ExamService] DB 조회 성공: answer_key=3
```

### 단계 3: 프론트엔드 서버 실행

**새 터미널 창에서:**

```powershell
# 프론트엔드 디렉토리로 이동
cd C:\Users\hi\Desktop\private\frontend

# 개발 서버 실행
npm run dev
```

**예상 출력:**
```
  ▲ Next.js 14.x.x
  - Local:        http://localhost:3000
  - ready started server on 0.0.0.0:3000
```

### 단계 4: 프론트엔드에서 테스트

1. 브라우저에서 `http://localhost:3000` 접속
2. 챗봇 입력창에 다음 질문 입력:
   ```
   2025년 국가직 행정법총론 3번 알려줘
   ```
3. 전송 버튼 클릭

**예상 응답:**
```
2025년 국가직 9급 일반행정직 행정법총론 3번 정답은 3번입니다.
```

### 단계 5: 다양한 테스트 케이스

#### 테스트 케이스 1: RULE_BASED (규칙 기반)
```
입력: "2025년 지방직 회계학 5번 정답 뭐야?"
예상: 게이트웨이 → RULE_BASED → DB 조회 → 정답 반환
```

#### 테스트 케이스 2: POLICY_BASED (정책 기반)
```
입력: "신뢰보호의 원칙이 이 판례에서 왜 적용 안 돼?"
예상: 게이트웨이 → POLICY_BASED → exam_agent (LLM) → 설명 생성
```

#### 테스트 케이스 3: BLOCK (차단)
```
입력: "오늘 날씨 어때?"
예상: 게이트웨이 → BLOCK → 차단 메시지 반환
```

#### 테스트 케이스 4: 엔티티 부족
```
입력: "행정법 3번 알려줘"
예상: 게이트웨이 → RULE_BASED → 엔티티 부족 → 명확화 요청
```

## 🔍 디버깅

### 문제 1: 게이트웨이 분류기가 로드되지 않음

**증상:**
```
[Gateway Classifier] 모델 경로를 찾을 수 없어 기본값 반환
```

**해결:**
1. 모델 경로 확인:
   ```powershell
   Test-Path artifacts/lora-adapters/koelectra-gateway/run_20260122_154846
   ```
2. `.env` 파일에 경로 설정:
   ```bash
   KOELECTRA_GATEWAY_LORA_PATH=./artifacts/lora-adapters/koelectra-gateway/run_20260122_154846
   ```

### 문제 2: DB 조회 실패

**증상:**
```
과목명을 인식하지 못했습니다. (예: 회계학/행정법총론)
```

**해결:**
1. Neon DB에서 사용 가능한 과목 확인:
   ```sql
   SELECT DISTINCT subject FROM exam_questions ORDER BY subject;
   ```
2. 입력 질문의 과목명이 DB의 과목명과 정확히 일치하는지 확인

### 문제 3: 프론트엔드 연결 실패

**증상:**
```
백엔드 서버에 연결할 수 없습니다.
```

**해결:**
1. 백엔드 서버가 실행 중인지 확인 (`http://localhost:8000`)
2. 프론트엔드 `.env.local` 파일 확인:
   ```bash
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

## 📊 성능 확인

### 게이트웨이 분류기 성능

백엔드 로그에서 다음 정보 확인:
- **게이트웨이 분류 시간**: 보통 0.1~0.3초
- **신뢰도**: 0.8 이상이면 좋음
- **분류 정확도**: RULE_BASED/POLICY_BASED/BLOCK 구분 정확도

### 전체 응답 시간

- **RULE_BASED**: 0.5~1초 (DB 조회만)
- **POLICY_BASED**: 3~10초 (LLM 사용)

## ✅ 체크리스트

테스트 전 확인 사항:

- [ ] KoELECTRA 게이트웨이 분류기 모델 파일 존재
- [ ] Neon DB 연결 설정 완료
- [ ] `exam_questions` 테이블에 데이터 존재 (180개 이상)
- [ ] 백엔드 서버 실행 중 (`http://localhost:8000`)
- [ ] 프론트엔드 서버 실행 중 (`http://localhost:3000`)
- [ ] 환경 변수 설정 완료

테스트 완료 후 확인 사항:

- [ ] RULE_BASED 질문 → DB 조회 성공
- [ ] POLICY_BASED 질문 → LLM 응답 생성
- [ ] BLOCK 질문 → 차단 메시지 반환
- [ ] 엔티티 부족 시 명확화 요청
- [ ] 프론트엔드에 응답 정상 표시

## 🎯 다음 단계

1. **성능 최적화**
   - 게이트웨이 분류기 캐싱 확인
   - DB 쿼리 최적화
   - 응답 템플릿 개선

2. **에러 처리 개선**
   - 엔티티 파싱 실패 시 사용자 친화적 메시지
   - DB 조회 실패 시 대안 제시

3. **로깅 강화**
   - 각 단계별 상세 로그
   - 성능 메트릭 수집

