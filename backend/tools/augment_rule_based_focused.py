"""RULE_BASED 중심 대규모 데이터 증강 스크립트

전략:
1. RULE_BASED 데이터 집중 추가 (2,000~3,000개 수준)
2. 다양한 패턴과 변형 생성
3. 유의어 교체 및 문장 구조 변형
"""

import json
import random
import sys
from pathlib import Path
from typing import List, Dict, Any

sys.stdout.reconfigure(encoding='utf-8')

# 과목 목록 (확장)
SUBJECTS = [
    "행정법총론", "행정학개론", "국어", "영어", "한국사", "회계학",
    "경제학", "세법", "민법", "형법", "상법", "국제법", "헌법",
    "지방자치론", "정책학", "조직론", "인사행정론", "재무행정론",
    "행정법", "행정학", "공직선거법", "지방세법", "국가법", "지방법"
]

EXAM_TYPES = ["국가직", "지방직", "서울시", "경찰", "소방", "국회", "법원", "검찰"]
GRADES = ["7급", "9급", "5급"]
JOB_SERIES = [
    "일반행정직", "교육행정직", "사회복지직", "보건직", "회계직",
    "세무직", "법무직", "외무직", "기술직", "전산직", "통계직",
    "공업직", "농업직", "임업직", "수산직", "환경직"
]
YEARS = [str(y) for y in range(2018, 2026)]
QUESTION_NOS = [str(i) for i in range(1, 21)]

# 동의어 사전 (확장)
SYNONYMS = {
    "정답": ["답", "답안", "정답지", "해답", "정답은", "답은"],
    "알려줘": ["알려주세요", "알려줄래", "말해줘", "말해주세요", "가르쳐줘", "알려줄 수 있나요"],
    "문제": ["문항", "문제지", "시험문제", "문제는"],
    "작년": ["작년년", "지난해", "전년도"],
    "올해": ["올해년", "금년", "이번", "올해도"],
    "재작년": ["재작년년", "전년", "그 전해"],
    "번": ["번 문제", "번 문항", "번째", "번째 문제"],
    "정답": ["정답이", "답이", "답안이"],
}

# 문장 끝 변형
ENDINGS = ["!", "?", "요", "해", "해요", "주세요", "주실 수 있나요", "부탁드려요"]


def generate_rule_based_questions(count: int) -> List[Dict[str, Any]]:
    """RULE_BASED 질문 대량 생성 (다양한 패턴)"""
    templates = [
        # 기본 패턴
        "{year}년 {exam_type} {grade} {job_series} {subject} {qno}번 정답",
        "{year}년 {exam_type} {grade} {subject} {qno}번 답안",
        "{exam_type} {grade} {subject} {qno}번 정답 뭐야?",
        "{year}년 {subject} {qno}번 문제 정답 알려줘",
        "{subject} {qno}번 정답 뭔가?",

        # 연도 변형
        "작년 {exam_type} {grade} {subject} {qno}번 정답",
        "올해 {exam_type} {grade} {job_series} {subject} {qno}번 답안",
        "작년년 {exam_type} {subject} {qno}번 정답 뭐야?",
        "올해년 {exam_type} {grade} {subject} {qno}번 답안",
        "재작년 {exam_type} {grade} {subject} {qno}번 정답",

        # 간소화 패턴
        "{year}년 {exam_type} {subject} {qno}번 정답지",
        "{exam_type} {subject} {qno}번 답 알려줘",
        "{year}년 {grade} {job_series} {subject} {qno}번",
        "{subject} {qno}번 정답 말해줘",
        "{year}년 {exam_type} {subject} {qno}번 정답 알려주세요",

        # 질문 형태 변형
        "{year}년 {exam_type} {grade} {job_series} {subject} {qno}번 문제 답은?",
        "{exam_type} {grade} {subject} {qno}번 정답이 뭐야?",
        "{year}년 {subject} {qno}번 문제의 정답은?",
        "{subject} {qno}번 문제 정답 알려줄 수 있나요?",
        "{year}년 {exam_type} {grade} {subject} {qno}번 답안이 궁금해요",

        # 추가 변형
        "{year}년도 {exam_type} {grade} {subject} {qno}번 정답",
        "{exam_type} {grade} {job_series} {subject} {qno}번 문제 답",
        "{year}년 {exam_type} {grade} {subject} {qno}번 정답지 알려줘",
        "{subject} {qno}번 정답 부탁드려요",
        "{year}년 {exam_type} {subject} {qno}번 문제의 답안은?",
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

        # 동의어 치환 (40% 확률)
        if random.random() < 0.4:
            for old, news in SYNONYMS.items():
                if old in text:
                    text = text.replace(old, random.choice(news), 1)
                    break  # 한 번만 치환

        # 문장 끝 변형 (30% 확률)
        if random.random() < 0.3 and text[-1] not in ["?", "!", "요", "해", "가", "요"]:
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
    """EXPLAIN 질문 생성"""
    templates = [
        "이 판례에서 왜 이렇게 판단했나요?",
        "행정법상 이 원칙의 법적 근거는 무엇인가요?",
        "이 경우에 행정행위가 무효인 이유를 설명해줘",
        "판례에서 이 원칙이 적용된 구체적 사례를 알려줘",
        "법리적 해석을 통해 이 문제를 어떻게 접근해야 하나요?",
    ]
    questions = []
    for i in range(count):
        text = random.choice(templates)
        questions.append({
            "instruction": "다음 시험 관련 질문을 분석하여 처리 방식을 판단하고 JSON 형식으로만 답하세요.",
            "input": {"question": text, "intent": "EXPLAIN"},
            "output": {"action": "POLICY_BASED", "reason": "복잡한 추론이 필요한 요청으로 정책 기반 처리 필요 (LLM 사용)", "confidence": 0.9, "intent": "EXPLAIN"}
        })
    return questions


def generate_advice_questions(count: int) -> List[Dict[str, Any]]:
    """ADVICE 질문 생성"""
    templates = [
        "공무원 시험 합격을 위한 효과적인 학습 방법은?",
        "직장인도 공무원 시험에 합격할 수 있나요?",
        "9급 공무원 시험 준비 기간은 얼마나 걸리나요?",
        "과목별 공부 전략을 알려줘",
        "시험 직전 준비 방법은 무엇인가요?",
    ]
    questions = []
    for i in range(count):
        text = random.choice(templates)
        questions.append({
            "instruction": "다음 시험 관련 질문을 분석하여 처리 방식을 판단하고 JSON 형식으로만 답하세요.",
            "input": {"question": text, "intent": "ADVICE"},
            "output": {"action": "POLICY_BASED", "reason": "복잡한 추론이 필요한 요청으로 정책 기반 처리 필요 (LLM 사용)", "confidence": 0.9, "intent": "ADVICE"}
        })
    return questions


def generate_block_questions(count: int) -> List[Dict[str, Any]]:
    """BLOCK 질문 생성"""
    templates = [
        "오늘 날씨 어때?", "배고파", "영화 추천해줘", "드라마 추천",
        "책 추천해줘", "음악 추천", "여행지 추천", "음식점 추천해줘",
    ]
    questions = []
    for i in range(count):
        text = random.choice(templates)
        questions.append({
            "instruction": "다음 시험 관련 질문을 분석하여 처리 방식을 판단하고 JSON 형식으로만 답하세요.",
            "input": {"question": text, "intent": "OUT_OF_DOMAIN"},
            "output": {"action": "BLOCK", "reason": "서비스 범위 밖의 질문으로 차단", "confidence": 0.95, "intent": "OUT_OF_DOMAIN"}
        })
    return questions


def generate_balanced_dataset(
    rule_based_count: int = 2000,
    policy_based_count: int = 1000,
    block_count: int = 1000
) -> List[Dict[str, Any]]:
    """균형잡힌 대규모 데이터셋 생성"""
    print(f"📊 데이터 생성 시작...")
    print(f"  RULE_BASED: {rule_based_count}개")
    print(f"  POLICY_BASED (EXPLAIN + ADVICE): {policy_based_count}개")
    print(f"  BLOCK: {block_count}개")

    rule_based = generate_rule_based_questions(rule_based_count)
    explain = generate_explain_questions(policy_based_count // 2)
    advice = generate_advice_questions(policy_based_count // 2)
    block = generate_block_questions(block_count)

    all_data = rule_based + explain + advice + block
    random.shuffle(all_data)

    return all_data


def main():
    """메인 함수"""
    output_path = Path("data/spamdata/intent_training_data_3000.gateway.sft.jsonl")

    # RULE_BASED 중심 대규모 데이터 생성
    # 총 3,000개: RULE_BASED 2,000개 (66.7%), POLICY_BASED 500개 (16.7%), BLOCK 500개 (16.7%)
    all_data = generate_balanced_dataset(
        rule_based_count=2000,
        policy_based_count=500,
        block_count=500
    )

    # JSONL로 저장
    with open(output_path, "w", encoding="utf-8") as f:
        for item in all_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    # 통계 출력
    actions = {}
    for item in all_data:
        action = item['output']['action']
        actions[action] = actions.get(action, 0) + 1

    print(f"\n✅ 데이터 생성 완료!")
    print(f"📁 저장 위치: {output_path}")
    print(f"📊 총 데이터: {len(all_data)}개")
    print(f"\n📈 클래스별 분포:")
    for action, count in sorted(actions.items()):
        print(f"  {action}: {count}개 ({count/len(all_data)*100:.1f}%)")


if __name__ == "__main__":
    main()

