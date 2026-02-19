# Vercel Redeploy 가이드

## 방법 1: Vercel 대시보드에서 Redeploy (가장 쉬운 방법)

### 단계별 설명

1. **Vercel 대시보드 접속**
   - https://vercel.com/dashboard 접속
   - 로그인

2. **프로젝트 선택**
   - 배포한 프로젝트 클릭 (예: "rag" 또는 "LangChain Chatbot")

3. **Deployments 탭으로 이동**
   - 상단 메뉴에서 **"Deployments"** 클릭
   - 또는 프로젝트 페이지에서 **"View Deployments"** 클릭

4. **최신 배포 찾기**
   - 배포 목록에서 가장 최근 배포를 찾습니다
   - 각 배포 항목에는 상태(Ready, Building, Error 등)가 표시됩니다

5. **Redeploy 실행**
   - 최신 배포 항목의 **오른쪽 상단에 있는 "..." (점 3개) 메뉴** 클릭
   - 또는 배포 항목을 클릭하여 상세 페이지로 이동
   - **"Redeploy"** 옵션 클릭
   - 확인 대화상자에서 **"Redeploy"** 클릭

6. **배포 완료 대기**
   - 배포 상태가 "Building" → "Ready"로 변경될 때까지 대기
   - 보통 1-3분 정도 소요됩니다

## 방법 2: 특정 커밋으로 Redeploy

1. **Deployments 탭** → 배포 항목 클릭
2. **"..." 메뉴** → **"Redeploy"** 클릭
3. 원하는 커밋 선택 (선택사항)
4. **"Redeploy"** 클릭

## 방법 3: GitHub에 푸시하여 자동 배포

환경 변수를 설정한 후:

1. **로컬에서 아무 파일이나 수정** (예: README.md에 공백 추가)
2. **Git에 커밋 및 푸시:**
   ```bash
   git add .
   git commit -m "Trigger redeploy for environment variables"
   git push origin main
   ```
3. **자동 배포 시작**
   - Vercel이 자동으로 변경사항을 감지하고 배포를 시작합니다

## 방법 4: Vercel CLI 사용

터미널에서:

```bash
# 1. Vercel CLI 설치 (이미 설치되어 있다면 스킵)
npm i -g vercel

# 2. 프로젝트 루트로 이동 (frontend 폴더가 아닌 리포지토리 루트)
cd C:\Users\hi\Desktop\test3\rag

# 3. Vercel 로그인 (처음만)
vercel login

# 4. 프로덕션 배포 (Redeploy)
vercel --prod
```

## 환경 변수 변경 후 Redeploy가 필요한 이유

**중요:** Vercel에서 환경 변수를 추가하거나 수정한 후에는 **반드시 Redeploy**를 해야 합니다.

이유:
- 환경 변수는 빌드 시점에 주입됩니다
- 기존 배포는 이전 환경 변수로 빌드되었기 때문에 새 환경 변수를 사용하지 않습니다
- Redeploy를 하면 새로운 환경 변수로 다시 빌드됩니다

## Redeploy 확인 방법

1. **Deployments 탭에서 확인**
   - 새로운 배포 항목이 생성됩니다
   - 상태가 "Building" → "Ready"로 변경됩니다

2. **배포 완료 알림**
   - 배포가 완료되면 Vercel이 알림을 보냅니다
   - 또는 배포 상태가 "Ready"로 변경됩니다

3. **사이트 접속하여 테스트**
   - 배포된 URL로 접속하여 기능이 정상 작동하는지 확인

## 스크린샷 가이드

### Deployments 탭에서 Redeploy

```
┌─────────────────────────────────────────┐
│  Deployments                            │
├─────────────────────────────────────────┤
│  [최신 배포 항목]                       │
│  ┌───────────────────────────────────┐ │
│  │ Status: Ready                     │ │
│  │ Commit: abc123                    │ │
│  │ ... [메뉴] ──┐                    │ │
│  └───────────────────────────────────┘ │
│         │                              │
│         └─> Redeploy                   │
│             Promote to Production      │
│             Cancel                     │
└─────────────────────────────────────────┘
```

### 배포 상세 페이지에서 Redeploy

```
┌─────────────────────────────────────────┐
│  Deployment Details                     │
├─────────────────────────────────────────┤
│  [배포 정보]                            │
│                                         │
│  [Redeploy] [Promote] [Cancel]          │
│                                         │
└─────────────────────────────────────────┘
```

## 빠른 체크리스트

- [ ] Vercel 대시보드 접속
- [ ] 프로젝트 선택
- [ ] Deployments 탭 클릭
- [ ] 최신 배포의 "..." 메뉴 클릭
- [ ] "Redeploy" 클릭
- [ ] 배포 완료 대기 (1-3분)
- [ ] 사이트 접속하여 테스트

## 문제 해결

### Redeploy 버튼이 보이지 않을 때
- 배포가 이미 진행 중일 수 있습니다
- 권한이 없을 수 있습니다 (프로젝트 소유자 확인)

### Redeploy 후에도 환경 변수가 적용되지 않을 때
1. 환경 변수가 올바르게 설정되었는지 다시 확인
2. 환경 변수 이름 확인 (`BACKEND_URL`, `NEXT_PUBLIC_BACKEND_URL`)
3. 환경 변수가 모든 환경(Production, Preview, Development)에 설정되었는지 확인
4. 다시 Redeploy 실행

### 배포가 실패할 때
1. **Logs 탭**에서 오류 메시지 확인
2. 빌드 로그 확인
3. 환경 변수 값이 올바른지 확인 (특히 URL 형식)
