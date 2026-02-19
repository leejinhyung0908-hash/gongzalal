#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KoELECTRA 게이트웨이 + EXAONE 에이전트 테스트 스크립트

테스트 시나리오:
1. 낮은 구간 (정상 메일): EXAONE 미사용
2. 높은 구간 (스팸 메일): EXAONE 미사용
3. 애매한 구간: EXAONE LangGraph 에이전트 자동 호출
"""

import requests
import json
from typing import Dict, Any


BASE_URL = "http://localhost:8000"
GATEWAY_ENDPOINT = f"{BASE_URL}/api/mcp/gateway"


def test_gateway(text: str, test_name: str) -> Dict[str, Any]:
    """게이트웨이 엔드포인트 테스트"""
    print(f"\n{'='*80}")
    print(f"테스트: {test_name}")
    print(f"{'='*80}")
    print(f"입력 텍스트: {text}")
    print()

    payload = {
        "text": text,
        "session_id": f"test_session_{test_name.lower().replace(' ', '_')}",
    }

    try:
        response = requests.post(GATEWAY_ENDPOINT, json=payload, timeout=120)
        response.raise_for_status()

        result = response.json()

        print(f"✅ 요청 성공")
        print(f"\n📊 KoELECTRA 결과:")
        print(f"  - 스팸 확률: {result.get('spam_prob', 0):.2%}")
        print(f"  - 라벨: {result.get('label', 'unknown')}")
        print(f"  - 신뢰도: {result.get('confidence', 'unknown')}")
        print(f"  - 임계치 구간: {result.get('threshold_zone', 'unknown')}")
        print(f"  - 방법: {result.get('method', 'unknown')}")

        print(f"\n🎯 게이트웨이 결정:")
        print(f"  - 액션: {result.get('gateway_action', 'unknown')}")
        print(f"  - 메시지: {result.get('gateway_message', 'unknown')}")
        print(f"  - EXAONE 필요: {result.get('requires_exaone', False)}")

        exaone_used = result.get('exaone_used', False)
        if exaone_used:
            print(f"\n🤖 EXAONE 판별기 결과:")
            exaone_result = result.get('exaone_result', {})
            if exaone_result:
                print(f"  - 액션: {exaone_result.get('action', 'unknown')}")
                print(f"  - 신뢰도: {exaone_result.get('confidence', 0):.2%}")
                print(f"  - 근거: {exaone_result.get('reason', 'N/A')[:100]}")
                print(f"  - 증거: {exaone_result.get('evidence', [])}")
                print(f"  - 위험 코드: {exaone_result.get('risk_codes', [])}")
        else:
            print(f"\n⚡ EXAONE 미사용 (KoELECTRA만으로 결정)")

        print(f"\n📝 세션 정보:")
        print(f"  - 세션 ID: {result.get('session_id', 'unknown')}")
        print(f"  - 요청 ID: {result.get('request_id', 'unknown')}")
        print(f"  - 세션 요청 수: {result.get('session_request_count', 0)}")

        return result

    except requests.exceptions.RequestException as e:
        print(f"❌ 요청 실패: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"응답 내용: {e.response.text}")
        return {}
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return {}


def main():
    """메인 테스트 함수"""
    print("="*80)
    print("KoELECTRA 게이트웨이 + EXAONE LangGraph 에이전트 테스트")
    print("="*80)
    print(f"\n서버 URL: {BASE_URL}")
    print(f"엔드포인트: {GATEWAY_ENDPOINT}")
    print("\n⚠️  서버가 실행 중인지 확인하세요: python -m backend.main --server")
    print()

    # 테스트 케이스들
    test_cases = [
        {
            "name": "1. 낮은 구간 (정상 메일) - EXAONE 미사용",
            "text": "안녕하세요. 오늘 회의 일정을 확인하고 싶습니다. 가능하시면 답변 부탁드립니다."
        },
        {
            "name": "2. 높은 구간 (스팸 메일) - EXAONE 미사용",
            "text": "🎉🎉🎉 지금 당장 클릭하세요! 특가 할인 이벤트 진행중! 무료 체험! 광고 광고 광고! discount sale now!"
        },
        {
            "name": "3. 애매한 구간 - EXAONE 자동 호출",
            "text": "안녕하세요. 새로운 서비스에 대한 소개를 드리고 싶습니다. 혹시 관심이 있으시면 연락 주시기 바랍니다."
        },
        {
            "name": "4. 애매한 구간 (의심스러운 메일) - EXAONE 자동 호출",
            "text": "고객님께 특별한 혜택을 드립니다. 지금 바로 확인하세요. 한정 기간 할인 이벤트가 진행 중입니다."
        }
    ]

    results = []
    for test_case in test_cases:
        result = test_gateway(test_case["text"], test_case["name"])
        results.append({
            "test": test_case["name"],
            "result": result
        })

    # 요약
    print(f"\n{'='*80}")
    print("테스트 요약")
    print(f"{'='*80}")

    for i, result_data in enumerate(results, 1):
        result = result_data.get("result", {})
        exaone_used = result.get("exaone_used", False)
        gateway_action = result.get("gateway_action", "unknown")
        spam_prob = result.get("spam_prob", 0)

        print(f"\n{i}. {result_data['test']}")
        print(f"   스팸 확률: {spam_prob:.2%}")
        print(f"   게이트웨이 액션: {gateway_action}")
        print(f"   EXAONE 사용: {'✅ 예' if exaone_used else '❌ 아니오'}")

    print(f"\n{'='*80}")
    print("테스트 완료!")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()

