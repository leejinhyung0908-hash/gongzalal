# Vercel 배포 가이드

## Frontend를 Vercel에 배포하기

### 1. Vercel 대시보드에서 프로젝트 연결

#### 방법 A: GitHub 연동 (권장)

1. **Vercel 대시보드 접속**
   - https://vercel.com/dashboard 접속
   - "Add New..." → "Project" 클릭

2. **GitHub 리포지토리 선택**
   - GitHub 계정 연동 (이미 되어있다면 스킵)
   - 리포지토리 선택: `rag` (또는 해당 리포지토리)

3. **프로젝트 설정**
   - **Framework Preset**: Next.js (자동 감지됨)
   - **Root Directory**: `frontend` ⚠️ **중요!**
   - **Build Command**: `npm run build` (기본값)
   - **Output Directory**: `.next` (기본값)
   - **Install Command**: `npm install` (기본값)

4. **환경 변수 설정**
   - "Environment Variables" 섹션에서 다음 변수 추가:

   ```
   BACKEND_URL=http://YOUR_EC2_IP:8000
   NEXT_PUBLIC_BACKEND_URL=http://YOUR_EC2_IP:8000
   ```

   예시:
   ```
   BACKEND_URL=http://13.125.210.86:8000
   NEXT_PUBLIC_BACKEND_URL=http://13.125.210.86:8000
   ```

   ⚠️ **프로덕션 환경에서는 HTTPS를 사용하는 것이 좋습니다.**
   - 도메인을 사용한다면: `https://api.yourdomain.com`
   - 또는 EC2에 Nginx를 설정하여 HTTPS 사용

5. **Deploy 클릭**

#### 방법 B: Vercel CLI 사용

```bash
# 1. Vercel CLI 설치
npm i -g vercel

# 2. frontend 디렉토리로 이동
cd frontend

# 3. Vercel 로그인
vercel login

# 4. 프로젝트 배포
vercel

# 5. 프로덕션 배포
vercel --prod
```

CLI 사용 시 환경 변수 설정:
```bash
vercel env add BACKEND_URL
vercel env add NEXT_PUBLIC_BACKEND_URL
```

### 2. 환경 변수 설정

Vercel 대시보드에서 환경 변수 설정:

1. **프로젝트 선택** → **Settings** → **Environment Variables**

2. **다음 변수 추가**:

   | Name | Value | Environment |
   |------|-------|-------------|
   | `BACKEND_URL` | `http://13.125.210.86:8000` | Production, Preview, Development |
   | `NEXT_PUBLIC_BACKEND_URL` | `http://13.125.210.86:8000` | Production, Preview, Development |

   ⚠️ **주의사항**:
   - EC2 IP 주소를 실제 IP로 변경하세요
   - 프로덕션에서는 HTTPS를 사용하는 것이 좋습니다
   - CORS 설정이 EC2 백엔드에서 허용되어야 합니다

### 3. Root Directory 설정 확인

Vercel 대시보드에서:

1. **프로젝트 선택** → **Settings** → **General**
2. **Root Directory** 확인: `frontend`로 설정되어 있는지 확인
3. 없으면 "Edit" 클릭하여 `frontend` 입력

### 4. CORS 설정 확인

EC2 백엔드의 CORS 설정이 Vercel 도메인을 허용하는지 확인:

`backend/main.py`에서:
```python
CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")
```

Vercel 도메인을 추가하려면:
```python
# .env 파일에 추가
CORS_ORIGINS=https://your-project.vercel.app,https://your-custom-domain.com
```

### 5. 배포 후 확인

배포가 완료되면:

1. **Vercel 대시보드에서 배포 상태 확인**
   - "Deployments" 탭에서 배포 상태 확인
   - 성공하면 URL이 생성됨 (예: `https://your-project.vercel.app`)

2. **브라우저에서 접속**
   ```
   https://your-project.vercel.app
   ```

3. **API 연결 테스트**
   - 채팅 기능이 정상 작동하는지 확인
   - 브라우저 개발자 도구(F12) → Network 탭에서 API 호출 확인

### 6. 자동 배포 설정

GitHub 연동 시:
- `main` 또는 `master` 브랜치에 푸시하면 자동 배포
- `frontend/` 폴더 변경 시에만 배포되도록 설정 가능

**자동 배포 조건 설정** (선택사항):
- Vercel 대시보드 → Settings → Git
- "Ignore Build Step" 설정:
  ```bash
  git diff HEAD^ HEAD --quiet ./frontend
  ```
  이렇게 하면 `frontend/` 폴더가 변경되었을 때만 빌드됩니다.

### 7. 커스텀 도메인 설정 (선택사항)

1. **Vercel 대시보드** → **Settings** → **Domains**
2. 도메인 추가
3. DNS 설정 안내에 따라 DNS 레코드 추가

### 8. 문제 해결

#### 빌드 실패 시:
```bash
# 로컬에서 빌드 테스트
cd frontend
npm install
npm run build
```

#### API 연결 실패 시:
1. EC2 보안 그룹에서 포트 8000이 열려있는지 확인
2. CORS 설정 확인
3. 환경 변수 `BACKEND_URL`이 올바른지 확인

#### 환경 변수가 적용되지 않을 때:
- Vercel 대시보드에서 환경 변수 삭제 후 재추가
- 배포 재시도

## 빠른 시작 체크리스트

- [ ] Vercel 계정 생성 및 GitHub 연동
- [ ] 리포지토리 선택
- [ ] Root Directory를 `frontend`로 설정
- [ ] 환경 변수 설정 (`BACKEND_URL`, `NEXT_PUBLIC_BACKEND_URL`)
- [ ] Deploy 클릭
- [ ] 배포 완료 후 URL 확인
- [ ] 브라우저에서 접속 테스트
- [ ] EC2 백엔드 CORS 설정 확인

## 참고사항

- **HTTPS**: Vercel은 자동으로 HTTPS를 제공합니다
- **환경 변수**: `NEXT_PUBLIC_` 접두사가 있는 변수만 클라이언트에서 접근 가능
- **API Routes**: Next.js API Routes는 Vercel Serverless Functions로 실행됩니다
- **빌드 시간**: 첫 배포는 약 2-3분 소요됩니다
