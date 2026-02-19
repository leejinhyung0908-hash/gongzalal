# EXAONE + RAG 통합 테스트 가이드

학습된 EXAONE 모델과 Neon DB RAG가 정책 기반 질문(ADVICE)에 제대로 응답하는지 테스트하는 방법입니다.

## 🎯 테스트 목표

프론트엔드 챗봇에서 정책 기반 질문을 했을 때:
1. ✅ Neon DB에서 관련 합격 수기 검색 (RAG)
2. ✅ 학습된 EXAONE 모델로 응답 생성
3. ✅ 학습된 말투와 논리로 답변

## 🧪 테스트 방법

### 방법 1: Python 스크립트로 테스트

```bash
# 백엔드 환경에서 실행
cd backend
python ../test_exaone_rag_integration.py
```

### 방법 2: 프론트엔드에서 직접 테스트

1. **백엔드 서버 실행**
   ```bash
   cd backend
   python -m uvicorn main:app --reload --port 8000
   ```

2. **프론트엔드 실행**
   ```bash
   cd frontend
   npm run dev
   ```

3. **챗봇에서 테스트 질문 입력**

   다음 질문들을 입력해보세요:
   - "직장인인데 하루 4시간 공부로 합격 가능할까?"
   - "전업 수험생으로 공부하는데 하루 일과를 어떻게 구성해야 할까요?"
   - "국어 학습 전략이 궁금해요. 합격자들의 조언을 듣고 싶어요."
   - "영어 노베이스인데 어떻게 시작해야 할까요?"

## 🔍 작동 원리

### 1. 질문 분류

```
사용자 질문
    ↓
게이트웨이 분류 (KoELECTRA)
    ↓
POLICY_BASED로 분류
    ↓
의도 분류 (Intent Classifier)
    ↓
ADVICE 의도 감지
```

### 2. RAG 검색

```
ADVICE 의도 감지
    ↓
Neon DB 벡터 검색
    - 질문을 KURE-v1으로 embedding 생성
    - success_stories 테이블에서 유사도 검색
    - 상위 3개 합격 수기 반환
```

### 3. EXAONE 응답 생성

```
RAG 결과 + 사용자 질문
    ↓
학습된 EXAONE 모델 (LoRA 어댑터)
    ↓
합격 수기 기반 답변 생성
    - 학습된 말투 사용
    - Chain-of-Thought 방식으로 답변
    - 따뜻하고 전문적인 어조
```

## 📝 예상 응답 예시

**질문**: "직장인인데 하루 4시간 공부로 합격 가능할까?"

**예상 응답**:
```
물론 가능합니다! 직장인 수험생 여러분, 시간이 생명입니다!
합격하신 선배님들의 조언을 들려드릴게요.

[합격 수기 1]
- 출처: megagong
- 시험 정보: 2024년 지방직 9급 세무직
- 핵심 포인트: 저를 합격으로 이끈 핵심 학습 전략은 '꾸준함'이었습니다.
  공무원 시험은 결국 암기력과 반복력의 싸움이라고 생각하기 때문에,
  흔들리지 않고 매일 일정한 순공시간을 유지하는 것이 가장 중요했습니다.

직장인이라면 퇴근 후 시간을 어떻게 활용하느냐가 합격을 좌우합니다.
오늘부터 바로 시작해보시는 건 어떨까요?
```

## ⚙️ 설정 확인

### 1. 환경 변수 확인

`.env` 파일에 다음이 설정되어 있어야 합니다:

```env
# Neon DB 연결
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=require

# EXAONE LoRA 어댑터 경로 (선택사항)
EXAONE_SUCCESS_STORIES_LORA_PATH=artifacts/lora-adapters/exaone-success-stories
```

### 2. 모델 파일 확인

다음 파일들이 존재해야 합니다:

```
artifacts/
├── base-models/
│   └── exaone/          # EXAONE 베이스 모델
└── lora-adapters/
    └── exaone-success-stories/  # 학습된 LoRA 어댑터
        ├── adapter_config.json
        ├── adapter_model.bin
        └── ...
```

### 3. Neon DB 데이터 확인

Neon DB에 합격 수기 데이터가 저장되어 있어야 합니다:

```sql
SELECT COUNT(*) FROM success_stories;
-- gongdanki와 megagong 데이터가 있어야 함
```

## 🐛 문제 해결

### 문제 1: "관련 합격 수기를 찾지 못했습니다"

**원인**: Neon DB에 데이터가 없거나 embedding이 생성되지 않음

**해결**:
```bash
# embedding 생성 스크립트 실행
conda activate torch313
python create_embeddings_for_neon.py
```

### 문제 2: "LoRA 어댑터 경로를 찾을 수 없습니다"

**원인**: 학습된 LoRA 어댑터가 없음

**해결**:
- 학습이 완료되었는지 확인
- `artifacts/lora-adapters/exaone-success-stories/` 경로 확인
- 환경 변수 `EXAONE_SUCCESS_STORIES_LORA_PATH` 설정

### 문제 3: 응답이 느림

**원인**: 모델 로드 시간 또는 GPU 메모리 부족

**해결**:
- 첫 요청 시 모델 로드 시간 필요 (약 30-60초)
- 이후 요청은 캐시된 모델 사용
- GPU 메모리 확인: `nvidia-smi`

## ✅ 성공 확인 체크리스트

- [ ] Neon DB에서 합격 수기 검색 성공
- [ ] EXAONE 모델 로드 성공
- [ ] LoRA 어댑터 로드 성공
- [ ] 응답이 학습된 말투로 생성됨
- [ ] 합격 수기 내용이 응답에 포함됨
- [ ] 프론트엔드에서 정상적으로 표시됨

## 📊 로그 확인

백엔드 서버 로그에서 다음을 확인할 수 있습니다:

```
[SuccessStoriesRAG] KURE-v1 모델 로딩 중...
[SuccessStoriesRAG] KURE-v1 모델 로딩 완료
[ExaoneLLM] 모델 로드 시작: artifacts/base-models/exaone
[ExaoneLLM] LoRA 어댑터 로드 시작: artifacts/lora-adapters/exaone-success-stories
[ExaoneLLM] LoRA 어댑터 로드 완료
[ExamAgent] ADVICE 의도 감지 → RAG + EXAONE 사용
```

