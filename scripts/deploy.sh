#!/bin/bash
# EC2 배포 스크립트
# 이 스크립트는 EC2 인스턴스에서 직접 실행하거나 GitHub Actions에서 사용할 수 있습니다.

set -e

echo "🚀 FastAPI 배포 시작..."

# 변수 설정
APP_DIR="$HOME/rag"
SERVICE_NAME="rag-api"
PYTHON_VERSION="3.11"

# 앱 디렉토리로 이동
cd "$APP_DIR" || {
  echo "❌ 앱 디렉토리를 찾을 수 없습니다: $APP_DIR"
  exit 1
}

echo "📦 최신 코드 가져오기..."
git fetch origin
git reset --hard origin/main || git reset --hard origin/master

# Python 가상환경 설정
if [ ! -d "venv" ]; then
  echo "🐍 Python 가상환경 생성..."
  python3 -m venv venv
fi

echo "📚 의존성 설치..."
source venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt

# 환경 변수 확인
if [ ! -f .env ]; then
  echo "⚠️  .env 파일이 없습니다."
  echo "필요한 환경 변수:"
  echo "  - DATABASE_URL"
  echo "  - OPENAI_API_KEY (선택사항)"
  echo "  - 기타 설정..."
fi

# systemd 서비스 재시작
if systemctl list-unit-files | grep -q "$SERVICE_NAME.service"; then
  echo "🔄 서비스 재시작..."
  sudo systemctl daemon-reload
  sudo systemctl restart "$SERVICE_NAME.service"
  sudo systemctl status "$SERVICE_NAME.service" --no-pager
else
  echo "⚠️  systemd 서비스가 설정되지 않았습니다."
  echo "scripts/rag-api.service 파일을 /etc/systemd/system/에 복사해주세요."
fi

echo "✅ 배포 완료!"
