# Vercel 응답 오류 빠른 해결 가이드

## 🚨 즉시 확인할 3가지

### 1. Vercel 환경 변수 확인 및 설정

**Vercel 대시보드:**
1. 프로젝트 선택 → **Settings** → **Environment Variables**
2. 다음 변수 추가/확인:
   ```
   BACKEND_URL=http://YOUR_EC2_IP:8000
   NEXT_PUBLIC_BACKEND_URL=http://YOUR_EC2_IP:8000
   ```
3. **중요:** 환경 변수 추가/수정 후 **반드시 Redeploy**

### 2. EC2 백엔드 실행 확인

**EC2 SSH 접속 후:**
```bash
# 서비스 상태 확인
sudo systemctl status rag-api.service

# 실행 중이 아니면 시작
sudo systemctl start rag-api.service

# 헬스 체크
curl http://localhost:8000/health
```

### 3. EC2 CORS 설정

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

## 🔧 단계별 해결

### Step 1: Vercel 환경 변수 설정

1. Vercel 대시보드 접속
2. 프로젝트 → Settings → Environment Variables
3. `BACKEND_URL` 추가 (값: `http://YOUR_EC2_IP:8000`)
4. `NEXT_PUBLIC_BACKEND_URL` 추가 (값: `http://YOUR_EC2_IP:8000`)
5. **Deployments** → 최신 배포 → **Redeploy** 클릭

### Step 2: EC2 백엔드 확인

```bash
# EC2 SSH 접속
ssh -i your-key.pem ubuntu@YOUR_EC2_IP

# 서비스 시작
sudo systemctl start rag-api.service
sudo systemctl enable rag-api.service

# 상태 확인
sudo systemctl status rag-api.service

# 헬스 체크
curl http://localhost:8000/health
```

### Step 3: EC2 보안 그룹 확인

**AWS 콘솔:**
1. EC2 → 인스턴스 선택
2. 보안 탭 → 보안 그룹 클릭
3. 인바운드 규칙에 포트 8000이 열려있는지 확인
4. 없으면 추가: 포트 8000, 소스 0.0.0.0/0

### Step 4: CORS 설정

```bash
# EC2에서
cd /home/ubuntu/rag
nano .env
```

`.env` 파일에 추가:
```env
CORS_ORIGINS=https://rag-nine-cyan.vercel.app,https://rag-nine-cyan-*.vercel.app,http://localhost:3000
```

```bash
# 서비스 재시작
sudo systemctl restart rag-api.service
```

## ✅ 최종 확인

1. **Vercel 사이트 접속**
   - `https://rag-nine-cyan.vercel.app`

2. **브라우저 개발자 도구 열기 (F12)**
   - Console 탭: 오류 확인
   - Network 탭: API 요청 확인

3. **챗봇에 메시지 전송**
   - 정상 응답이 오는지 확인

## 🆘 여전히 오류가 발생하면

1. **Vercel 함수 로그 확인**
   - Vercel 대시보드 → Deployments → Functions 탭
   - `/api/chat` 함수 로그 확인

2. **EC2 로그 확인**
   ```bash
   sudo journalctl -u rag-api.service -n 100 --no-pager
   ```

3. **외부에서 EC2 접근 테스트**
   ```bash
   # Windows PowerShell
   curl http://YOUR_EC2_IP:8000/health
   ```

## 📝 체크리스트

- [ ] Vercel 환경 변수 `BACKEND_URL` 설정
- [ ] Vercel 환경 변수 `NEXT_PUBLIC_BACKEND_URL` 설정
- [ ] Vercel Redeploy 실행
- [ ] EC2 서비스 실행 중 (`systemctl status`)
- [ ] EC2 헬스 체크 성공 (`curl localhost:8000/health`)
- [ ] EC2 보안 그룹 포트 8000 열림
- [ ] EC2 CORS 설정 완료
- [ ] 브라우저에서 테스트 성공
