"""
EXAONE + RAG 통합 테스트 스크립트

정책 기반 질문(ADVICE)에 대해 학습된 EXAONE 모델과 Neon DB RAG가
제대로 작동하는지 테스트합니다.
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.domain.admin.agents.exam_agent import ExamAgent
from backend.domain.admin.analysis.intent_classifier import ExamIntent


async def test_advice_question():
    """ADVICE 의도 질문 테스트"""

    print("=" * 60)
    print("EXAONE + RAG 통합 테스트")
    print("=" * 60)

    # 테스트 질문들
    test_questions = [
        "직장인인데 하루 4시간 공부로 합격 가능할까?",
        "전업 수험생으로 공부하는데 하루 일과를 어떻게 구성해야 할까요?",
        "국어 학습 전략이 궁금해요. 합격자들의 조언을 듣고 싶어요.",
        "영어 노베이스인데 어떻게 시작해야 할까요?",
        "1년~1년 6개월 수험기간으로는 부족한가요?",
    ]

    agent = ExamAgent()

    for i, question in enumerate(test_questions, 1):
        print(f"\n[테스트 {i}/{len(test_questions)}]")
        print(f"질문: {question}")
        print("-" * 60)

        # ADVICE 의도로 설정
        koelectra_result = {
            "intent": {
                "intent": "ADVICE",
                "confidence": 0.8
            },
            "spam_prob": 0.5
        }

        request_data = {
            "question": question
        }

        try:
            result = await agent.handle_request(
                request_text=question,
                request_data=request_data,
                koelectra_result=koelectra_result
            )

            if result.get("success"):
                answer = result.get("answer", {})
                response = answer.get("response", "응답 없음")
                sources = answer.get("sources", [])

                print(f"✅ 성공!")
                print(f"\n응답:")
                print(response)
                print(f"\n참고한 합격 수기:")
                for j, source in enumerate(sources, 1):
                    print(f"  {j}. {source.get('source')} (유사도: {source.get('similarity', 0):.2f})")
            else:
                error = result.get("error", "알 수 없는 오류")
                print(f"❌ 실패: {error}")

        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()

        print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_advice_question())

