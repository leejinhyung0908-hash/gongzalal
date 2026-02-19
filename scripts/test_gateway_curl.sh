#!/bin/bash
# KoELECTRA 게이트웨이 + EXAONE 에이전트 테스트 (curl 버전)

BASE_URL="http://localhost:8000"
GATEWAY_ENDPOINT="${BASE_URL}/api/mcp/gateway"

echo "=========================================="
echo "KoELECTRA 게이트웨이 + EXAONE 테스트"
echo "=========================================="
echo ""

# 테스트 1: 낮은 구간 (정상 메일)
echo "테스트 1: 낮은 구간 (정상 메일) - EXAONE 미사용"
echo "----------------------------------------"
curl -X POST "${GATEWAY_ENDPOINT}" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "안녕하세요. 오늘 회의 일정을 확인하고 싶습니다. 가능하시면 답변 부탁드립니다.",
    "session_id": "test_session_1"
  }' | jq '.'
echo ""
echo ""

# 테스트 2: 높은 구간 (스팸 메일)
echo "테스트 2: 높은 구간 (스팸 메일) - EXAONE 미사용"
echo "----------------------------------------"
curl -X POST "${GATEWAY_ENDPOINT}" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "🎉🎉🎉 지금 당장 클릭하세요! 특가 할인 이벤트 진행중! 무료 체험! 광고 광고 광고! discount sale now!",
    "session_id": "test_session_2"
  }' | jq '.'
echo ""
echo ""

# 테스트 3: 애매한 구간 - EXAONE 자동 호출
echo "테스트 3: 애매한 구간 - EXAONE 자동 호출"
echo "----------------------------------------"
curl -X POST "${GATEWAY_ENDPOINT}" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "안녕하세요. 새로운 서비스에 대한 소개를 드리고 싶습니다. 혹시 관심이 있으시면 연락 주시기 바랍니다.",
    "session_id": "test_session_3"
  }' | jq '.'
echo ""
echo ""

echo "=========================================="
echo "테스트 완료!"
echo "=========================================="

