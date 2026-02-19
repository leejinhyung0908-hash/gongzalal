# Neon DB에 Embedding 저장하기

합격 수기 데이터(`success_stories.json`, `megagong_stories.json`)를 Neon DB에 저장하고 embedding을 생성하는 가이드입니다.

## 📋 목적

- **EXAONE 학습용 (JSONL)**: 말투와 논리를 배우는 교과서 → 이미 생성 완료
- **Neon DB 저장용**: 정확한 근거를 찾는 도서관 → 이 가이드에서 진행

## 🔧 사전 준비

### 1. Conda 환경 활성화

```bash
conda activate torch313
```

### 2. 필요한 패키지 설치

**torch313 환경에는 이미 PyTorch가 설치되어 있으므로, sentence-transformers만 추가 설치하면 됩니다:**

```bash
pip install sentence-transformers
```

**또는 requirements 파일 사용:**

```bash
pip install -r requirements_embeddings.txt
```

**참고:** torch313 환경에는 이미 다음이 설치되어 있습니다:
- ✅ PyTorch 2.9.1+cu126 (CUDA 지원)
- ✅ psycopg
- ✅ pgvector
- ✅ python-dotenv

### 2. 환경 변수 설정

`.env` 파일을 생성하거나 수정:

```env
# Neon DB 연결 URL
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=require
```

**Neon DB URL 형식:**
- Neon 콘솔에서 Connection String 복사
- `postgresql://` → `postgresql+psycopg://`로 변경
- 예: `postgresql+psycopg://user:pass@ep-xxx.neon.tech/dbname?sslmode=require`

### 3. Embedding 모델

**KURE-v1** (`nlpai-lab/KURE-v1`) 모델을 사용합니다.
- 한국어에 특화된 embedding 모델
- 1024차원 벡터 생성
- 로컬에서 실행 (API 비용 없음)
- Hugging Face에서 자동 다운로드
- GPU 사용 시 더 빠른 처리

## 🚀 실행 방법

```bash
# 1. conda 환경 활성화
conda activate torch313

# 2. 스크립트 실행
python create_embeddings_for_neon.py
```

**참고:** GPU가 있으면 자동으로 사용하여 더 빠르게 처리됩니다.

## 📊 데이터베이스 스키마

스크립트가 자동으로 다음 테이블을 생성합니다:

```sql
CREATE TABLE success_stories (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,  -- 'gongdanki' or 'megagong'
    story_id INTEGER,  -- 원본 JSON의 인덱스
    exam_info JSONB,  -- 시험 정보
    study_style JSONB,  -- 수험생활 스타일
    daily_plan TEXT,
    subject_methods JSONB,
    interview_prep TEXT,
    difficulties TEXT,
    key_points TEXT,
    raw_text TEXT,  -- 원본 텍스트
    search_text TEXT,  -- 검색용 텍스트
    embedding vector(1024),  -- KURE-v1은 1024차원
    source_url TEXT,
    crawled_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🔍 검색 예시

Neon DB에 저장된 데이터를 벡터 검색으로 찾는 예시:

```python
import psycopg
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

# KURE-v1 모델 로드
model = SentenceTransformer('nlpai-lab/KURE-v1')

# Embedding 생성
query_embedding = model.encode("직장인 수험생 일일 계획", normalize_embeddings=True).tolist()

# 벡터 검색
conn = psycopg.connect(DATABASE_URL)
register_vector(conn)
cur = conn.cursor()

cur.execute("""
    SELECT
        source,
        exam_info->>'job_series' as job_series,
        daily_plan,
        search_text,
        1 - (embedding <=> %s::vector) as similarity
    FROM success_stories
    ORDER BY embedding <=> %s::vector
    LIMIT 5
""", (query_embedding, query_embedding))

results = cur.fetchall()
for row in results:
    print(f"유사도: {row[4]:.3f}, 직렬: {row[1]}")
    print(f"내용: {row[2][:100]}...")
    print()
```

## ⚙️ 다른 Embedding 모델 사용하기

현재는 **KURE-v1** 모델을 사용하고 있습니다. 다른 모델로 변경하려면 `create_embeddings_for_neon.py`의 `create_embedding` 함수를 수정하세요.

### OpenAI Embedding 사용

```python
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def create_embedding(text: str) -> List[float]:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding
```

**주의:** 테이블의 `embedding vector(768)` 부분을 모델의 차원에 맞게 수정해야 합니다 (OpenAI는 1536차원).

### EXAONE Embedding 사용

EXAONE API를 사용하는 경우:

```python
# EXAONE API 예시 (실제 API는 문서 참조)
import requests

def create_embedding(text: str) -> List[float]:
    response = requests.post(
        "https://api.exaone.com/v1/embeddings",
        headers={"Authorization": f"Bearer {EXAONE_API_KEY}"},
        json={"text": text, "model": "exaone-embedding"}
    )
    return response.json()["embedding"]
```

## 📝 처리 과정

1. **텍스트 변환**: JSON의 구조화된 필드들을 검색 가능한 텍스트로 변환
2. **Embedding 생성**: 텍스트를 벡터로 변환 (OpenAI API 사용)
3. **DB 저장**: 원문 JSON + embedding 벡터를 Neon DB에 저장
4. **인덱싱**: 벡터 검색을 위한 인덱스 자동 생성

## ⚠️ 주의사항

1. **처리 시간**:
   - KURE-v1은 로컬에서 실행되므로 첫 실행 시 모델 다운로드 시간이 필요합니다
   - 대량 데이터는 시간이 걸릴 수 있음 (GPU 사용 시 더 빠름)

2. **텍스트 길이**:
   - KURE-v1은 최대 512 토큰 제한
   - 스크립트에서 자동으로 잘라냄 (2000자, 안전하게 설정)

3. **메모리 사용량**:
   - KURE-v1 모델은 약 400MB 메모리 사용
   - GPU가 있으면 자동으로 사용 (더 빠름)

## 🐛 문제 해결

### "DATABASE_URL 환경 변수가 설정되지 않았습니다"
- `.env` 파일에 `DATABASE_URL` 추가 확인

### "KURE-v1 모델 로딩 실패"
- 인터넷 연결 확인 (첫 실행 시 Hugging Face에서 모델 다운로드)
- `sentence-transformers`와 `torch` 패키지 설치 확인
- GPU 메모리 부족 시 CPU 모드로 자동 전환됨

### "pgvector 확장 오류"
- Neon DB는 pgvector를 자동 지원하지만, 수동으로 활성화 필요할 수 있음
- Neon 콘솔에서 SQL Editor로 `CREATE EXTENSION vector;` 실행

### "벡터 차원 불일치"
- KURE-v1은 1024차원을 사용합니다
- 테이블이 이미 다른 차원으로 생성된 경우:
  ```sql
  ALTER TABLE success_stories ALTER COLUMN embedding TYPE vector(1024);
  ```

## 📚 참고 자료

- [Neon DB 문서](https://neon.tech/docs)
- [pgvector 문서](https://github.com/pgvector/pgvector)
- [KURE-v1 모델 (Hugging Face)](https://huggingface.co/nlpai-lab/KURE-v1)
- [Sentence Transformers 문서](https://www.sbert.net/)

