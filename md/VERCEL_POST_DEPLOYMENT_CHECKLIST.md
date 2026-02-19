# Vercel 배포 후 확인 체크리스트

## ✅ 배포 완료 확인

배포가 성공적으로 완료되었습니다! 이제 다음 단계를 진행하세요.

## 1. Vercel 환경 변수 설정 확인

Vercel 대시보드에서 환경 변수가 올바르게 설정되었는지 확인:

1. **Vercel 대시보드** → **프로젝트 선택** → **Settings** → **Environment Variables**

2. 다음 변수가 설정되어 있는지 확인:
   ```
   BACKEND_URL=http://YOUR_EC2_IP:8000
   NEXT_PUBLIC_BACKEND_URL=http://YOUR_EC2_IP:8000
   ```

3. **중요**: EC2 IP 주소를 실제 IP로 변경했는지 확인하세요.

## 2. EC2 백엔드 CORS 설정 업데이트

Vercel 도메인을 CORS 허용 목록에 추가해야 합니다.

### EC2에 SSH 접속

```bash
ssh -i your-key.pem ubuntu@YOUR_EC2_IP
```

### .env 파일 수정

```bash
cd /home/ubuntu/rag
nano .env
```

다음 내용 추가/수정:
```env
# 기존 DATABASE_URL 유지
DATABASE_URL=postgresql+psycopg://YOUR_NEON_DB_URL

# CORS 설정 - Vercel 도메인 추가
# Vercel 프로젝트 URL을 확인하여 추가하세요 (예: https://your-project.vercel.app)
CORS_ORIGINS=https://your-project.vercel.app,https://your-project-*.vercel.app,http://localhost:3000,http://localhost:8000

# 기타 설정...
```

**참고**:
- `https://your-project-*.vercel.app` 패턴은 모든 Vercel 프리뷰 도메인을 허용합니다.
- 실제 Vercel 프로젝트 URL은 Vercel 대시보드에서 확인할 수 있습니다.

### 서비스 재시작

```bash
sudo systemctl restart rag-api.service
sudo systemctl status rag-api.service
```

## 3. 연결 테스트

### 3.1 Vercel 사이트에서 테스트

1. Vercel 배포된 사이트 접속 (예: `https://your-project.vercel.app`)
2. 브라우저 개발자 도구 열기 (F12)
3. **Network** 탭 열기
4. 챗봇에 메시지 전송
5. API 요청이 성공하는지 확인:
   - 요청 URL: `http://YOUR_EC2_IP:8000/api/v1/chat`
   - 상태 코드: `200 OK`

### 3.2 EC2 백엔드 직접 테스트

EC2에서 직접 헬스 체크:

```bash
curl http://localhost:8000/health
```

예상 응답:
```json
{"status":"healthy","database":"connected"}
```

### 3.3 CORS 테스트

브라우저 콘솔에서 직접 테스트:

```javascript
fetch('http://YOUR_EC2_IP:8000/api/v1/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    question: '테스트 메시지',
    mode: 'rag_openai'
  })
})
.then(res => res.json())
.then(data => console.log('성공:', data))
.catch(err => console.error('오류:', err));
```

## 4. 문제 해결

### 문제: CORS 오류 발생

**증상**: 브라우저 콘솔에 `CORS policy` 오류 메시지

**해결**:
1. EC2 `.env` 파일의 `CORS_ORIGINS`에 Vercel 도메인이 포함되어 있는지 확인
2. 서비스 재시작: `sudo systemctl restart rag-api.service`
3. EC2 보안 그룹에서 포트 8000이 열려있는지 확인

### 문제: API 연결 실패 (Network Error)

**증상**: `Failed to fetch` 또는 네트워크 오류

**해결**:
1. EC2 보안 그룹 확인:
   - 인바운드 규칙에 포트 8000이 열려있는지 확인
   - 소스: `0.0.0.0/0` (또는 특정 IP)
2. EC2에서 서비스 상태 확인:
   ```bash
   sudo systemctl status rag-api.service
   ```
3. Vercel 환경 변수 `BACKEND_URL`이 올바른지 확인

### 문제: 환경 변수가 적용되지 않음

**해결**:
1. Vercel 대시보드에서 환경 변수 삭제 후 재추가
2. **Redeploy** 클릭하여 재배포
3. 환경 변수 이름 확인:
   - 서버 사이드: `BACKEND_URL`
   - 클라이언트 사이드: `NEXT_PUBLIC_BACKEND_URL`

## 5. 프로덕션 최적화 (선택사항)

### 5.1 HTTPS 사용

현재 HTTP를 사용 중이라면, 프로덕션에서는 HTTPS를 권장합니다:

1. **도메인 사용**: EC2에 도메인 연결 후 Nginx로 HTTPS 설정
2. **Vercel 환경 변수 업데이트**:
   ```
   BACKEND_URL=https://api.yourdomain.com
   NEXT_PUBLIC_BACKEND_URL=https://api.yourdomain.com
   ```

### 5.2 환경별 설정

Vercel에서 환경별로 다른 백엔드 URL 사용:

- **Production**: 실제 EC2 IP
- **Preview**: 테스트용 EC2 또는 동일 IP
- **Development**: `http://localhost:8000`

## 6. 최종 확인 체크리스트

- [ ] Vercel 환경 변수 설정 완료
- [ ] EC2 `.env` 파일에 CORS_ORIGINS 설정 완료
- [ ] EC2 서비스 재시작 완료
- [ ] Vercel 사이트에서 챗봇 테스트 성공
- [ ] 브라우저 개발자 도구에서 API 호출 확인
- [ ] 모든 모드 (RAG, OpenAI, QLoRA 등) 테스트 완료

## 다음 단계

모든 확인이 완료되면:
1. **커스텀 도메인 설정** (선택사항)
2. **Speed Insights 활성화** (선택사항)
3. **모니터링 설정** (선택사항)

축하합니다! 🎉 배포가 완료되었습니다.
