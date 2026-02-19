#!/bin/bash
# EC2에서 systemd 서비스 설정 스크립트

echo "🔧 systemd 서비스 설정 중..."

# 서비스 파일 복사
if [ -f "/home/ubuntu/rag/backend/scripts/rag-api.service" ]; then
    echo "📋 서비스 파일 복사 중..."
    sudo cp /home/ubuntu/rag/backend/scripts/rag-api.service /etc/systemd/system/rag-api.service
elif [ -f "/home/ubuntu/rag/scripts/rag-api.service" ]; then
    echo "📋 서비스 파일 복사 중..."
    sudo cp /home/ubuntu/rag/scripts/rag-api.service /etc/systemd/system/rag-api.service
else
    echo "❌ 서비스 파일을 찾을 수 없습니다. 수동으로 생성합니다..."
    sudo tee /etc/systemd/system/rag-api.service > /dev/null <<EOF
[Unit]
Description=FastAPI RAG Application
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/rag
Environment="PATH=/home/ubuntu/rag/venv/bin"
ExecStart=/home/ubuntu/rag/venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

# 로그 설정
StandardOutput=journal
StandardError=journal
SyslogIdentifier=rag-api

# 환경 변수 파일 로드
EnvironmentFile=/home/ubuntu/rag/.env

[Install]
WantedBy=multi-user.target
EOF
fi

# systemd 재로드
echo "🔄 systemd 재로드 중..."
sudo systemctl daemon-reload

# 서비스 활성화
echo "✅ 서비스 활성화 중..."
sudo systemctl enable rag-api.service

# 서비스 시작
echo "🚀 서비스 시작 중..."
sudo systemctl start rag-api.service

# 서비스 상태 확인
echo "📊 서비스 상태:"
sudo systemctl status rag-api.service --no-pager -l | head -20

echo ""
echo "✅ 서비스 설정 완료!"
echo "📝 로그 확인: sudo journalctl -u rag-api.service -f"
echo "🔄 재시작: sudo systemctl restart rag-api.service"
