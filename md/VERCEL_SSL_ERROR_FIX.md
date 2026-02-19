# Vercel SSL 연결 오류 해결 가이드

## 🔍 오류 분석

**오류 메시지:**
```
[Next.js API] 백엔드 오류: {
  "detail": "서버 오류: consuming input failed: SSL connection has been closed unexpectedly"
}
```

**의미:**
- ✅ Vercel에서 EC2로 연결은 성공했습니다 (타임아웃 오류 해결됨)
- ❌ EC2 백엔드에서 데이터베이스(Neon DB) 연결 시 SSL 오류 발생
- ❌ SSL 연결이 예기치 않게 종료되었습니다

## 🚨 원인 분석

이 오류는 보통 다음 중 하나입니다:

1. **Neon DB SSL 설정 문제**
   - `DATABASE_URL`에 `?sslmode=require`가 없거나 잘못됨
   - SSL 인증서 문제

2. **데이터베이스 연결 풀 문제**
   - 연결이 너무 오래 유지되어 타임아웃
   - 연결 풀 설정 문제

3. **네트워크 불안정**
   - EC2와 Neon DB 간 네트워크 연결 불안정

## 🔧 해결 방법

### 해결 1: EC2 .env 파일 확인 (가장 중요!)

**EC2 SSH 접속 후:**

```bash
cd /home/ubuntu/rag
cat .env | grep DATABASE_URL
```

**확인할 내용:**
- `DATABASE_URL`이 올바른 형식인지
- `?sslmode=require`가 포함되어 있는지

**올바른 형식:**
```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=require
```

**문제가 있으면 수정:**
```bash
nano /home/ubuntu/rag/.env
```

다음과 같이 수정:
```env
# Neon DB URL (올바른 형식)
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=require

# 또는 더 안전한 SSL 설정
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=require&connect_timeout=10
```

**서비스 재시작:**
```bash
sudo systemctl restart rag-api.service
sudo systemctl status rag-api.service
```

### 해결 2: EC2 백엔드 로그 확인

**EC2에서:**
```bash
# 최근 로그 확인
sudo journalctl -u rag-api.service -n 100 --no-pager

# 실시간 로그 확인
sudo journalctl -u rag-api.service -f
```

**확인할 내용:**
- 데이터베이스 연결 오류 메시지
- SSL 관련 오류
- 연결 타임아웃 오류

### 해결 3: Neon DB 연결 테스트

**EC2에서 직접 테스트:**
```bash
# psql이 설치되어 있다면
psql "postgresql://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=require"

# 또는 Python으로 테스트
python3 -c "
import psycopg
conn = psycopg.connect('postgresql+psycopg://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=require')
print('연결 성공!')
conn.close()
"
```

### 해결 4: 데이터베이스 연결 설정 개선

**`backend/dependencies.py` 확인:**

연결 풀 설정이 있는지 확인하고, 필요시 타임아웃 및 재연결 로직 추가.

## ✅ 확인 체크리스트

- [ ] EC2 `.env` 파일의 `DATABASE_URL` 확인
- [ ] `DATABASE_URL`에 `?sslmode=require` 포함 확인
- [ ] Neon DB URL 형식이 올바른지 확인
- [ ] EC2 서비스 재시작 완료
- [ ] EC2 백엔드 로그 확인
- [ ] Neon DB 연결 직접 테스트

## 🧪 테스트 방법

### 1. EC2에서 데이터베이스 연결 테스트

```bash
# EC2 SSH 접속
ssh -i your-key.pem ubuntu@13.125.210.86

# .env 파일 확인
cd /home/ubuntu/rag
cat .env | grep DATABASE_URL

# 서비스 재시작
sudo systemctl restart rag-api.service

# 로그 확인
sudo journalctl -u rag-api.service -n 50 --no-pager
```

### 2. Vercel에서 다시 테스트

1. Vercel 사이트 접속
2. 챗봇에 메시지 전송
3. 오류가 해결되었는지 확인

## 📝 추가 확인 사항

### Neon DB 콘솔 확인

1. **Neon 콘솔** 접속
2. 프로젝트 선택
3. **Connection Details** 확인
4. 연결 문자열이 올바른지 확인

### SSL 인증서 문제

만약 SSL 인증서 문제라면:

```env
# 더 관대한 SSL 설정 (개발 환경용)
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=prefer
```

**주의:** 프로덕션에서는 `sslmode=require`를 사용하는 것이 안전합니다.

## 🆘 여전히 문제가 있으면

1. **Neon DB 상태 확인**
   - Neon 콘솔에서 데이터베이스 상태 확인
   - 연결 제한 확인

2. **EC2 네트워크 확인**
   - EC2에서 외부 연결 가능한지 확인
   - 방화벽 설정 확인

3. **연결 풀 설정 확인**
   - `backend/dependencies.py`에서 연결 풀 설정 확인
   - 타임아웃 설정 확인
