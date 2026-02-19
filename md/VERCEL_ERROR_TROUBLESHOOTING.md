# Vercel 응답 오류 해결 가이드

## 문제 진단 단계

### 1단계: Vercel 환경 변수 확인

**Vercel 대시보드에서 확인:**

1. **Vercel 대시보드** → **프로젝트 선택** → **Settings** → **Environment Variables**

2. 다음 변수가 **반드시** 설정되어 있어야 합니다:
   ```
   BACKEND_URL=http://YOUR_EC2_IP:8000
   NEXT_PUBLIC_BACKEND_URL=http://YOUR_EC2_IP:8000
   ```

3. **중요 확인사항:**
   - ✅ 변수 이름이 정확한지 확인 (`BACKEND_URL`, `NEXT_PUBLIC_BACKEND_URL`)
   - ✅ EC2 IP 주소가 실제 IP로 설정되어 있는지 확인
   - ✅ 환경(Production, Preview, Development) 모두에 설정되어 있는지 확인

4. **환경 변수 수정 후 반드시 재배포:**
   - Vercel 대시보드 → **Deployments** → 최신 배포 → **Redeploy** 클릭

### 2단계: EC2 백엔드 상태 확인

**EC2에 SSH 접속하여 확인:**

```bash
# 1. 서비스 상태 확인
sudo systemctl status rag-api.service

# 2. 서비스가 실행 중이 아니면 시작
sudo systemctl start rag-api.service

# 3. 로그 확인 (오류 확인)
sudo journalctl -u rag-api.service -n 50 --no-pager

# 4. 백엔드 헬스 체크
curl http://localhost:8000/health

# 5. 외부에서 접근 가능한지 확인 (EC2 퍼블릭 IP 사용)
curl http://YOUR_EC2_IP:8000/health
```

**예상 응답:**
```json
{"status":"healthy","database":"connected"}
```

### 3단계: EC2 보안 그룹 확인

**AWS 콘솔에서 확인:**

1. **EC2 콘솔** → **인스턴스** → 인스턴스 선택
2. **보안** 탭 → **보안 그룹** 클릭
3. **인바운드 규칙** 확인:
   - 포트 `8000`이 열려있는지 확인
   - 소스: `0.0.0.0/0` (또는 특정 IP)

**규칙이 없으면 추가:**
- 유형: `사용자 지정 TCP`
- 포트: `8000`
- 소스: `0.0.0.0/0` (또는 Vercel IP 범위)

### 4단계: CORS 설정 확인

**EC2에서 `.env` 파일 확인:**

```bash
cd /home/ubuntu/rag
cat .env | grep CORS_ORIGINS
```

**다음과 같이 설정되어 있어야 합니다:**
```env
CORS_ORIGINS=https://rag-nine-cyan.vercel.app,https://rag-nine-cyan-*.vercel.app,http://localhost:3000
```

**설정 후 서비스 재시작:**
```bash
sudo systemctl restart rag-api.service
```

### 5단계: 브라우저 개발자 도구로 오류 확인

**Vercel 사이트에서:**

1. 브라우저 개발자 도구 열기 (F12)
2. **Console** 탭에서 오류 메시지 확인
3. **Network** 탭에서:
   - `/api/chat` 요청 확인
   - 요청 상태 코드 확인 (200, 500, 등)
   - 응답 내용 확인

**확인할 오류 유형:**
- `CORS policy`: CORS 설정 문제
- `Failed to fetch`: 네트워크 연결 문제
- `500 Internal Server Error`: 서버 오류
- `404 Not Found`: 엔드포인트 경로 문제

### 6단계: Vercel 함수 로그 확인

**Vercel 대시보드에서:**

1. **프로젝트** → **Deployments** → 최신 배포 클릭
2. **Functions** 탭 클릭
3. `/api/chat` 함수 로그 확인
4. 오류 메시지 확인

## 일반적인 문제와 해결 방법

### 문제 1: 환경 변수가 설정되지 않음

**증상:**
- 모든 요청이 실패
- Vercel 함수 로그에 `BACKEND_URL`이 `undefined` 또는 `http://localhost:8000`

**해결:**
1. Vercel 대시보드에서 환경 변수 추가
2. **Redeploy** 실행

### 문제 2: EC2 백엔드가 실행되지 않음

**증상:**
- `Failed to fetch` 오류
- EC2에서 `curl http://localhost:8000/health` 실패

**해결:**
```bash
# EC2에서
sudo systemctl start rag-api.service
sudo systemctl enable rag-api.service
sudo systemctl status rag-api.service
```

### 문제 3: CORS 오류

**증상:**
- 브라우저 콘솔에 `CORS policy` 오류
- `Access-Control-Allow-Origin` 관련 오류

**해결:**
1. EC2 `.env` 파일에 Vercel 도메인 추가
2. 서비스 재시작

### 문제 4: 보안 그룹 포트 미개방

**증상:**
- `Connection refused` 또는 타임아웃
- EC2 내부에서는 작동하지만 외부에서 접근 불가

**해결:**
1. AWS 콘솔에서 보안 그룹 인바운드 규칙 추가
2. 포트 8000 열기

### 문제 5: 네트워크 타임아웃

**증상:**
- 요청이 오래 걸리다가 타임아웃
- `ETIMEDOUT` 오류

**해결:**
1. EC2 인스턴스 상태 확인
2. 네트워크 연결 확인
3. 백엔드 응답 시간 확인 (로그 확인)

## 빠른 진단 체크리스트

- [ ] Vercel 환경 변수 `BACKEND_URL` 설정 확인
- [ ] Vercel 환경 변수 `NEXT_PUBLIC_BACKEND_URL` 설정 확인
- [ ] 환경 변수 설정 후 Redeploy 실행
- [ ] EC2 서비스 실행 상태 확인 (`systemctl status`)
- [ ] EC2 헬스 체크 성공 확인 (`curl http://localhost:8000/health`)
- [ ] EC2 외부 접근 가능 확인 (`curl http://EC2_IP:8000/health`)
- [ ] EC2 보안 그룹 포트 8000 열림 확인
- [ ] EC2 `.env` 파일에 CORS_ORIGINS 설정 확인
- [ ] 브라우저 개발자 도구에서 오류 확인
- [ ] Vercel 함수 로그 확인

## 테스트 명령어

### 로컬에서 EC2 백엔드 테스트

```bash
# Windows PowerShell에서
curl http://YOUR_EC2_IP:8000/health

# 또는
Invoke-WebRequest -Uri "http://YOUR_EC2_IP:8000/health" -Method GET
```

### Vercel 함수 직접 테스트

```bash
# Vercel CLI 사용
vercel logs --follow

# 또는 브라우저에서
# Vercel 대시보드 → Deployments → Functions 탭
```

## 추가 디버깅

### Next.js API 라우트에 로깅 추가

`frontend/app/api/chat/route.ts`에 다음 추가:

```typescript
console.log("[API] BACKEND_URL:", process.env.BACKEND_URL);
console.log("[API] Request body:", body);
```

이렇게 하면 Vercel 함수 로그에서 확인할 수 있습니다.
