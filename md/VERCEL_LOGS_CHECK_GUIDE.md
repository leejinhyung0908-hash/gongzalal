# Vercel 로그 확인 가이드

## 방법 1: Deployments에서 로그 확인 (가장 일반적)

### 단계별 설명

1. **Vercel 대시보드 접속**
   - https://vercel.com/dashboard
   - 로그인

2. **프로젝트 선택**
   - 배포한 프로젝트 클릭

3. **Deployments 탭 클릭**
   - 상단 메뉴에서 **"Deployments"** 클릭

4. **최신 배포 클릭**
   - 배포 목록에서 가장 최근 배포 항목 클릭

5. **로그 확인**
   - 배포 상세 페이지에서:
     - **"Logs"** 탭 또는 **"Runtime Logs"** 탭 클릭
     - 또는 페이지 하단에 로그가 표시될 수 있습니다
   - 실시간 로그를 확인할 수 있습니다

## 방법 2: Vercel CLI로 로그 확인

### 설치 및 사용

```bash
# 1. Vercel CLI 설치 (이미 설치되어 있다면 스킵)
npm i -g vercel

# 2. Vercel 로그인 (처음만)
vercel login

# 3. 프로젝트 루트로 이동
cd C:\Users\hi\Desktop\test3\rag

# 4. 로그 확인 (실시간)
vercel logs --follow

# 5. 특정 함수 로그만 확인
vercel logs --follow /api/chat
```

## 방법 3: 브라우저 개발자 도구에서 확인

### Network 탭에서 확인

1. **Vercel 사이트 접속**
   - `https://rag-nine-cyan.vercel.app`

2. **개발자 도구 열기 (F12)**

3. **Network 탭 클릭**

4. **챗봇에 메시지 전송**

5. **`/api/chat` 요청 클릭**

6. **Response 탭에서 응답 확인**
   - 오류 메시지와 상세 정보 확인 가능

7. **Headers 탭에서 요청/응답 헤더 확인**

## 방법 4: Vercel 대시보드의 다른 위치

### Analytics & Monitoring

1. **프로젝트 선택** → **Analytics** 탭
2. **Functions** 섹션 확인
3. 함수 실행 통계 및 오류 확인

### Settings에서 확인

1. **프로젝트 선택** → **Settings**
2. **Functions** 섹션 확인
3. 함수 설정 및 로그 확인

## 방법 5: 배포 상세 페이지에서 확인

### 배포 상세 페이지 구조

```
┌─────────────────────────────────────────┐
│  Deployment Details                     │
├─────────────────────────────────────────┤
│  [Overview] [Logs] [Source] [Settings]  │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │  Build Logs                       │ │
│  │  Runtime Logs                     │ │
│  │  Function Logs                    │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

**확인할 로그:**
- **Build Logs**: 빌드 과정의 로그
- **Runtime Logs**: 런타임 실행 로그
- **Function Logs**: 서버리스 함수 실행 로그

## 방법 6: 직접 API 테스트

### 브라우저 콘솔에서 테스트

Vercel 사이트에서 개발자 도구 콘솔 열고:

```javascript
// API 직접 호출 테스트
fetch('/api/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    question: '테스트',
    mode: 'rag_openai'
  })
})
.then(res => {
  console.log('Status:', res.status);
  return res.json();
})
.then(data => {
  console.log('Response:', data);
})
.catch(err => {
  console.error('Error:', err);
});
```

## 로그에서 확인할 내용

### 성공적인 경우

```
[Next.js API] BACKEND_URL: http://YOUR_EC2_IP:8000
[Next.js API] 요청 모드: rag_openai
[Next.js API] 요청 질문: 테스트...
[Next.js API] 요청 URL: http://YOUR_EC2_IP:8000/api/v1/chat
[Next.js API] 응답 상태: 200 OK
[Next.js API] 응답 성공
```

### 환경 변수 문제

```
[Next.js API] BACKEND_URL: http://localhost:8000
```

→ **해결**: Vercel 환경 변수 설정 및 Redeploy

### 연결 실패

```
[Next.js API] 백엔드 연결 실패: {
  error: "fetch failed",
  name: "TypeError",
  backendUrl: "http://YOUR_EC2_IP:8000"
}
```

→ **해결**: EC2 서비스 상태 및 보안 그룹 확인

### 백엔드 오류

```
[Next.js API] 백엔드 오류: {
  status: 500,
  statusText: "Internal Server Error",
  error: "..."
}
```

→ **해결**: EC2 로그 확인

## 빠른 확인 방법

### 1. 배포 상세 페이지에서

1. **Deployments** → 최신 배포 클릭
2. 페이지를 아래로 스크롤
3. **"View Function Logs"** 또는 **"Logs"** 버튼 클릭

### 2. 실시간 로그 스트리밍

Vercel CLI 사용:
```bash
vercel logs --follow
```

이 명령어는 실시간으로 로그를 스트리밍합니다.

## 문제 해결

### 로그가 보이지 않을 때

1. **배포가 완료되었는지 확인**
   - 배포 상태가 "Ready"인지 확인

2. **다른 배포 확인**
   - 이전 배포의 로그를 확인해보세요

3. **Vercel CLI 사용**
   - CLI를 통해 로그 확인

### 로그가 비어있을 때

1. **챗봇에 메시지 전송**
   - API가 호출되어야 로그가 생성됩니다

2. **잠시 대기**
   - 로그가 지연되어 표시될 수 있습니다

3. **새로고침**
   - 페이지를 새로고침하여 최신 로그 확인

## 추천 확인 순서

1. ✅ **Deployments** → 최신 배포 → **Logs** 탭
2. ✅ **브라우저 개발자 도구** → **Network** 탭
3. ✅ **Vercel CLI** 사용 (`vercel logs --follow`)
4. ✅ **브라우저 콘솔**에서 직접 API 테스트
