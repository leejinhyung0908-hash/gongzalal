"""POLICY_BASED 데이터 증강 스크립트 (ADVICE 타입 집중)

오분류된 케이스를 분석하여 POLICY_BASED 데이터를 집중적으로 증강합니다.
특히 "방법", "전략", "계획", "추천" 등의 키워드가 포함된 ADVICE 타입 데이터를 생성합니다.
"""

import json
import random
import sys
from pathlib import Path
from typing import List, Dict, Any

# 출력 인코딩 설정 (Windows)
sys.stdout.reconfigure(encoding='utf-8')

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 과목 목록
SUBJECTS = [
    "행정법총론", "행정학개론", "국어", "영어", "한국사", "회계학",
    "경제학", "세법", "민법", "형법", "상법", "국제법", "헌법",
    "지방자치론", "정책학", "조직론", "인사행정론", "재무행정론"
]

# 시험 유형
EXAM_TYPES = ["국가직", "지방직", "서울시", "경찰", "소방"]

# 급수
GRADES = ["7급", "9급"]

# 직렬
JOB_SERIES = [
    "일반행정직", "교육행정직", "사회복지직", "보건직", "회계직",
    "세무직", "법무직", "외무직", "기술직", "전산직"
]


def generate_advice_questions_focused(count: int) -> List[Dict[str, Any]]:
    """ADVICE (POLICY_BASED) 질문 생성 - 오분류 패턴 집중"""

    # 오분류된 패턴을 기반으로 한 템플릿
    templates = [
        # "방법" 패턴
        "{grade} 공무원 시험 준비 방법 알려줘",
        "{grade} 공무원 시험 합격 방법은?",
        "공무원 시험 공부 방법 알려줘",
        "시험 준비 방법을 알려주세요",
        "효과적인 공부 방법은?",
        "합격하는 방법 알려줘",
        "시험 합격 방법을 가르쳐줘",
        "공무원 시험 준비하는 방법은?",
        "성공적인 시험 준비 방법은?",
        "효과적인 학습 방법을 알려줘",

        # "전략" 패턴
        "{subject} 공부 전략 추천해줘",
        "공무원 시험 전략 알려줘",
        "과목별 공부 전략은?",
        "시험 전략을 추천해주세요",
        "효과적인 전략을 알려줘",
        "합격 전략을 가르쳐줘",
        "공부 전략을 추천해줘",
        "시험 준비 전략은?",
        "과목별 전략을 알려줘",
        "효과적인 시험 전략은?",

        # "계획" 패턴
        "합격을 위한 학습 계획 세우는 방법은?",
        "공부 계획을 어떻게 세워야 할까요?",
        "시험 준비 계획을 알려줘",
        "학습 계획을 세우는 방법은?",
        "효과적인 공부 계획은?",
        "합격 계획을 세우고 싶어요",
        "시험 대비 계획을 알려줘",
        "공부 계획을 추천해줘",
        "학습 계획을 어떻게 세우나요?",
        "시험 준비 계획을 세우는 방법은?",

        # "추천" 패턴
        "{subject} 공부 방법 추천해줘",
        "공무원 시험 준비 추천해줘",
        "과목별 공부 방법 추천",
        "시험 준비 방법 추천해주세요",
        "효과적인 방법 추천해줘",
        "합격 방법 추천",
        "공부 방법을 추천해주세요",
        "시험 대비 방법 추천",
        "학습 방법 추천해줘",
        "준비 방법 추천해주세요",

        # "팁", "조언" 패턴
        "공무원 시험 합격 팁 알려줘",
        "시험 준비 팁을 알려주세요",
        "공부 팁 추천해줘",
        "합격 팁을 가르쳐줘",
        "시험 대비 팁은?",
        "효과적인 팁을 알려줘",
        "공무원 시험 조언해줘",
        "시험 준비 조언을 구해요",
        "공부 조언을 알려줘",
        "합격 조언을 해주세요",

        # "어떻게" 패턴
        "공무원 시험 어떻게 준비하나요?",
        "시험을 어떻게 공부해야 할까요?",
        "합격하려면 어떻게 해야 하나요?",
        "공부를 어떻게 시작해야 할까요?",
        "시험 준비를 어떻게 해야 하나요?",
        "효과적으로 어떻게 공부하나요?",
        "시험 대비를 어떻게 해야 할까요?",
        "공부를 어떻게 계획해야 하나요?",
        "시험을 어떻게 대비해야 하나요?",
        "합격을 위해 어떻게 해야 하나요?",

        # "가능할까" 패턴
        "직장인인데 하루 4시간 공부로 합격 가능할까?",
        "3개월 준비로 합격 가능할까요?",
        "직장 다니면서 합격 가능할까?",
        "짧은 기간에 합격 가능한가요?",
        "늦게 시작해도 합격 가능할까요?",
        "직장인도 합격 가능한가요?",
        "시간이 부족한데 합격 가능할까?",
        "공부 시간이 적어도 합격 가능할까요?",
        "늦은 나이에 합격 가능할까?",
        "직장과 병행하며 합격 가능한가요?",

        # "기간", "시간" 패턴
        "{grade} 공무원 시험 준비 기간은 얼마나 걸리나요?",
        "시험 준비 기간을 알려줘",
        "공부 기간은 얼마나 필요한가요?",
        "합격까지 걸리는 기간은?",
        "시험 대비 기간을 추천해줘",
        "공부 시간을 어떻게 분배해야 하나요?",
        "하루 공부 시간은 얼마나 해야 하나요?",
        "효과적인 공부 시간은?",
        "시험 준비 시간을 알려줘",
        "공부 시간 계획을 세우는 방법은?",
    ]

    # 문장 끝 변형
    endings = ["", "요", "해요", "주세요", "해주세요", "알려줘", "알려주세요"]

    questions = []
    for i in range(count):
        template = random.choice(templates)

        # 템플릿 변수 치환
        if "{grade}" in template:
            template = template.replace("{grade}", random.choice(GRADES))
        if "{subject}" in template:
            template = template.replace("{subject}", random.choice(SUBJECTS))

        text = template

        # 문장 끝 변형 (30% 확률)
        if random.random() < 0.3:
            ending = random.choice(endings)
            if ending and not text.endswith(ending):
                if text.endswith("?"):
                    text = text[:-1] + ending + "?"
                elif text.endswith("."):
                    text = text[:-1] + ending + "."
                else:
                    text = text + ending

        # 약간의 변형 (20% 확률)
        if random.random() < 0.2:
            if "알려줘" in text:
                text = text.replace("알려줘", random.choice(["알려주세요", "알려줄래", "가르쳐줘", "말해줘"]))
            if "추천해줘" in text:
                text = text.replace("추천해줘", random.choice(["추천해주세요", "추천해줄래", "추천해줘요"]))
            if "방법은" in text:
                text = text.replace("방법은", random.choice(["방법이", "방법을", "방법"]))

        questions.append({
            "instruction": "다음 시험 관련 질문을 분석하여 처리 방식을 판단하고 JSON 형식으로만 답하세요.",
            "input": {
                "question": text,
                "intent": "ADVICE"
            },
            "output": {
                "action": "POLICY_BASED",
                "reason": "복잡한 추론이 필요한 학습 상담 요청으로 정책 기반 처리 필요 (LLM 사용)",
                "confidence": 0.95,
                "intent": "ADVICE"
            }
        })

    return questions


def generate_explain_questions_focused(count: int) -> List[Dict[str, Any]]:
    """EXPLAIN (POLICY_BASED) 질문 생성"""

    templates = [
        "신뢰보호의 원칙이 이 판례에서 왜 적용 안 돼?",
        "행정법에서 신뢰보호의 원칙의 의미를 설명해줘",
        "이 문제에서 행정행위의 하자의 치유가 가능한 이유는?",
        "판례에서 이 원칙이 적용된 사례를 설명해줘",
        "이 법리 적용 근거를 설명해줘",
        "왜 이렇게 판단했는지 설명해줘",
        "이 원칙의 적용 요건은?",
        "이 판례의 법리를 설명해줘",
        "이 문제의 해결 방법을 설명해줘",
        "이 법조문의 의미를 설명해줘",
    ]

    questions = []
    for i in range(count):
        text = random.choice(templates)
        questions.append({
            "instruction": "다음 시험 관련 질문을 분석하여 처리 방식을 판단하고 JSON 형식으로만 답하세요.",
            "input": {
                "question": text,
                "intent": "EXPLAIN"
            },
            "output": {
                "action": "POLICY_BASED",
                "reason": "복잡한 추론이 필요한 해설 요청으로 정책 기반 처리 필요 (LLM 사용)",
                "confidence": 0.95,
                "intent": "EXPLAIN"
            }
        })

    return questions


def main():
    """POLICY_BASED 데이터 증강"""

    # 생성할 데이터 수
    ADVICE_COUNT = 1000  # ADVICE 타입 집중
    EXPLAIN_COUNT = 200  # EXPLAIN 타입

    print("📊 POLICY_BASED 데이터 증강 시작...")
    print(f"  ADVICE: {ADVICE_COUNT}개")
    print(f"  EXPLAIN: {EXPLAIN_COUNT}개")

    # 데이터 생성
    advice_questions = generate_advice_questions_focused(ADVICE_COUNT)
    explain_questions = generate_explain_questions_focused(EXPLAIN_COUNT)

    all_questions = advice_questions + explain_questions

    # 출력 파일 경로
    output_path = Path("data/spamdata/intent_training_data_policy_based_augmented.jsonl")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # JSONL 형식으로 저장
    with open(output_path, "w", encoding="utf-8") as f:
        for item in all_questions:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"\n✅ 데이터 생성 완료!")
    print(f"📁 저장 위치: {output_path}")
    print(f"📊 총 데이터: {len(all_questions)}개")
    print(f"\n📈 클래스별 분포:")
    print(f"  ADVICE: {len(advice_questions)}개 ({len(advice_questions)/len(all_questions)*100:.1f}%)")
    print(f"  EXPLAIN: {len(explain_questions)}개 ({len(explain_questions)/len(all_questions)*100:.1f}%)")


if __name__ == "__main__":
    main()

