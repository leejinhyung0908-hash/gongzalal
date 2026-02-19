# EC2 .env 파일 확인 가이드

## 🔍 .env 파일 확인 방법

### 방법 1: 전체 내용 확인

EC2 SSH 접속 후:
```bash
cd /home/ubuntu/rag
cat .env
```

### 방법 2: 특정 변수만 확인

```bash
# DATABASE_URL 확인
cat /home/ubuntu/rag/.env | grep DATABASE_URL

# OPENAI_API_KEY 확인 (값은 마스킹됨)
cat /home/ubuntu/rag/.env | grep OPENAI_API_KEY

# CORS_ORIGINS 확인
cat /home/ubuntu/rag/.env | grep CORS_ORIGINS

# 모든 환경 변수 확인
cat /home/ubuntu/rag/.env
```

### 방법 3: 파일 편집기로 확인

```bash
cd /home/ubuntu/rag
nano .env
# 또는
vim .env
```

**nano 사용법:**
- 파일 확인 후 `Ctrl+X`로 종료
- 수정하려면 내용 변경 후 `Ctrl+O`로 저장, `Ctrl+X`로 종료

## 📝 확인할 주요 환경 변수

### 필수 변수

```bash
# 데이터베이스 URL
cat /home/ubuntu/rag/.env | grep DATABASE_URL

# OpenAI API 키
cat /home/ubuntu/rag/.env | grep OPENAI_API_KEY

# CORS 설정
cat /home/ubuntu/rag/.env | grep CORS_ORIGINS
```

### 선택적 변수

```bash
# 모델 경로
cat /home/ubuntu/rag/.env | grep MODEL_BASE_PATH

# 서버 설정
cat /home/ubuntu/rag/.env | grep -E "HOST|PORT"
```

## 🔧 .env 파일 수정 방법

### nano 편집기 사용

```bash
cd /home/ubuntu/rag
nano .env
```

**편집 후:**
1. `Ctrl+O` - 저장
2. `Enter` - 파일명 확인
3. `Ctrl+X` - 종료

### 수정 후 서비스 재시작

```bash
sudo systemctl restart rag-api.service
sudo systemctl status rag-api.service
```

## 📋 .env 파일 예시

```env
# 데이터베이스 설정
DATABASE_URL=postgresql+psycopg://neondb_owner:npg_5gUtKvmle0MI@ep-restless-surf-a1aft67h-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require

# OpenAI 설정
OPENAI_API_KEY=sk-...

# CORS 설정
CORS_ORIGINS=https://rag-nine-cyan.vercel.app,https://rag-nine-cyan-*.vercel.app,http://localhost:3000
```

## ⚠️ 주의사항

1. **비밀번호/키 노출 주의**
   - `.env` 파일에는 민감한 정보가 포함되어 있습니다
   - 스크린샷이나 로그에 노출되지 않도록 주의하세요

2. **파일 권한 확인**
   ```bash
   ls -la /home/ubuntu/rag/.env
   ```
   - 권한이 `600` (소유자만 읽기/쓰기)인 것이 좋습니다

3. **백업**
   - 수정 전에 백업하는 것을 권장합니다
   ```bash
   cp /home/ubuntu/rag/.env /home/ubuntu/rag/.env.backup
   ```
