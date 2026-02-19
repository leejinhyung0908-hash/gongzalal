#!/bin/bash
# EC2 서비스 상태 확인 스크립트

echo "🔍 EC2 백엔드 상태 확인 중..."
echo ""

# 1. 서비스 상태
echo "1️⃣ 서비스 상태:"
sudo systemctl status rag-api.service --no-pager -l | head -15
echo ""

# 2. 포트 리스닝 확인
echo "2️⃣ 포트 리스닝 확인:"
sudo ss -tuln | grep -E ':(80|8000)' || echo "❌ 포트 80 또는 8000에서 리스닝하지 않음"
echo ""

# 3. 헬스 체크
echo "3️⃣ 헬스 체크 (포트 8000):"
curl -s http://localhost:8000/health || echo "❌ 포트 8000 헬스 체크 실패"
echo ""

echo "4️⃣ 헬스 체크 (포트 80):"
curl -s http://localhost/health || echo "❌ 포트 80 헬스 체크 실패"
echo ""

# 4. 최근 로그
echo "5️⃣ 최근 서비스 로그 (마지막 20줄):"
sudo journalctl -u rag-api.service -n 20 --no-pager
echo ""

# 5. EC2 IP 확인
echo "6️⃣ EC2 퍼블릭 IP:"
curl -s http://169.254.169.254/latest/meta-data/public-ipv4
echo ""

echo "✅ 확인 완료!"
