# 메가공 합격수기 데이터 처리 가이드

메가공 합격수기 데이터를 크롤링하고 학습 데이터셋을 생성하는 가이드입니다.

## 파일 구조

```
backend/tools/
├── crawl_megagong_stories.py          # 메가공 크롤러
└── create_megagong_advice_dataset.py  # 메가공 데이터셋 생성기

data/success_stories/megagong/
├── megagong_stories.json              # 크롤링된 원본 데이터 (JSON)
├── megagong_stories.csv               # 크롤링된 원본 데이터 (CSV)
├── megagong_advice_dataset.csv        # 생성된 질문-답변 쌍 (CSV)
├── megagong_advice_dataset.jsonl     # ExaOne 학습용 (통합)
├── megagong_advice_dataset_chat.jsonl      # ExaOne 학습용 (Chat 형식)
└── megagong_advice_dataset_instruction.jsonl  # ExaOne 학습용 (Instruction 형식)
```

## 사용 방법

### 1. JSON/CSV 파일에서 데이터 로드 및 처리

메가공에서 크롤링한 JSON 또는 CSV 파일이 있는 경우:

```bash
# JSON 파일에서 로드
python backend/tools/crawl_megagong_stories.py \
  --input-json data/success_stories/megagong/your_stories.json \
  --output-dir data/success_stories/megagong \
  --format both

# CSV 파일에서 로드
python backend/tools/crawl_megagong_stories.py \
  --input-csv data/success_stories/megagong/your_stories.csv \
  --output-dir data/success_stories/megagong \
  --format both
```

### 2. URL에서 직접 크롤링

```bash
# 단일 URL 크롤링
python backend/tools/crawl_megagong_stories.py \
  --url "https://lab.megagong.net/l/gong/pass_opinion/view.asp?idx=33466" \
  --output-dir data/success_stories/megagong \
  --format both

# URL 목록 파일에서 크롤링
python backend/tools/crawl_megagong_stories.py \
  --urls-file data/success_stories/megagong/urls.txt \
  --output-dir data/success_stories/megagong \
  --format both
```

### 3. 학습 데이터셋 생성

크롤링된 데이터나 기존 JSON/CSV 파일에서 학습 데이터셋 생성:

```bash
# JSON 파일에서 생성
python backend/tools/create_megagong_advice_dataset.py \
  --input data/success_stories/megagong/megagong_stories.json \
  --output-dir data/success_stories/megagong \
  --format both

# CSV 파일에서 생성
python backend/tools/create_megagong_advice_dataset.py \
  --input data/success_stories/megagong/megagong_stories.csv \
  --output-dir data/success_stories/megagong \
  --format both
```

## 데이터 형식

### 입력 데이터 형식 (JSON)

```json
[
  {
    "exam_info": {
      "year": "2024",
      "exam_type": "지방직",
      "grade": "9",
      "job_series": "일반행정직",
      "subjects": ["국어", "영어", "한국사", "행정법", "행정학"],
      "총 수험기간": "2년 3개월",
      "하루 평균 학습 시간": "10시간"
    },
    "study_style": {
      "수험생활": "100% 순공시간 확보",
      "평균 회독수": "3~4회",
      "정신력": "긍정적 마인드"
    },
    "daily_plan": "하루 학습 계획...",
    "subject_methods": {
      "국어": "국어 학습법...",
      "영어": "영어 학습법...",
      "한국사": "한국사 학습법..."
    },
    "interview_prep": "면접 준비 과정...",
    "difficulties": "어려웠던 점...",
    "key_points": "핵심 포인트..."
  }
]
```

### 출력 데이터 형식 (JSONL - Instruction)

```json
{
  "instruction": "일반행정직을 준비하는 데 보통 얼마나 걸려?",
  "input": "",
  "output": "[2024년, 지방직, 9급, 일반행정직 합격 선배의 조언]\n\n총 수험 기간은 2년 3개월입니다.",
  "category": "study_period",
  "exam_info": {
    "year": "2024",
    "exam_type": "지방직",
    "grade": "9",
    "job_series": "일반행정직"
  }
}
```

### 출력 데이터 형식 (JSONL - Chat)

```json
{
  "messages": [
    {
      "role": "user",
      "content": "일반행정직을 준비하는 데 보통 얼마나 걸려?"
    },
    {
      "role": "assistant",
      "content": "[2024년, 지방직, 9급, 일반행정직 합격 선배의 조언]\n\n총 수험 기간은 2년 3개월입니다."
    }
  ],
  "category": "study_period",
  "exam_info": {...}
}
```

## 생성되는 질문 카테고리

1. **study_period**: 수험 기간 관련 질문
2. **study_hours**: 학습 시간 관련 질문
3. **daily_plan**: 하루 학습 계획 관련 질문
4. **subject_method**: 과목별 학습법 관련 질문
5. **subject_method_detail**: 과목별 세부 영역 학습법 질문
6. **difficulties**: 어려웠던 점 관련 질문
7. **key_points**: 핵심 포인트 관련 질문
8. **interview_prep**: 면접 준비 관련 질문
9. **general_advice**: 종합 조언 질문

## ExaOne 학습용 데이터

생성된 JSONL 파일은 ExaOne 모델 학습에 바로 사용할 수 있습니다:

- **megagong_advice_dataset_instruction.jsonl**: Instruction 형식 (SFT 학습용)
- **megagong_advice_dataset_chat.jsonl**: Chat 형식 (대화형 학습용)

## 주의사항

1. 메가공 페이지 구조는 공단기와 다르므로 별도의 크롤러를 사용합니다.
2. CSV 파일에서 로드할 때는 `subject_methods` 필드가 JSON 문자열 형식이어야 합니다.
3. 크롤링 시 서버 부하를 방지하기 위해 URL 간 1초 딜레이가 있습니다.

