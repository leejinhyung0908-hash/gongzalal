# Vercel 500 오류 진단 가이드

## 🔍 현재 오류

**브라우저 콘솔:**
```
Failed to load resource: the server responded with a status of 500 ()
/api/chat:1
```

**의미:**
- Vercel의 Next.js API 라우트(`/api/chat`)에서 500 오류 발생
- EC2 백엔드로 요청을 보낼 때 오류 발생

## 🚨 가능한 원인

### 1. EC2 백엔드 오류

EC2에서 오류가 발생하여 500 응답을 반환할 수 있습니다.

**확인 방법:**
```bash
# EC2에서 최근 로그 확인
sudo journalctl -u rag-api.service -n 100 --no-pager

# 실시간 로그 확인
sudo journalctl -u rag-api.service -f
```

### 2. Vercel 함수 로그 확인

Vercel 대시보드에서:
1. 프로젝트 선택 → **Deployments** → 최신 배포 클릭
2. **Functions** 탭 또는 **Logs** 탭 확인
3. `/api/chat` 함수의 오류 메시지 확인

### 3. OpenAI API 키 문제

"OpenAI만" 모드에서 오류가 발생하는 경우:
- EC2의 `.env` 파일에 `OPENAI_API_KEY`가 설정되어 있는지 확인

**확인 방법:**
```bash
# EC2에서
cd /home/ubuntu/rag
cat .env | grep OPENAI_API_KEY
```

### 4. 네트워크 연결 문제

Vercel에서 EC2로의 연결이 실패할 수 있습니다.

**확인 방법:**
- Vercel 함수 로그에서 "백엔드 연결 실패" 메시지 확인

## 🔧 해결 방법

### 해결 1: EC2 로그 확인

EC2 SSH 접속 후:
```bash
# 최근 오류 확인
sudo journalctl -u rag-api.service -n 200 --no-pager | grep -i "error\|fail\|exception"

# 실시간 로그 확인
sudo journalctl -u rag-api.service -f
```

그 다음 Vercel 사이트에서 메시지를 보내면:
- 로그에 오류 메시지가 나타남
- 구체적인 오류 원인 확인 가능

### 해결 2: Vercel 함수 로그 확인

**Vercel 대시보드:**
1. 프로젝트 선택 → **Deployments** → 최신 배포 클릭
2. **Logs** 탭 또는 **Runtime Logs** 확인
3. 오류 메시지 확인

**또는 Vercel CLI:**
```bash
cd C:\Users\hi\Desktop\test3\rag
vercel logs --follow
```

### 해결 3: OpenAI API 키 확인

EC2에서:
```bash
cd /home/ubuntu/rag
cat .env | grep OPENAI_API_KEY
```

**없으면 추가:**
```bash
nano /home/ubuntu/rag/.env
```

다음 추가:
```env
OPENAI_API_KEY=your_openai_api_key_here
```

서비스 재시작:
```bash
sudo systemctl restart rag-api.service
```

### 해결 4: EC2 서비스 상태 확인

```bash
# 서비스 상태 확인
sudo systemctl status rag-api.service

# 헬스 체크
curl http://localhost:8000/health
```

## 📊 단계별 진단

### Step 1: Vercel 함수 로그 확인

Vercel 대시보드 또는 CLI로 로그 확인:
```bash
vercel logs --follow
```

**확인할 내용:**
- `[Next.js API] BACKEND_URL: ...` - 환경 변수 확인
- `[Next.js API] 백엔드 연결 실패: ...` - 네트워크 오류
- `[Next.js API] 백엔드 오류: ...` - EC2 서버 오류

### Step 2: EC2 로그 확인

```bash
# 실시간 로그 확인
sudo journalctl -u rag-api.service -f
```

Vercel 사이트에서 메시지를 보내면:
- 로그에 요청이 나타남
- 오류 메시지 확인 가능

### Step 3: OpenAI API 키 확인

"OpenAI만" 모드에서 오류가 발생하는 경우:
```bash
# EC2에서
cat /home/ubuntu/rag/.env | grep OPENAI_API_KEY
```

## ✅ 빠른 확인 체크리스트

- [ ] Vercel 함수 로그 확인 (`vercel logs --follow`)
- [ ] EC2 로그 확인 (`sudo journalctl -u rag-api.service -f`)
- [ ] EC2 OpenAI API 키 확인
- [ ] EC2 서비스 상태 확인
- [ ] EC2 헬스 체크 성공 확인

## 🆘 여전히 문제가 있으면

1. **Vercel 함수 로그 전체 확인**
   - Vercel 대시보드 → Deployments → Logs

2. **EC2 로그 전체 확인**
   ```bash
   sudo journalctl -u rag-api.service -n 500 --no-pager > /tmp/rag-api.log
   cat /tmp/rag-api.log
   ```

3. **다른 모드 테스트**
   - "RAG만" 모드 테스트
   - "RAG + OpenAI" 모드 테스트
