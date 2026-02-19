#!/bin/bash
# Vercel에서 EC2 백엔드 연결 테스트 스크립트

echo "🔍 Vercel → EC2 백엔드 연결 테스트"
echo "=================================="
echo ""

# EC2 IP 주소 입력 (스크립트 실행 시 인자로 받거나 환경 변수에서 읽기)
EC2_IP="${1:-$EC2_IP}"
if [ -z "$EC2_IP" ]; then
    echo "❌ EC2 IP 주소를 입력해주세요."
    echo "사용법: ./test_vercel_backend_connection.sh YOUR_EC2_IP"
    exit 1
fi

echo "📍 EC2 IP: $EC2_IP"
echo ""

# 1. 헬스 체크
echo "1️⃣ 헬스 체크 테스트..."
HEALTH_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "http://${EC2_IP}:8000/health")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$HEALTH_RESPONSE" | sed '/HTTP_CODE/d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ 헬스 체크 성공 (HTTP $HTTP_CODE)"
    echo "응답: $BODY"
else
    echo "❌ 헬스 체크 실패 (HTTP $HTTP_CODE)"
    echo "응답: $BODY"
fi
echo ""

# 2. CORS 헤더 확인
echo "2️⃣ CORS 헤더 확인..."
CORS_HEADERS=$(curl -s -I -X OPTIONS "http://${EC2_IP}:8000/api/v1/chat" \
    -H "Origin: https://rag-nine-cyan.vercel.app" \
    -H "Access-Control-Request-Method: POST" \
    -H "Access-Control-Request-Headers: content-type" | grep -i "access-control")

if [ -z "$CORS_HEADERS" ]; then
    echo "⚠️  CORS 헤더가 없습니다. CORS 설정을 확인하세요."
else
    echo "✅ CORS 헤더 발견:"
    echo "$CORS_HEADERS"
fi
echo ""

# 3. 채팅 API 테스트
echo "3️⃣ 채팅 API 테스트..."
CHAT_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -X POST "http://${EC2_IP}:8000/api/v1/chat" \
    -H "Content-Type: application/json" \
    -H "Origin: https://rag-nine-cyan.vercel.app" \
    -d '{"question":"테스트 메시지","mode":"rag_openai"}')

HTTP_CODE=$(echo "$CHAT_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$CHAT_RESPONSE" | sed '/HTTP_CODE/d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ 채팅 API 성공 (HTTP $HTTP_CODE)"
    echo "응답: $BODY" | head -c 200
    echo "..."
else
    echo "❌ 채팅 API 실패 (HTTP $HTTP_CODE)"
    echo "응답: $BODY"
fi
echo ""

# 4. 연결 시간 측정
echo "4️⃣ 연결 시간 측정..."
TIME_START=$(date +%s%N)
curl -s -o /dev/null -w "연결 시간: %{time_total}초\n" "http://${EC2_IP}:8000/health"
echo ""

echo "=================================="
echo "✅ 테스트 완료"
echo ""
echo "💡 다음 단계:"
echo "1. 모든 테스트가 성공하면 Vercel 환경 변수를 확인하세요"
echo "2. 실패한 테스트가 있으면 해당 항목을 수정하세요"
echo "3. Vercel에서 Redeploy를 실행하세요"
