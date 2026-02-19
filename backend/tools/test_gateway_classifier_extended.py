"""게이트웨이 분류기 확장 테스트 스크립트

과적합 검증을 위해 학습 데이터에 없는 새로운 케이스로 테스트합니다.
"""

import json
import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

sys.stdout.reconfigure(encoding='utf-8')

from backend.domain.admin.agents.analysis.spam_detector import mcp_tool_koelectra_gateway_classifier


def test_gateway_classifier_extended():
    """게이트웨이 분류기 확장 테스트 (과적합 검증)"""

    # 학습 데이터에 없는 새로운 케이스들
    test_cases = [
        # RULE_BASED 케이스 (새로운 변형)
        ("2023년 국가직 7급 행정법 15번 정답 뭐야?", "RULE_BASED"),
        ("2022년 지방직 9급 국어 7번 답안 알려줘", "RULE_BASED"),
        ("2021년 국가직 회계학 12번 정답", "RULE_BASED"),
        ("2020년 지방직 9급 한국사 5번 답", "RULE_BASED"),
        ("2026년 국가직 행정학개론 8번 정답 알려줘", "RULE_BASED"),
        ("2024년 서울시 9급 행정법총론 3번 정답", "RULE_BASED"),
        ("2023년 경찰 행정법 10번 답안", "RULE_BASED"),
        ("2022년 소방 행정학 6번 정답", "RULE_BASED"),

        # POLICY_BASED (EXPLAIN) - 새로운 변형
        ("이 법리 적용 근거를 자세히 설명해줘", "POLICY_BASED"),
        ("왜 이렇게 판단했는지 법리를 설명해줘", "POLICY_BASED"),
        ("이 원칙의 적용 요건은 무엇인가요?", "POLICY_BASED"),
        ("이 판례의 법리적 의미는?", "POLICY_BASED"),
        ("이 문제의 해결 방법을 법리적으로 설명해줘", "POLICY_BASED"),
        ("이 법조문의 해석 방법은?", "POLICY_BASED"),
        ("이 원칙이 적용되지 않는 경우는?", "POLICY_BASED"),
        ("이 판례와 유사한 사례를 설명해줘", "POLICY_BASED"),

        # POLICY_BASED (ADVICE) - 새로운 변형
        ("공무원 시험 합격을 위한 효과적인 방법은?", "POLICY_BASED"),
        ("시험 준비 기간은 얼마나 걸리나요?", "POLICY_BASED"),
        ("과목별 공부 비중을 어떻게 정하나요?", "POLICY_BASED"),
        ("시험 직전 며칠 전략을 알려줘", "POLICY_BASED"),
        ("공부 효율을 높이는 방법은?", "POLICY_BASED"),
        ("합격생들의 공부 패턴은 어떤가요?", "POLICY_BASED"),
        ("시험 당일 컨디션 관리 방법은?", "POLICY_BASED"),
        ("공부할 때 집중력을 높이는 방법은?", "POLICY_BASED"),

        # BLOCK 케이스 - 새로운 변형
        ("오늘 점심 뭐 먹을까?", "BLOCK"),
        ("내일 날씨는?", "BLOCK"),
        ("요즘 인기 드라마 추천", "BLOCK"),
        ("좋은 책 추천해줘", "BLOCK"),
        ("여행지 추천", "BLOCK"),
        ("맛집 추천해줘", "BLOCK"),
        ("운동 추천", "BLOCK"),
        ("취미 생활 추천", "BLOCK"),

        # 경계 케이스 (애매한 경우)
        ("행정법 문제 풀이 방법", "POLICY_BASED"),  # 방법이지만 해설 요청일 수 있음
        ("2024년 행정법 문제", "RULE_BASED"),  # 문항번호 없지만 명확한 조회 의도
        ("공무원 시험 정보", "POLICY_BASED"),  # 정보 요청이지만 상담일 수 있음
        ("시험 문제", "RULE_BASED"),  # 매우 짧지만 조회 의도
    ]

    print("=" * 60)
    print("게이트웨이 분류기 확장 테스트 (과적합 검증)")
    print("=" * 60)
    print("⚠️  학습 데이터에 없는 새로운 케이스로 테스트합니다.\n")

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

        print(f"{status} 질문: {question}")
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
    error_count = 0
    for r in results:
        if not r["correct"]:
            error_count += 1
            print(f"  ❌ '{r['question']}'")
            print(f"     예상: {r['expected']}, 예측: {r['predicted']}, 신뢰도: {r['confidence']:.3f}")

    if error_count == 0:
        print("  없음 (모든 케이스 정확)")

    # 과적합 가능성 평가
    print("\n" + "=" * 60)
    print("과적합 가능성 평가")
    print("=" * 60)

    if correct / total >= 0.95:
        print("⚠️  높은 정확도 (95% 이상)")
        print("   - 학습 데이터와 유사한 패턴일 가능성")
        print("   - 실제 다양한 케이스로 추가 검증 권장")
    elif correct / total >= 0.85:
        print("✅ 양호한 정확도 (85-95%)")
        print("   - 일반화 성능이 양호한 것으로 보임")
    else:
        print("❌ 낮은 정확도 (85% 미만)")
        print("   - 과적합 가능성 또는 데이터 부족")

    # 신뢰도 분석
    confidences = [r["confidence"] for r in results if r["correct"]]
    if confidences:
        avg_confidence = sum(confidences) / len(confidences)
        print(f"\n평균 신뢰도 (정확한 예측): {avg_confidence:.3f}")
        if avg_confidence > 0.95:
            print("⚠️  매우 높은 신뢰도 - 과적합 가능성 있음")
        elif avg_confidence > 0.85:
            print("✅ 적절한 신뢰도")
        else:
            print("⚠️  낮은 신뢰도 - 모델이 불확실함")

    return results


if __name__ == "__main__":
    test_gateway_classifier_extended()

