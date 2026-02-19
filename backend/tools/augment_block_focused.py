"""BLOCK 데이터 증강 스크립트

BLOCK 클래스의 정확도를 높이기 위해 다양한 도메인 외 질문을 생성합니다.
"""

import json
import random
import sys
from pathlib import Path
from typing import List, Dict, Any

sys.stdout.reconfigure(encoding='utf-8')

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def generate_block_questions_focused(count: int) -> List[Dict[str, Any]]:
    """BLOCK (OUT_OF_DOMAIN) 질문 생성 - 다양한 패턴"""

    templates = [
        # 날씨 관련
        "오늘 날씨 어때?",
        "내일 날씨는?",
        "주말 날씨 알려줘",
        "비 올까요?",
        "날씨가 어떤가요?",

        # 음식 관련
        "오늘 점심 뭐 먹을까?",
        "저녁 메뉴 추천",
        "맛집 추천해줘",
        "배고파",
        "배고픈데 뭐 먹지?",
        "좋은 식당 알려줘",

        # 엔터테인먼트
        "영화 추천해줘",
        "드라마 추천",
        "요즘 인기 드라마",
        "좋은 영화 알려줘",
        "책 추천",
        "좋은 책 추천해줘",
        "음악 추천",
        "노래 추천해줘",

        # 쇼핑/생활
        "쇼핑몰 추천",
        "옷 추천해줘",
        "선물 추천",
        "생일 선물 뭐가 좋을까?",

        # 여행/취미
        "여행지 추천",
        "좋은 여행지 알려줘",
        "운동 추천",
        "취미 생활 추천",
        "취미 뭐가 좋을까?",

        # 일반 대화
        "안녕하세요",
        "반가워요",
        "고마워요",
        "잘 지내?",
        "뭐해?",
        "어디야?",
        "지금 몇 시야?",

        # 기술/IT (시험과 무관)
        "컴퓨터 추천해줘",
        "스마트폰 추천",
        "노트북 추천해줘",
        "프로그래밍 배우고 싶어",

        # 건강/의료
        "다이어트 방법 알려줘",
        "운동 방법 추천",
        "건강 관리 방법은?",

        # 금융/투자
        "주식 추천",
        "투자 방법 알려줘",
        "저축 방법은?",

        # 교육 (시험과 무관)
        "영어 공부 방법",
        "코딩 배우는 방법",
        "언어 학습 방법",

        # 애매한 케이스 (시험 관련이지만 도메인 외)
        "공무원 시험 언제 보나요?",  # 일정 문의는 도메인 외
        "공무원 시험 접수는 어디서 하나요?",  # 접수 문의는 도메인 외
        "공무원 시험 비용은 얼마인가요?",  # 비용 문의는 도메인 외
    ]

    # 문장 끝 변형
    endings = ["", "요", "해요", "주세요", "해주세요", "알려줘", "알려주세요", "?", "!"]

    questions = []
    for i in range(count):
        template = random.choice(templates)
        text = template

        # 문장 끝 변형 (30% 확률)
        if random.random() < 0.3:
            ending = random.choice(endings)
            if ending and not text.endswith(ending):
                if text.endswith("?"):
                    text = text[:-1] + ending
                elif text.endswith("!"):
                    text = text[:-1] + ending
                elif not text.endswith(("요", "해요", "주세요", "해주세요", "알려줘", "알려주세요")):
                    text = text + ending

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
    """BLOCK 데이터 증강"""

    # 생성할 데이터 수
    BLOCK_COUNT = 1000  # BLOCK 타입 집중

    print("📊 BLOCK 데이터 증강 시작...")
    print(f"  BLOCK: {BLOCK_COUNT}개")

    # 데이터 생성
    block_questions = generate_block_questions_focused(BLOCK_COUNT)

    # 출력 파일 경로
    output_path = Path("data/spamdata/intent_training_data_block_augmented.jsonl")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # JSONL 형식으로 저장
    with open(output_path, "w", encoding="utf-8") as f:
        for item in block_questions:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"\n✅ 데이터 생성 완료!")
    print(f"📁 저장 위치: {output_path}")
    print(f"📊 총 데이터: {len(block_questions)}개")


if __name__ == "__main__":
    main()

