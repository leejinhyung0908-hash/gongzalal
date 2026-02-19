"""게이트웨이 학습 데이터 증강 스크립트

기존 데이터와 다른 패턴으로 새로운 데이터 400개를 생성합니다.
균형잡힌 분포를 위해:
- RULE_BASED: 133개 (33.3%)
- POLICY_BASED: 133개 (33.3%) - EXPLAIN 67개, ADVICE 66개
- BLOCK: 134개 (33.4%)
"""

import json
import random
import sys
from pathlib import Path
from typing import List, Dict, Any

# 출력 인코딩 설정 (Windows)
sys.stdout.reconfigure(encoding='utf-8')

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

# 연도
YEARS = ["2020", "2021", "2022", "2023", "2024", "2025"]

# 문항번호
QUESTION_NOS = [str(i) for i in range(1, 21)]

# 동의어
SYNONYMS = {
    "정답": ["답", "답안", "정답지", "해답"],
    "알려줘": ["알려주세요", "알려줄래", "말해줘", "말해주세요", "가르쳐줘"],
    "문제": ["문항", "문제지"],
    "작년": ["작년년", "지난해"],
    "올해": ["올해년", "금년", "이번"],
    "재작년": ["재작년년", "전년"],
}

# 문장 끝 변형
ENDINGS = ["!", "?", "요", "해", "해요", "주세요"]


def generate_rule_based_questions(count: int) -> List[Dict[str, Any]]:
    """RULE_BASED (DB_QUERY) 질문 생성"""
    templates = [
        "{year}년 {exam_type} {grade} {job_series} {subject} {qno}번 정답",
        "{year}년 {exam_type} {grade} {subject} {qno}번 답안",
        "{exam_type} {grade} {subject} {qno}번 정답 뭐야?",
        "{year}년 {subject} {qno}번 문제 정답 알려줘",
        "{subject} {qno}번 정답 뭔가?",
        "작년 {exam_type} {grade} {subject} {qno}번 정답",
        "올해 {exam_type} {grade} {job_series} {subject} {qno}번 답안",
        "{year}년 {exam_type} {subject} {qno}번 정답지",
        "{exam_type} {subject} {qno}번 답 알려줘",
        "{year}년 {grade} {job_series} {subject} {qno}번",
        "작년년 {exam_type} {subject} {qno}번 정답 뭐야?",
        "올해년 {exam_type} {grade} {subject} {qno}번 답안",
        "{year}년 {exam_type} {grade} {job_series} {subject} {qno}번 문제 답",
        "{subject} {qno}번 정답 말해줘",
        "{year}년 {exam_type} {subject} {qno}번 정답 알려주세요",
    ]

    questions = []
    for i in range(count):
        template = random.choice(templates)

        # 변수 치환
        text = template.format(
            year=random.choice(YEARS),
            exam_type=random.choice(EXAM_TYPES),
            grade=random.choice(GRADES),
            job_series=random.choice(JOB_SERIES) if "{job_series}" in template else "",
            subject=random.choice(SUBJECTS),
            qno=random.choice(QUESTION_NOS)
        )

        # 공백 정리
        text = " ".join(text.split())

        # 동의어 치환 (30% 확률)
        if random.random() < 0.3:
            for old, news in SYNONYMS.items():
                if old in text:
                    text = text.replace(old, random.choice(news), 1)

        # 문장 끝 변형 (20% 확률)
        if random.random() < 0.2 and text[-1] not in ["?", "!", "요", "해", "가"]:
            text += random.choice(ENDINGS)

        questions.append({
            "instruction": "다음 시험 관련 질문을 분석하여 처리 방식을 판단하고 JSON 형식으로만 답하세요.",
            "input": {
                "question": text,
                "intent": "DB_QUERY"
            },
            "output": {
                "action": "RULE_BASED",
                "reason": "명확한 데이터 조회 요청으로 규칙 기반 처리 가능",
                "confidence": 0.95,
                "intent": "DB_QUERY"
            }
        })

    return questions


def generate_explain_questions(count: int) -> List[Dict[str, Any]]:
    """EXPLAIN (POLICY_BASED) 질문 생성"""
    templates = [
        "이 판례에서 왜 이렇게 판단했나요?",
        "행정법상 이 원칙의 법적 근거는 무엇인가요?",
        "이 경우에 행정행위가 무효인 이유를 설명해줘",
        "판례에서 이 원칙이 적용된 구체적 사례를 알려줘",
        "법리적 해석을 통해 이 문제를 어떻게 접근해야 하나요?",
        "이 원칙이 적용되기 위한 요건은 무엇인가요?",
        "실무에서 이 원칙이 어떻게 적용되는지 설명해줘",
        "이 원칙의 한계와 예외는 무엇인가요?",
        "행정법상 이 개념의 의미를 자세히 설명해줘",
        "이 판례의 법리를 구체적으로 설명해주세요",
        "왜 이 경우에 행정행위의 하자가 치유 가능한가요?",
        "이 원칙과 다른 원칙의 관계는 어떻게 되나요?",
        "판례에서 이 원칙이 적용되지 않은 사례는 무엇인가요?",
        "이 문제의 해결을 위한 법리적 접근 방법은?",
        "행정법상 이 원칙의 실효성은 어떻게 보장되나요?",
        "이 판례의 판단 기준을 설명해줘",
        "이 원칙이 행정법 체계에서 차지하는 위치는?",
        "이 경우에 법원이 취한 입장을 설명해줘",
        "이 원칙의 입법 취지와 목적은 무엇인가요?",
        "이 문제에서 적용되는 법리를 단계별로 설명해줘",
    ]

    questions = []
    for i in range(count):
        text = random.choice(templates)

        # 약간의 변형 (50% 확률)
        if random.random() < 0.5:
            variations = []
            if "설명해줘" in text:
                variations.append(text.replace("설명해줘", random.choice(["설명해주세요", "설명해줄래", "설명해", "가르쳐줘"])))
            if "왜" in text:
                variations.append(text.replace("왜", random.choice(["어떻게", "무엇 때문에", "어떤 이유로", "어떻게 해서"])))
            if "이 " in text and "이번" not in text and "이런" not in text:
                variations.append(text.replace("이 ", random.choice(["이번 ", "해당 ", "이런 ", "이러한 "])))
            if "이 원칙" in text:
                variations.append(text.replace("이 원칙", random.choice(["이 원칙", "해당 원칙", "이런 원칙"])))
            if "이 판례" in text:
                variations.append(text.replace("이 판례", random.choice(["이 판례", "해당 판례", "이런 판례"])))

            if variations:
                valid_variations = [v for v in variations if v != text]
                if valid_variations:
                    text = random.choice(valid_variations)

        questions.append({
            "instruction": "다음 시험 관련 질문을 분석하여 처리 방식을 판단하고 JSON 형식으로만 답하세요.",
            "input": {
                "question": text,
                "intent": "EXPLAIN"
            },
            "output": {
                "action": "POLICY_BASED",
                "reason": "복잡한 추론이 필요한 요청으로 정책 기반 처리 필요 (LLM 사용)",
                "confidence": 0.9,
                "intent": "EXPLAIN"
            }
        })

    return questions


def generate_advice_questions(count: int) -> List[Dict[str, Any]]:
    """ADVICE (POLICY_BASED) 질문 생성"""
    templates = [
        "공무원 시험 합격을 위한 효과적인 학습 방법은?",
        "직장인도 공무원 시험에 합격할 수 있나요?",
        "9급 공무원 시험 준비 기간은 얼마나 걸리나요?",
        "과목별 공부 전략을 알려줘",
        "시험 직전 준비 방법은 무엇인가요?",
        "합격률을 높이는 구체적인 팁은?",
        "공부 시간을 어떻게 분배해야 하나요?",
        "효과적인 공부 습관을 만드는 방법은?",
        "행정법 과목 공부 전략을 추천해줘",
        "합격을 위한 학습 계획을 세우는 방법은?",
        "직장인인데 하루 4시간 공부로 합격 가능할까?",
        "어떤 과목부터 공부해야 할까요?",
        "시험 준비 기간 동안 어떻게 관리해야 하나요?",
        "공부 효율을 높이는 방법은?",
        "합격생들의 공부 패턴은 어떤가요?",
        "시험 직전 며칠 전략을 알려줘",
        "과목별 난이도와 공부 비중은 어떻게 정하나요?",
        "공부할 때 집중력을 높이는 방법은?",
        "시험 당일 컨디션 관리 방법은?",
        "합격을 위한 필수 준비사항은 무엇인가요?",
    ]

    questions = []
    for i in range(count):
        text = random.choice(templates)

        # 약간의 변형 (50% 확률)
        if random.random() < 0.5:
            variations = []
            if "알려줘" in text:
                variations.append(text.replace("알려줘", random.choice(["알려주세요", "알려줄래", "가르쳐줘"])))
            if "방법은" in text:
                variations.append(text.replace("방법은", random.choice(["방법이", "방법을"])))
            if "어떻게" in text:
                variations.append(text.replace("어떻게", random.choice(["어떤 방식으로", "무엇을"])))
            if "합격" in text:
                variations.append(text.replace("합격", random.choice(["시험 합격", "시험 통과"])))

            if variations:
                valid_variations = [v for v in variations if v != text]
                if valid_variations:
                    text = random.choice(valid_variations)

        questions.append({
            "instruction": "다음 시험 관련 질문을 분석하여 처리 방식을 판단하고 JSON 형식으로만 답하세요.",
            "input": {
                "question": text,
                "intent": "ADVICE"
            },
            "output": {
                "action": "POLICY_BASED",
                "reason": "복잡한 추론이 필요한 요청으로 정책 기반 처리 필요 (LLM 사용)",
                "confidence": 0.9,
                "intent": "ADVICE"
            }
        })

    return questions


def generate_block_questions(count: int) -> List[Dict[str, Any]]:
    """BLOCK (OUT_OF_DOMAIN) 질문 생성"""
    templates = [
        "오늘 날씨 어때?",
        "배고파",
        "영화 추천해줘",
        "드라마 추천",
        "책 추천해줘",
        "음악 추천",
        "여행지 추천",
        "음식점 추천해줘",
        "카페 추천해줘",
        "쇼핑몰 추천",
        "운동하고 싶어",
        "게임하고 싶어",
        "심심해",
        "주말 뭐하지?",
        "취미 추천해줘",
        "오늘 뭐 먹지?",
        "내일 날씨는?",
        "영화관 추천해줘",
        "맛집 추천",
        "카페 메뉴 추천해줘",
        "운동 뭐하지?",
        "게임 추천",
        "책 읽고 싶어",
        "드라마 뭐 볼까?",
        "음악 듣고 싶어",
        "여행 가고 싶어",
        "맛있는 거 먹고 싶어",
        "카페 가고 싶어",
        "쇼핑하고 싶어",
        "놀고 싶어",
    ]

    questions = []
    for i in range(count):
        text = random.choice(templates)

        # 약간의 변형 (30% 확률)
        if random.random() < 0.3:
            variations = []
            if "추천해줘" in text:
                variations.append(text.replace("추천해줘", random.choice(["추천해주세요", "추천해줄래", "추천"])))
            if "하고 싶어" in text:
                variations.append(text.replace("하고 싶어", random.choice(["하고 싶다", "하고 싶네"])))
            if "어때?" in text:
                variations.append(text.replace("어때?", random.choice(["어때요?", "어떤가?"])))

            if variations:
                valid_variations = [v for v in variations if v != text]
                if valid_variations:
                    text = random.choice(valid_variations)

        questions.append({
            "instruction": "다음 시험 관련 질문을 분석하여 처리 방식을 판단하고 JSON 형식으로만 답하세요.",
            "input": {
                "question": text,
                "intent": "OUT_OF_DOMAIN"
            },
            "output": {
                "action": "BLOCK",
                "reason": "서비스 범위 밖의 질문으로 차단",
                "confidence": 0.95,
                "intent": "OUT_OF_DOMAIN"
            }
        })

    return questions


def main():
    """메인 함수"""
    output_path = Path("data/spamdata/intent_training_data_400.gateway.sft.augmented.jsonl")

    # 균형잡힌 데이터 생성
    rule_based = generate_rule_based_questions(133)  # RULE_BASED: 33.3%
    explain = generate_explain_questions(67)  # EXPLAIN: 16.75%
    advice = generate_advice_questions(66)  # ADVICE: 16.5%
    block = generate_block_questions(134)  # BLOCK: 33.5%

    # 모든 데이터 합치기
    all_data = rule_based + explain + advice + block

    # 셔플
    random.shuffle(all_data)

    # JSONL로 저장
    with open(output_path, "w", encoding="utf-8") as f:
        for item in all_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    # 통계 출력
    print(f"✅ 데이터 증강 완료!")
    print(f"📁 저장 위치: {output_path}")
    print(f"📊 총 데이터: {len(all_data)}개")
    print(f"\n📈 클래스별 분포:")
    print(f"  RULE_BASED: {len(rule_based)}개 ({len(rule_based)/len(all_data)*100:.1f}%)")
    print(f"  POLICY_BASED (EXPLAIN): {len(explain)}개 ({len(explain)/len(all_data)*100:.1f}%)")
    print(f"  POLICY_BASED (ADVICE): {len(advice)}개 ({len(advice)/len(all_data)*100:.1f}%)")
    print(f"  BLOCK: {len(block)}개 ({len(block)/len(all_data)*100:.1f}%)")
    print(f"\n  POLICY_BASED 총합: {len(explain) + len(advice)}개 ({(len(explain) + len(advice))/len(all_data)*100:.1f}%)")


if __name__ == "__main__":
    main()

