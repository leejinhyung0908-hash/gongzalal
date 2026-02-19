"""Exam Flow API End-to-End 테스트 스크립트

백엔드 서버가 실행 중일 때 실제 API를 호출하여 테스트합니다.
"""

import json
import sys
import requests
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# API 엔드포인트
BASE_URL = "http://localhost:8000"
EXAM_FLOW_ENDPOINT = f"{BASE_URL}/api/v1/admin/exam/flow"


def test_exam_flow_api():
    """Exam Flow API 테스트"""

    test_cases = [
        # RULE_BASED 케이스 (명확한 DB 조회)
        {
            "question": "2025년 국가직 행정법총론 3번 알려줘",
            "expected_type": "RULE_BASED",
            "description": "명확한 정답 조회 요청"
        },
        {
            "question": "2024년 지방직 9급 한국사 10번 정답",
            "expected_type": "RULE_BASED",
            "description": "명확한 정답 조회 요청"
        },

        # POLICY_BASED (EXPLAIN) 케이스
        {
            "question": "신뢰보호의 원칙이 이 판례에서 왜 적용 안 돼?",
            "expected_type": "POLICY_BASED",
            "description": "해설 요청"
        },
        {
            "question": "행정법에서 신뢰보호의 원칙의 의미를 설명해줘",
            "expected_type": "POLICY_BASED",
            "description": "해설 요청"
        },

        # POLICY_BASED (ADVICE) 케이스
        {
            "question": "직장인인데 하루 4시간 공부로 합격 가능할까?",
            "expected_type": "POLICY_BASED",
            "description": "학습 상담 요청"
        },
        {
            "question": "9급 공무원 시험 준비 방법 알려줘",
            "expected_type": "POLICY_BASED",
            "description": "학습 상담 요청"
        },

        # BLOCK 케이스
        {
            "question": "오늘 날씨 어때?",
            "expected_type": "BLOCK",
            "description": "도메인 외 질문"
        },
        {
            "question": "배고파",
            "expected_type": "BLOCK",
            "description": "도메인 외 질문"
        },
    ]

    print("=" * 60)
    print("Exam Flow API End-to-End 테스트")
    print("=" * 60)
    print(f"서버 URL: {BASE_URL}")
    print(f"엔드포인트: {EXAM_FLOW_ENDPOINT}\n")

    # 서버 연결 확인
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code != 200:
            print("❌ 서버가 실행 중이 아닙니다. 백엔드 서버를 먼저 실행해주세요.")
            print("   명령어: uvicorn backend.main:app --host localhost --port 8000 --reload")
            return
    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다. 백엔드 서버를 먼저 실행해주세요.")
        print("   명령어: uvicorn backend.main:app --host localhost --port 8000 --reload")
        return

    print("✅ 서버 연결 확인 완료\n")

    results = []

    for i, test_case in enumerate(test_cases, 1):
        question = test_case["question"]
        expected = test_case["expected_type"]
        description = test_case["description"]

        print(f"\n[{i}/{len(test_cases)}] {description}")
        print(f"질문: {question}")
        print(f"예상 타입: {expected}")

        try:
            response = requests.post(
                EXAM_FLOW_ENDPOINT,
                json={"question": question},
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✅ 성공 (Status: {response.status_code})")

                # 응답 구조 확인
                intent = result.get("intent", "UNKNOWN")
                gateway = result.get("gateway", "UNKNOWN")
                success = result.get("success", False)

                print(f"   Intent: {intent}")
                print(f"   Gateway: {gateway}")
                print(f"   Success: {success}")

                if "answer" in result:
                    answer = result["answer"]
                    if isinstance(answer, dict):
                        print(f"   Answer: {answer.get('year', '')}년 {answer.get('exam_type', '')} {answer.get('subject', '')} {answer.get('question_no', '')}번")
                    else:
                        print(f"   Answer: {str(answer)[:100]}")

                results.append({
                    "question": question,
                    "expected": expected,
                    "success": True,
                    "intent": intent,
                    "gateway": gateway,
                    "response": result
                })
            else:
                print(f"❌ 실패 (Status: {response.status_code})")
                print(f"   응답: {response.text[:200]}")
                results.append({
                    "question": question,
                    "expected": expected,
                    "success": False,
                    "status_code": response.status_code,
                    "error": response.text[:200]
                })
        except requests.exceptions.Timeout:
            print(f"❌ 타임아웃 (30초 초과)")
            results.append({
                "question": question,
                "expected": expected,
                "success": False,
                "error": "Timeout"
            })
        except Exception as e:
            print(f"❌ 오류: {str(e)}")
            results.append({
                "question": question,
                "expected": expected,
                "success": False,
                "error": str(e)
            })

    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)

    successful = sum(1 for r in results if r.get("success", False))
    total = len(results)

    print(f"전체: {total}개")
    print(f"성공: {successful}개")
    print(f"실패: {total - successful}개")
    print(f"성공률: {successful/total*100:.1f}%")

    print("\n성공한 케이스:")
    for r in results:
        if r.get("success", False):
            print(f"  ✅ {r['question'][:50]}...")
            print(f"     Intent: {r.get('intent', 'N/A')}, Gateway: {r.get('gateway', 'N/A')}")

    print("\n실패한 케이스:")
    for r in results:
        if not r.get("success", False):
            print(f"  ❌ {r['question'][:50]}...")
            print(f"     오류: {r.get('error', 'Unknown error')}")

    return results


if __name__ == "__main__":
    test_exam_flow_api()

