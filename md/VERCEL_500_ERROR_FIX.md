# Vercel 500 오류 해결 가이드

## 🔍 문제 진단

콘솔에 `/api/chat`에서 **500 Internal Server Error**가 발생하고 있습니다.

이는 Next.js API 라우트(`frontend/app/api/chat/route.ts`)에서 백엔드로 요청을 보낼 때 오류가 발생하는 것을 의미합니다.

## 🚨 즉시 확인할 사항

### 1. Vercel 환경 변수 확인

**Vercel 대시보드:**
1. 프로젝트 선택 → **Settings** → **Environment Variables**
2. `BACKEND_URL`이 설정되어 있는지 확인
3. 값이 올바른지 확인 (예: `http://YOUR_EC2_IP:8000`)

**중요:** 환경 변수 설정 후 **반드시 Redeploy** 해야 합니다!

### 2. Vercel 함수 로그 확인

**Vercel 대시보드에서:**
1. 프로젝트 선택 → **Deployments** → 최신 배포 클릭
2. **Functions** 탭 클릭
3. `/api/chat` 함수 클릭
4. **Logs** 탭에서 오류 메시지 확인

**확인할 로그:**
- `[Next.js API] BACKEND_URL: ...` - 환경 변수가 올바르게 로드되었는지
- `[Next.js API] 백엔드 연결 실패: ...` - 네트워크 연결 오류
- `[Next.js API] 백엔드 오류: ...` - 백엔드 서버 오류

### 3. EC2 백엔드 상태 확인

**EC2 SSH 접속 후:**
```bash
# 서비스 상태 확인
sudo systemctl status rag-api.service

# 헬스 체크
curl http://localhost:8000/health

# 로그 확인
sudo journalctl -u rag-api.service -n 50 --no-pager
```

### 4. EC2 외부 접근 테스트

**로컬 컴퓨터에서 (Windows PowerShell):**
```powershell
# EC2 IP를 실제 IP로 변경
curl http://YOUR_EC2_IP:8000/health

# 또는
Invoke-WebRequest -Uri "http://YOUR_EC2_IP:8000/health" -Method GET
```

**예상 응답:**
```json
{"status":"healthy","database":"connected"}
```

## 🔧 해결 방법

### 해결 1: 환경 변수 설정 및 Redeploy

1. **Vercel 대시보드** → **Settings** → **Environment Variables**
2. 다음 변수 추가:
   ```
   BACKEND_URL=http://YOUR_EC2_IP:8000
   NEXT_PUBLIC_BACKEND_URL=http://YOUR_EC2_IP:8000
   ```
3. **Deployments** → 최신 배포 → **Redeploy** 클릭
4. 배포 완료 대기 (1-3분)

### 해결 2: EC2 백엔드 시작

```bash
# EC2 SSH 접속
ssh -i your-key.pem ubuntu@YOUR_EC2_IP

# 서비스 시작
sudo systemctl start rag-api.service
sudo systemctl enable rag-api.service

# 상태 확인
sudo systemctl status rag-api.service
```

### 해결 3: EC2 보안 그룹 확인

**AWS 콘솔:**
1. EC2 → 인스턴스 선택
2. **보안** 탭 → **보안 그룹** 클릭
3. **인바운드 규칙** 확인:
   - 포트 `8000`이 열려있는지
   - 소스: `0.0.0.0/0` (또는 특정 IP)

**규칙이 없으면 추가:**
- 유형: `사용자 지정 TCP`
- 포트: `8000`
- 소스: `0.0.0.0/0`

### 해결 4: CORS 설정 확인

**EC2에서:**
```bash
cd /home/ubuntu/rag
nano .env
```

다음 추가/수정:
```env
CORS_ORIGINS=https://rag-nine-cyan.vercel.app,https://rag-nine-cyan-*.vercel.app,http://localhost:3000
```

서비스 재시작:
```bash
sudo systemctl restart rag-api.service
```

## 📊 오류 유형별 해결

### 오류: "백엔드 서버에 연결할 수 없습니다" (503)

**원인:**
- `BACKEND_URL`이 설정되지 않음
- EC2 백엔드가 실행되지 않음
- EC2 보안 그룹에서 포트 8000이 닫혀있음
- 네트워크 연결 문제

**해결:**
1. Vercel 환경 변수 확인
2. EC2 서비스 상태 확인
3. EC2 보안 그룹 확인
4. 외부에서 EC2 접근 테스트

### 오류: "백엔드 서버에서 오류가 발생했습니다" (500)

**원인:**
- EC2 백엔드에서 내부 오류 발생
- 데이터베이스 연결 실패
- 모델 로딩 실패

**해결:**
1. EC2 로그 확인: `sudo journalctl -u rag-api.service -n 100`
2. 데이터베이스 연결 확인
3. 백엔드 코드 오류 확인

### 오류: 타임아웃

**원인:**
- EC2 백엔드 응답이 너무 느림
- 네트워크 지연

**해결:**
1. EC2 인스턴스 상태 확인
2. 백엔드 로그에서 느린 쿼리 확인
3. 타임아웃 시간 조정 (현재 30초)

## 🔍 디버깅 단계

### Step 1: Vercel 함수 로그 확인

1. Vercel 대시보드 → Deployments → Functions → `/api/chat` → Logs
2. 오류 메시지 확인
3. `BACKEND_URL` 값 확인

### Step 2: EC2 백엔드 직접 테스트

```bash
# EC2에서
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"테스트","mode":"rag_openai"}'
```

### Step 3: 외부에서 EC2 테스트

```powershell
# Windows PowerShell
$body = @{
    question = "테스트"
    mode = "rag_openai"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://YOUR_EC2_IP:8000/api/v1/chat" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

## ✅ 체크리스트

- [ ] Vercel 환경 변수 `BACKEND_URL` 설정 확인
- [ ] Vercel Redeploy 실행
- [ ] Vercel 함수 로그 확인
- [ ] EC2 서비스 실행 중 확인
- [ ] EC2 헬스 체크 성공 확인
- [ ] EC2 외부 접근 가능 확인
- [ ] EC2 보안 그룹 포트 8000 열림 확인
- [ ] EC2 CORS 설정 확인
- [ ] 브라우저에서 다시 테스트

## 📝 개선된 에러 로깅

코드에 더 자세한 로깅을 추가했습니다. 이제 Vercel 함수 로그에서:
- `BACKEND_URL` 값 확인 가능
- 요청 URL 확인 가능
- 응답 상태 확인 가능
- 구체적인 오류 메시지 확인 가능

이 정보를 통해 정확한 원인을 파악할 수 있습니다.
