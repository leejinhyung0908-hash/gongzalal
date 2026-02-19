# Vercel 프로젝트 URL 확인 방법

## 방법 1: Vercel 대시보드에서 확인 (가장 쉬운 방법)

1. **Vercel 대시보드 접속**
   - https://vercel.com/dashboard 접속
   - 로그인

2. **프로젝트 선택**
   - 배포한 프로젝트 클릭 (예: "LangChain Chatbot" 또는 "rag")

3. **URL 확인**
   - 프로젝트 페이지 상단에 **배포된 URL**이 표시됩니다
   - 예시:
     ```
     https://langchain-chatbot-abc123.vercel.app
     ```
   - 또는 **Domains** 섹션에서 확인 가능

4. **배포 목록에서 확인**
   - 왼쪽 사이드바에서 **Deployments** 클릭
   - 최신 배포 항목을 클릭
   - 상단에 배포된 URL이 표시됩니다

## 방법 2: 배포 성공 화면에서 확인

배포가 완료된 화면(축하 메시지가 나온 화면)에서:
- 중앙에 표시된 **미리보기 URL**이 바로 프로젝트 URL입니다
- 또는 **"Continue to Dashboard"** 버튼을 클릭하여 대시보드로 이동

## 방법 3: 브라우저 주소창에서 확인

이미 Vercel 사이트에 접속했다면:
- 브라우저 주소창의 URL이 바로 프로젝트 URL입니다
- 예: `https://your-project-name-xyz.vercel.app`

## URL 형식

Vercel 프로젝트 URL은 일반적으로 다음 형식입니다:

```
https://[프로젝트-이름]-[해시].vercel.app
```

예시:
- `https://langchain-chatbot-abc123.vercel.app`
- `https://rag-frontend-xyz789.vercel.app`

## CORS 설정에 사용할 URL

확인한 URL을 EC2 `.env` 파일에 다음과 같이 추가:

```env
CORS_ORIGINS=https://langchain-chatbot-abc123.vercel.app,https://langchain-chatbot-*.vercel.app,http://localhost:3000
```

**설명**:
- `https://langchain-chatbot-abc123.vercel.app`: 프로덕션 URL
- `https://langchain-chatbot-*.vercel.app`: 모든 프리뷰/브랜치 배포 URL 허용 (와일드카드)
- `http://localhost:3000`: 로컬 개발용

## 스크린샷으로 확인하는 방법

1. Vercel 대시보드 → 프로젝트 선택
2. 프로젝트 페이지 상단을 보면:
   ```
   ┌─────────────────────────────────────┐
   │  LangChain Chatbot                  │
   │  https://your-project.vercel.app   │  ← 여기!
   │  [Visit] [Settings] [Deployments]   │
   └─────────────────────────────────────┘
   ```

## 빠른 확인 체크리스트

- [ ] Vercel 대시보드 접속
- [ ] 프로젝트 선택
- [ ] 상단에 표시된 URL 확인
- [ ] URL 복사
- [ ] EC2 `.env` 파일에 `CORS_ORIGINS`에 추가
