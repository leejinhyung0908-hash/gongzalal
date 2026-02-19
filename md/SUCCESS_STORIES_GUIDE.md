# 합격수기 데이터 크롤링 및 학습 데이터셋 생성 가이드

## 📋 개요

합격수기 데이터를 크롤링하여 학습 상담(ADVICE) 응답을 위한 ExaOne 모델 학습 데이터셋을 생성합니다.

## 🎯 목표

1. 합격수기 웹사이트에서 데이터 크롤링
2. 구조화된 데이터로 변환 (CSV, JSON)
3. 질문-답변 쌍 생성
4. ExaOne 학습용 JSONL 형식으로 변환
5. (선택사항) Neon DB에 저장

## 📊 데이터 구조

### 합격수기 원본 데이터

```json
{
  "exam_info": {
    "year": "2025",
    "exam_type": "국가직",
    "grade": "9급",
    "job_series": "보호직",
    "subjects": ["국어", "영어", "한국사", "형사정책개론", "사회복지학개론"]
  },
  "study_style": {
    "총 수험기간": "1년~1년 6개월",
    "평균 학습 시간": "8~10시간",
    "평균 회독수": "3~4회",
    "평균 문제집 권수": "3권"
  },
  "daily_plan": "하루 학습 계획...",
  "subject_methods": {
    "국어": "이선재 선생님 강의...",
    "영어": "..."
  },
  "interview_prep": "면접 준비 과정...",
  "difficulties": "어려웠던 점...",
  "key_points": "핵심 학습 전략..."
}
```

### 생성되는 질문-답변 쌍

#### 자연스러운 사용자 질문 패턴

```json
{
  "question": "일반행정직을 준비하는 데 보통 얼마나 걸려?",
  "answer": "[2025년, 국가직, 9급, 일반행정직 합격 선배의 조언]\n\n총 수험 기간은 1년~1년 6개월입니다.",
  "category": "study_period"
}
```

```json
{
  "question": "어떻게 공부해야 돼?",
  "answer": "[2025년, 국가직, 9급, 보호직 합격 선배의 조언]\n\n...",
  "category": "study_method"
}
```

```json
{
  "question": "보호직 9급 공무원 시험을 준비하는데, 국어 과목의 논리/추론 영역 공부법을 알려줘",
  "answer": "[2025년, 국가직, 9급, 보호직 합격 선배의 조언]\n\n국어 과목의 논리 영역은 다음과 같이 공부하시면 됩니다. 이선재 선생님의 강의를 추천합니다...",
  "category": "subject_method_detail"
}
```

## 🚀 사용 방법

### 1단계: 합격수기 데이터 크롤링

#### 방법 1: URL에서 크롤링

```bash
python backend/tools/crawl_success_stories.py \
  --url "https://example.com/success-story/123" \
  --output-dir data/success_stories \
  --format both
```

#### 방법 2: HTML 파일에서 크롤링

```bash
python backend/tools/crawl_success_stories.py \
  --file "data/success_stories/raw/success_story.html" \
  --output-dir data/success_stories \
  --format both
```

#### 방법 3: URL 목록 파일에서 크롤링

```bash
# urls.txt 파일 생성 (한 줄에 하나씩)
echo "https://example.com/success-story/1" > urls.txt
echo "https://example.com/success-story/2" >> urls.txt

python backend/tools/crawl_success_stories.py \
  --urls-file urls.txt \
  --output-dir data/success_stories \
  --format both
```

**출력 파일:**
- `data/success_stories/success_stories.json`: 원본 구조화 데이터
- `data/success_stories/success_stories.csv`: CSV 형식 데이터

### 2단계: 학습 데이터셋 생성

```bash
# 기본 (Chat + Instruction 형식 모두 생성)
python backend/tools/create_advice_dataset.py \
  --input data/success_stories/success_stories.json \
  --output-dir data/success_stories \
  --format both

# Chat 형식만 (messages)
python backend/tools/create_advice_dataset.py \
  --input data/success_stories/success_stories.json \
  --output-dir data/success_stories \
  --format chat

# Instruction 형식만 (instruction/input/output)
python backend/tools/create_advice_dataset.py \
  --input data/success_stories/success_stories.json \
  --output-dir data/success_stories \
  --format instruction
```

**출력 파일:**
- `data/success_stories/advice_dataset.csv`: 질문-답변 쌍 (CSV)
- `data/success_stories/advice_dataset.jsonl`: ExaOne 학습용 (통합)
- `data/success_stories/advice_dataset_chat.jsonl`: Chat 형식 (messages)
- `data/success_stories/advice_dataset_instruction.jsonl`: Instruction 형식

**Chat 형식 (ExaOne 학습용):**

```json
{
  "messages": [
    {
      "role": "user",
      "content": "일반행정직을 준비하는 데 보통 얼마나 걸려?"
    },
    {
      "role": "assistant",
      "content": "[2025년, 국가직, 9급, 일반행정직 합격 선배의 조언]\n\n총 수험 기간은 1년~1년 6개월입니다."
    }
  ],
  "category": "study_period",
  "exam_info": {
    "year": "2025",
    "exam_type": "국가직",
    "grade": "9급",
    "job_series": "일반행정직"
  }
}
```

**Instruction 형식 (SFT 학습용):**

```json
{
  "instruction": "보호직 9급 공무원 시험을 준비하는데, 국어 과목의 논리/추론 영역 공부법을 알려줘.",
  "input": "",
  "output": "[2025년, 국가직, 9급, 보호직 합격 선배의 조언]\n\n국어 과목의 논리 영역은 다음과 같이 공부하시면 됩니다. 이선재 선생님의 강의를 추천합니다. 처음에는 논리 문제가 어렵게 느껴질 수 있지만, 선생님의 커리큘럼을 믿고 따라가며 다양한 유형의 문제를 접하다 보면 실력이 느는 것을 느낄 수 있습니다. 특히 '매일국어' 자료를 주 3~4회 풀면서 감을 익히는 것이 중요합니다.",
  "category": "subject_method_detail",
  "exam_info": {
    "year": "2025",
    "exam_type": "국가직",
    "grade": "9급",
    "job_series": "보호직"
  }
}
```

### 3단계: (선택사항) Neon DB에 저장

#### 합격수기 원본 데이터 저장

```bash
python backend/tools/save_success_stories_to_db.py \
  --stories-json data/success_stories/success_stories.json \
  --database-url "postgresql+psycopg://..."
```

#### Q&A 데이터 저장

```bash
python backend/tools/save_success_stories_to_db.py \
  --qa-csv data/success_stories/advice_dataset.csv \
  --database-url "postgresql+psycopg://..."
```

또는 JSONL 파일에서:

```bash
python backend/tools/save_success_stories_to_db.py \
  --qa-jsonl data/success_stories/advice_dataset.jsonl \
  --database-url "postgresql+psycopg://..."
```

## 📊 생성되는 질문 카테고리

1. **study_period**: 수험 기간 관련 질문
   - 예: "일반행정직을 준비하는 데 보통 얼마나 걸려?"
   - 예: "평균적으로 합격하는데 걸리는 시간은?"

2. **study_hours**: 학습 시간 관련 질문
   - 예: "하루에 몇 시간씩 공부해야 해?"
   - 예: "평균적으로 하루에 몇 시간 공부했나요?"

3. **study_method**: 공부 방법 관련 질문
   - 예: "어떻게 공부해야 돼?"
   - 예: "공부 방법을 알려줘"

4. **subject_method**: 과목별 학습법 관련 질문
   - 예: "국어는 어떻게 공부해야 해?"
   - 예: "보호직 준비하는데 국어는 어떻게 공부했나요?"

5. **subject_method_detail**: 과목별 세부 영역 학습법
   - 예: "보호직 9급 공무원 시험을 준비하는데, 국어 과목의 논리/추론 영역 공부법을 알려줘"
   - 예: "국어 논리 영역은 어떻게 공부해야 해?"

6. **daily_plan**: 하루 학습 계획 관련 질문
7. **difficulties**: 어려웠던 점 관련 질문
8. **key_points**: 핵심 포인트 관련 질문
9. **interview_prep**: 면접 준비 관련 질문
10. **general_advice**: 종합 조언 질문

## 🗄️ DB 스키마

### success_stories 테이블

```sql
CREATE TABLE success_stories (
    id SERIAL PRIMARY KEY,
    year INTEGER,
    exam_type VARCHAR(50),
    grade VARCHAR(10),
    job_series VARCHAR(100),
    subjects TEXT[],
    study_period VARCHAR(100),
    study_hours VARCHAR(100),
    review_count VARCHAR(100),
    book_count VARCHAR(100),
    daily_plan TEXT,
    subject_methods JSONB,
    interview_prep TEXT,
    difficulties TEXT,
    key_points TEXT,
    raw_text TEXT,
    source_url TEXT,
    source_file TEXT,
    crawled_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### advice_qa 테이블

```sql
CREATE TABLE advice_qa (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category VARCHAR(50),
    year INTEGER,
    exam_type VARCHAR(50),
    grade VARCHAR(10),
    job_series VARCHAR(100),
    subjects TEXT[],
    embedding vector(768),  -- 벡터 검색용 (선택사항)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 💡 Neon DB 저장 여부 결정 가이드

### DB 저장이 필요한 경우

✅ **저장 권장:**
- 나중에 검색/필터링이 필요한 경우
- 벡터 검색으로 유사한 합격수기를 찾고 싶은 경우
- 실시간으로 합격수기 데이터를 조회해야 하는 경우
- 여러 애플리케이션에서 공유해야 하는 경우

### DB 저장이 불필요한 경우

❌ **저장 불필요:**
- 단순히 학습용 데이터셋만 필요한 경우
- CSV/JSONL 파일로 충분한 경우
- 정적 데이터로 한 번만 사용하는 경우

**결론:** 학습용 데이터셋만 필요하다면 CSV/JSONL로 충분합니다. DB 저장은 나중에 검색/조회가 필요할 때 추가하면 됩니다.

## 🔄 전체 워크플로우

```bash
# 1. 크롤링
python backend/tools/crawl_success_stories.py \
  --urls-file urls.txt \
  --output-dir data/success_stories

# 2. 데이터셋 생성
python backend/tools/create_advice_dataset.py \
  --input data/success_stories/success_stories.json \
  --output-dir data/success_stories

# 3. (선택) DB 저장
python backend/tools/save_success_stories_to_db.py \
  --stories-json data/success_stories/success_stories.json \
  --qa-jsonl data/success_stories/advice_dataset.jsonl

# 4. ExaOne 학습에 사용
# advice_dataset.jsonl 파일을 ExaOne 모델 학습에 사용
```

## 📝 참고사항

1. **크롤링 시 주의사항:**
   - 웹사이트의 robots.txt 확인
   - 서버 부하를 고려한 딜레이 설정 (기본 1초)
   - 저작권 및 이용약관 확인

2. **데이터 품질:**
   - 크롤링된 데이터는 수동 검토 권장
   - 불완전한 데이터는 제외

3. **학습 데이터셋 크기:**
   - 최소 100개 이상의 질문-답변 쌍 권장
   - 카테고리별 균형 있는 분포 권장

