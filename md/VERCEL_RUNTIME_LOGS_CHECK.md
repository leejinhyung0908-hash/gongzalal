# Vercel 런타임 로그 확인 가이드

## ✅ 빌드 성공 확인

빌드 로그를 보면:
- ✅ 빌드가 성공적으로 완료되었습니다
- ✅ `/api/chat` 서버리스 함수가 생성되었습니다 (`ƒ /api/chat`)
- ✅ 배포가 완료되었습니다

하지만 **빌드 로그 ≠ 런타임 로그**입니다!

## 🔍 런타임 로그 확인 방법

### 방법 1: 실시간 로그 확인 (Vercel CLI)

**가장 확실한 방법:**

```bash
# 1. 프로젝트 루트로 이동
cd C:\Users\hi\Desktop\test3\rag

# 2. Vercel CLI로 로그 확인 (실시간)
vercel logs --follow

# 3. 챗봇에 메시지 전송하면 로그가 실시간으로 표시됩니다
```

### 방법 2: Vercel 대시보드에서 확인

1. **Vercel 대시보드** → **프로젝트 선택**
2. **Deployments** → **최신 배포 클릭**
3. 배포 상세 페이지에서:
   - **"Runtime Logs"** 또는 **"Function Logs"** 탭 찾기
   - 또는 페이지를 아래로 스크롤하여 로그 섹션 확인
4. **챗봇에 메시지 전송** (로그가 생성되려면 API가 호출되어야 함)
5. 로그 새로고침

### 방법 3: 브라우저에서 직접 테스트

**Vercel 사이트에서 개발자 도구 콘솔 열고:**

```javascript
// API 직접 호출하여 응답 확인
fetch('/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ question: '테스트', mode: 'rag_openai' })
})
.then(async res => {
  const data = await res.json();
  console.log('상태 코드:', res.status);
  console.log('응답 데이터:', data);
  return data;
})
.catch(err => console.error('오류:', err));
```

이렇게 하면 콘솔에 오류 메시지가 표시됩니다.

## 🔍 확인할 로그 내용

런타임 로그에서 다음을 확인하세요:

### 1. 환경 변수 확인

```
[Next.js API] BACKEND_URL: http://YOUR_EC2_IP:8000
```

**문제:**
- `BACKEND_URL: http://localhost:8000` → 환경 변수가 설정되지 않음
- `BACKEND_URL: undefined` → 환경 변수가 없음

**해결:**
- Vercel 대시보드 → Settings → Environment Variables
- `BACKEND_URL` 추가 후 Redeploy

### 2. 연결 실패 확인

```
[Next.js API] 백엔드 연결 실패: {
  error: "fetch failed",
  name: "TypeError",
  backendUrl: "http://YOUR_EC2_IP:8000"
}
```

**해결:**
- EC2 서비스 상태 확인
- EC2 보안 그룹 포트 8000 확인
- 외부에서 EC2 접근 테스트

### 3. 백엔드 오류 확인

```
[Next.js API] 백엔드 오류: {
  status: 500,
  statusText: "Internal Server Error",
  error: "..."
}
```

**해결:**
- EC2 로그 확인: `sudo journalctl -u rag-api.service -n 100`

## 🚀 빠른 진단 단계

### Step 1: 환경 변수 확인

**Vercel 대시보드:**
1. 프로젝트 → **Settings** → **Environment Variables**
2. `BACKEND_URL`이 설정되어 있는지 확인
3. 값이 올바른지 확인 (예: `http://YOUR_EC2_IP:8000`)

### Step 2: 런타임 로그 확인

**Vercel CLI 사용:**
```bash
cd C:\Users\hi\Desktop\test3\rag
vercel logs --follow
```

그 다음 챗봇에 메시지를 보내면 로그가 실시간으로 표시됩니다.

### Step 3: EC2 백엔드 확인

**로컬에서 테스트:**
```powershell
# Windows PowerShell
curl http://YOUR_EC2_IP:8000/health
```

예상 응답:
```json
{"status":"healthy","database":"connected"}
```

## 📝 체크리스트

- [ ] 빌드 성공 확인 (완료 ✅)
- [ ] Vercel 환경 변수 `BACKEND_URL` 설정 확인
- [ ] Vercel Redeploy 실행 (환경 변수 설정 후)
- [ ] Vercel 런타임 로그 확인 (`vercel logs --follow`)
- [ ] 챗봇에 메시지 전송하여 로그 생성
- [ ] EC2 백엔드 헬스 체크 성공 확인
- [ ] 브라우저 콘솔에서 API 직접 테스트

## 💡 팁

**Vercel CLI가 없다면:**
```bash
npm i -g vercel
vercel login
```

**로그가 보이지 않을 때:**
1. 챗봇에 메시지를 보내야 로그가 생성됩니다
2. `vercel logs --follow`를 실행한 상태에서 메시지를 보내세요
3. 로그는 실시간으로 스트리밍됩니다
