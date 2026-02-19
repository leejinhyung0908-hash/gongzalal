#!/bin/bash
# 배포 확인 스크립트

echo "🔍 배포 상태 확인 중..."
echo ""

# 1. 서비스 상태 확인
echo "1️⃣  systemd 서비스 상태:"
sudo systemctl status rag-api.service --no-pager -l | head -20
echo ""

# 2. 서비스 로그 확인
echo "2️⃣  최근 서비스 로그 (마지막 30줄):"
sudo journalctl -u rag-api.service -n 30 --no-pager
echo ""

# 3. 헬스 체크
echo "3️⃣  헬스 체크:"
if curl -f http://localhost:8000/health 2>/dev/null; then
    echo ""
    echo "✅ 헬스 체크 성공"
else
    echo "❌ 헬스 체크 실패"
fi
echo ""

# 4. API 엔드포인트 확인
echo "4️⃣  API 엔드포인트 확인:"
curl -s http://localhost:8000/docs > /dev/null && echo "✅ /docs 엔드포인트 접근 가능" || echo "❌ /docs 엔드포인트 접근 불가"
curl -s http://localhost:8000/health > /dev/null && echo "✅ /health 엔드포인트 접근 가능" || echo "❌ /health 엔드포인트 접근 불가"
echo ""

# 5. 디스크 공간 확인
echo "5️⃣  디스크 공간:"
df -h / | tail -1
echo ""

# 6. 프로세스 확인
echo "6️⃣  실행 중인 프로세스:"
ps aux | grep uvicorn | grep -v grep || echo "❌ uvicorn 프로세스가 실행 중이지 않습니다"
echo ""

# 7. 포트 확인
echo "7️⃣  포트 8000 리스닝 확인:"
sudo netstat -tlnp | grep :8000 || sudo ss -tlnp | grep :8000 || echo "❌ 포트 8000이 리스닝되지 않습니다"
echo ""

echo "✅ 확인 완료"
