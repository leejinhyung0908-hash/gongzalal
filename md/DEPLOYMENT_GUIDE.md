# FastAPI EC2 배포 가이드

이 가이드는 GitHub Actions를 사용하여 FastAPI 애플리케이션을 EC2에 자동 배포하는 방법을 설명합니다.

## 📋 사전 준비사항

### 1. GitHub Secrets 설정 (완료됨 ✅)

이미 다음 시크릿이 설정되어 있습니다:
- `EC2_HOST`: EC2 인스턴스 호스트명
- `EC2_USER`: EC2 사용자명 (보통 `ubuntu`)
- `EC2_SSH_KEY`: SSH 개인 키 전체 내용

### 2. EC2 인스턴스 초기 설정

EC2에 SSH로 접속하여 다음을 실행:

```bash
# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 필수 패키지 설치
sudo apt install -y python3-pip python3-venv git curl

# 저장소 클론
cd ~
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git rag
cd rag

# Python 가상환경 생성
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt

# 환경 변수 파일 생성
nano .env
```

### 3. .env 파일 설정

`.env` 파일 예시:

```env
# 데이터베이스 설정
DATABASE_URL=postgresql+psycopg://user:password@host:5432/dbname
PGENGINE_URL=postgresql+asyncpg://user:password@host:5432/dbname

# OpenAI 설정 (선택사항)
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4o-mini

# 서버 설정
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=*

# LLM 모델 설정
MODEL_BASE_PATH=./model
DEFAULT_MODEL_TYPE=midm
DEFAULT_MODEL_NAME=midm
```

### 4. systemd 서비스 설정

```bash
# 서비스 파일 복사
sudo cp scripts/rag-api.service /etc/systemd/system/

# 서비스 파일 수정 (경로 확인)
sudo nano /etc/systemd/system/rag-api.service

# systemd 재로드 및 서비스 시작
sudo systemctl daemon-reload
sudo systemctl enable rag-api.service
sudo systemctl start rag-api.service

# 서비스 상태 확인
sudo systemctl status rag-api.service
```

### 5. EC2 보안 그룹 설정

EC2 콘솔에서 보안 그룹에 다음 규칙 추가:

| Type | Protocol | Port Range | Source | Description |
|------|----------|------------|--------|-------------|
| SSH | TCP | 22 | My IP | SSH 접속 |
| Custom TCP | TCP | 8000 | 0.0.0.0/0 | FastAPI 서비스 |

## 🚀 배포 프로세스

### 자동 배포 (GitHub Actions)

1. **main/master 브랜치에 푸시**
   ```bash
   git add .
   git commit -m "배포 준비"
   git push origin main
   ```

2. **GitHub Actions 실행**
   - GitHub 저장소 → Actions 탭
   - "Deploy FastAPI to EC2" 워크플로우 확인
   - 배포 진행 상황 모니터링

3. **배포 완료 확인**
   - 워크플로우가 성공적으로 완료되면 자동으로 서비스 재시작
   - `http://YOUR_EC2_IP:8000/health`로 헬스 체크

### 수동 배포

EC2에 SSH 접속 후:

```bash
cd ~/rag
bash scripts/deploy.sh
```

## 📁 파일 구조

```
rag/
├── .github/
│   └── workflows/
│       └── deploy-ec2.yml      # GitHub Actions 워크플로우
├── backend/
│   ├── main.py                 # FastAPI 애플리케이션
│   ├── requirements.txt        # Python 의존성
│   └── ...
├── scripts/
│   ├── deploy.sh              # 배포 스크립트
│   └── rag-api.service        # systemd 서비스 파일
├── .env                        # 환경 변수 (Git에 커밋 안 됨)
└── venv/                       # Python 가상환경
```

## 🔍 모니터링 및 로그

### 서비스 상태 확인

```bash
# 서비스 상태
sudo systemctl status rag-api.service

# 서비스 시작/중지/재시작
sudo systemctl start rag-api.service
sudo systemctl stop rag-api.service
sudo systemctl restart rag-api.service

# 서비스 로그
sudo journalctl -u rag-api.service -f

# 최근 로그 (50줄)
sudo journalctl -u rag-api.service -n 50
```

### 헬스 체크

```bash
# 로컬에서
curl http://localhost:8000/health

# 외부에서
curl http://YOUR_EC2_IP:8000/health

# API 문서 확인
curl http://YOUR_EC2_IP:8000/docs
```

## 🐛 문제 해결

### 배포 실패 시

1. **GitHub Actions 로그 확인**
   - Actions 탭 → 실패한 워크플로우 → 로그 확인

2. **EC2에서 직접 확인**
   ```bash
   # 서비스 로그 확인
   sudo journalctl -u rag-api.service -n 100

   # 수동 실행 테스트
   cd ~/rag
   source venv/bin/activate
   uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```

3. **환경 변수 확인**
   ```bash
   cat ~/rag/.env
   ```

4. **포트 충돌 확인**
   ```bash
   sudo netstat -tlnp | grep 8000
   ```

### 서비스가 시작되지 않는 경우

```bash
# 서비스 파일 확인
cat /etc/systemd/system/rag-api.service

# 경로 확인
ls -la ~/rag
ls -la ~/rag/venv

# 권한 확인
whoami
pwd
```

## 🔄 CI/CD 워크플로우 설명

### 트리거

- **자동**: `main` 또는 `master` 브랜치에 푸시 시
- **수동**: GitHub Actions → "Deploy FastAPI to EC2" → "Run workflow"

### 배포 단계

1. **코드 체크아웃**: 저장소 코드 가져오기
2. **SSH 설정**: SSH 키 설정 및 호스트 확인
3. **EC2 배포**:
   - 저장소 클론/업데이트
   - Python 가상환경 설정
   - 의존성 설치
   - systemd 서비스 재시작
   - 헬스 체크
4. **외부 헬스 체크**: 배포 성공 확인

## 📝 추가 설정

### Nginx 리버스 프록시 (선택사항)

포트 80/443으로 접근하려면:

```bash
# Nginx 설치
sudo apt install nginx

# 설정 파일 생성
sudo nano /etc/nginx/sites-available/rag-api
```

Nginx 설정:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# 심볼릭 링크 생성
sudo ln -s /etc/nginx/sites-available/rag-api /etc/nginx/sites-enabled/

# Nginx 재시작
sudo systemctl restart nginx
```

### SSL/TLS 인증서 (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## 🔐 보안 고려사항

1. **SSH 키 보안**
   - GitHub Secrets에만 저장
   - 로컬 `.pem` 파일은 `.gitignore`에 포함

2. **환경 변수**
   - `.env` 파일은 Git에 커밋하지 않음
   - 민감한 정보는 환경 변수로 관리

3. **방화벽 설정**
   - 필요한 포트만 열기
   - SSH는 특정 IP만 허용 (선택사항)

4. **정기 업데이트**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

## ✅ 배포 체크리스트

- [ ] GitHub Secrets 설정 완료
- [ ] EC2 인스턴스 초기 설정 완료
- [ ] `.env` 파일 생성 및 설정
- [ ] systemd 서비스 설정 완료
- [ ] EC2 보안 그룹 설정 완료 (포트 8000)
- [ ] 로컬에서 서비스 테스트 완료
- [ ] GitHub Actions 워크플로우 테스트

## 📚 참고 자료

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [systemd 서비스 관리](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [GitHub Actions 문서](https://docs.github.com/en/actions)
- [AWS EC2 문서](https://docs.aws.amazon.com/ec2/)

---

**배포 준비가 완료되었습니다!** `main` 브랜치에 푸시하면 자동으로 배포됩니다. 🚀
