"""게이트웨이 분류기 테스트 스크립트

학습된 모델이 제대로 작동하는지 다양한 케이스로 테스트합니다.
"""

import json
import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

sys.stdout.reconfigure(encoding='utf-8')

from backend.domain.admin.agents.analysis.spam_detector import mcp_tool_koelectra_gateway_classifier


def test_gateway_classifier():
    """게이트웨이 분류기 테스트"""

    test_cases = [
        # RULE_BASED 케이스
        ("2025년 국가직 행정법총론 3번 알려줘", "RULE_BASED"),
        ("2024년 지방직 9급 한국사 10번 정답", "RULE_BASED"),
        ("작년 국가직 7급 회계학 5번 답안", "RULE_BASED"),
        ("행정학개론 2번 정답 알려줘", "RULE_BASED"),

        # POLICY_BASED (EXPLAIN) 케이스
        ("신뢰보호의 원칙이 이 판례에서 왜 적용 안 돼?", "POLICY_BASED"),
        ("행정법에서 신뢰보호의 원칙의 의미를 설명해줘", "POLICY_BASED"),
        ("이 문제에서 행정행위의 하자의 치유가 가능한 이유는?", "POLICY_BASED"),
        ("판례에서 이 원칙이 적용된 사례를 설명해줘", "POLICY_BASED"),

        # POLICY_BASED (ADVICE) 케이스
        ("직장인인데 하루 4시간 공부로 합격 가능할까?", "POLICY_BASED"),
        ("9급 공무원 시험 준비 방법 알려줘", "POLICY_BASED"),
        ("행정법 공부 전략 추천해줘", "POLICY_BASED"),
        ("합격을 위한 학습 계획 세우는 방법은?", "POLICY_BASED"),

        # BLOCK 케이스
        ("오늘 날씨 어때?", "BLOCK"),
        ("배고파", "BLOCK"),
        ("영화 추천해줘", "BLOCK"),
        ("드라마 추천", "BLOCK"),
    ]

    print("=" * 60)
    print("게이트웨이 분류기 테스트 시작")
    print("=" * 60)

    results = []
    correct = 0
    total = len(test_cases)

    for question, expected in test_cases:
        result = mcp_tool_koelectra_gateway_classifier.invoke({"text": question})

        predicted = result.get("gateway", "UNKNOWN")
        confidence = result.get("confidence", 0.0)
        probabilities = result.get("probabilities", [])

        is_correct = predicted == expected
        if is_correct:
            correct += 1

        status = "✅" if is_correct else "❌"
        results.append({
            "question": question,
            "expected": expected,
            "predicted": predicted,
            "confidence": confidence,
            "correct": is_correct
        })

        print(f"\n{status} 질문: {question}")
        print(f"   예상: {expected}, 예측: {predicted}, 신뢰도: {confidence:.3f}")
        if probabilities:
            print(f"   확률: RULE_BASED={probabilities[0]:.3f}, POLICY_BASED={probabilities[1]:.3f}, BLOCK={probabilities[2]:.3f}")

    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    print(f"전체: {total}개")
    print(f"정확: {correct}개")
    print(f"오류: {total - correct}개")
    print(f"정확도: {correct/total*100:.1f}%")

    print("\n클래스별 정확도:")
    for gateway in ["RULE_BASED", "POLICY_BASED", "BLOCK"]:
        gateway_cases = [r for r in results if r["expected"] == gateway]
        gateway_correct = sum(1 for r in gateway_cases if r["correct"])
        if gateway_cases:
            print(f"  {gateway}: {gateway_correct}/{len(gateway_cases)} ({gateway_correct/len(gateway_cases)*100:.1f}%)")

    print("\n오분류 케이스:")
    for r in results:
        if not r["correct"]:
            print(f"  ❌ '{r['question']}'")
            print(f"     예상: {r['expected']}, 예측: {r['predicted']}, 신뢰도: {r['confidence']:.3f}")

    return results


if __name__ == "__main__":
    test_gateway_classifier()

