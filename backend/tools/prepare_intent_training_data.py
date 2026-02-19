#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
의도 분류 학습 데이터 준비 스크립트

실제 사용자 질문 데이터를 수집하고 레이블링하여 학습 데이터셋을 생성합니다.

사용법:
    # 1. 데이터 수집 (DB에서 실제 질문 가져오기)
    python prepare_intent_training_data.py collect --output data/raw_questions.jsonl

    # 2. 레이블링 (수동 또는 자동)
    python prepare_intent_training_data.py label --input data/raw_questions.jsonl --output data/labeled_questions.jsonl

    # 3. 검증 및 통계
    python prepare_intent_training_data.py stats --input data/labeled_questions.jsonl
"""

import argparse
import json
import re
from pathlib import Path
from typing import List, Dict, Any
from collections import Counter

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.dependencies import get_db_connection
from backend.domain.admin.agents.analysis.intent_classifier import classify_intent_rule_based
from backend.domain.admin.agents.analysis.entity_extractor import extract_all_entities


INTENT_LABELS = ["DB_QUERY", "EXPLAIN", "ADVICE", "OUT_OF_DOMAIN"]


def collect_questions_from_db(output_path: str, limit: int = 1000):
    """DB에서 실제 질문 수집

    exam_questions 테이블이나 로그에서 질문을 수집합니다.
    """
    conn = get_db_connection()

    # 예시: 실제 질문이 저장된 테이블이 있다면
    # 여기서는 예시 데이터를 생성합니다.

    questions = []

    # 실제 구현: DB에서 질문 가져오기
    # with conn.cursor() as cur:
    #     cur.execute("SELECT question_text FROM user_questions ORDER BY created_at DESC LIMIT %s", (limit,))
    #     for row in cur.fetchall():
    #         questions.append({"text": row[0], "intent": None})

    # 예시 데이터 생성 (실제로는 DB에서 가져와야 함)
    example_questions = [
        # DB_QUERY 예시
        "2024년 지방직 9급 교육행정직 회계학 3번 정답 뭐야?",
        "작년 국가직 행정법총론 5번 문제 정답 알려줘",
        "2023년 지방직 7급 일반행정직 영어 10번",
        "올해 국가직 9급 국어 1번 정답",

        # EXPLAIN 예시
        "신뢰보호의 원칙이 이 판례에서 왜 적용 안 돼?",
        "행정법에서 신뢰보호의 원칙의 의미를 설명해줘",
        "이 문제에서 행정행위의 하자의 치유가 가능한 이유는?",
        "판례에서 이 원칙이 적용된 사례를 설명해줘",

        # ADVICE 예시
        "직장인인데 하루 4시간 공부로 합격 가능할까?",
        "9급 공무원 시험 준비 방법 알려줘",
        "행정법 공부 전략 추천해줘",
        "합격을 위한 학습 계획 세우는 방법은?",

        # OUT_OF_DOMAIN 예시
        "오늘 날씨 어때?",
        "배고파",
        "영화 추천해줘",
    ]

    for text in example_questions:
        questions.append({"text": text, "intent": None})

    # JSONL로 저장
    with open(output_path, "w", encoding="utf-8") as f:
        for q in questions:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")

    print(f"수집된 질문: {len(questions)}개")
    print(f"저장 위치: {output_path}")


def auto_label_questions(input_path: str, output_path: str):
    """규칙 기반으로 자동 레이블링

    실제로는 수동 검토가 필요하지만, 초기 레이블링을 위해 사용합니다.
    """
    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"경고: DB 연결 실패 ({e}). 엔티티 추출 없이 레이블링합니다.")
        conn = None

    labeled = []
    unlabeled = []

    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            text = data.get("text", "").strip()

            if not text:
                continue

            # 이미 레이블이 있으면 그대로 사용
            if data.get("intent"):
                labeled.append(data)
                continue

            # 규칙 기반으로 자동 레이블링
            if conn:
                entities = extract_all_entities(text, conn)
            else:
                # DB 연결 없이 기본 엔티티 구조 생성
                from datetime import datetime
                entities = {
                    "year": None,
                    "exam_type": None,
                    "grade": None,
                    "subject": None,
                    "question_no": None,
                    "job_series": None,
                    "has_all_required": False
                }
            intent_result = classify_intent_rule_based(text, entities)

            data["intent"] = intent_result["intent"]
            data["confidence"] = intent_result["confidence"]
            data["auto_labeled"] = True  # 자동 레이블링 표시

            # 신뢰도가 낮으면 검토 필요
            if intent_result["confidence"] < 0.7:
                data["needs_review"] = True
                unlabeled.append(data)
            else:
                labeled.append(data)

    # 레이블링된 데이터 저장
    with open(output_path, "w", encoding="utf-8") as f:
        for item in labeled + unlabeled:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"\n레이블링 완료:")
    print(f"  자동 레이블링 (신뢰도 높음): {len([x for x in labeled if x.get('auto_labeled')])}개")
    print(f"  검토 필요 (신뢰도 낮음): {len(unlabeled)}개")
    print(f"  저장 위치: {output_path}")

    if unlabeled:
        review_path = output_path.replace(".jsonl", "_needs_review.jsonl")
        with open(review_path, "w", encoding="utf-8") as f:
            for item in unlabeled:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"  검토 필요 데이터: {review_path}")


def show_stats(input_path: str):
    """데이터셋 통계 출력"""
    intents = []
    total = 0

    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            intent = data.get("intent")
            if intent:
                intents.append(intent)
                total += 1

    counter = Counter(intents)

    print(f"\n데이터셋 통계:")
    print(f"  총 데이터: {total}개")
    print(f"\n의도별 분포:")
    for intent in INTENT_LABELS:
        count = counter.get(intent, 0)
        percentage = (count / total * 100) if total > 0 else 0
        print(f"  {intent}: {count}개 ({percentage:.1f}%)")

    # 최소 데이터 수 확인
    min_count = min(counter.values()) if counter else 0
    print(f"\n최소 클래스 데이터 수: {min_count}개")
    if min_count < 50:
        print("⚠️  경고: 일부 클래스의 데이터가 부족합니다. 최소 50개 이상 권장합니다.")


def create_template_data(output_path: str, samples_per_intent: int = 100):
    """템플릿 데이터 생성 (각 의도별 지정된 개수만큼)

    Args:
        output_path: 출력 파일 경로
        samples_per_intent: 의도별 생성할 샘플 수 (기본값: 100)
    """
    import random

    # 기본 템플릿
    db_query_templates = [
        "{year}년 {exam_type} {grade} {job_series} {subject} {qno}번 정답 뭐야?",
        "{year}년 {exam_type} {grade} {job_series} {subject} {qno}번 문제 정답 알려줘",
        "{year}년 {exam_type} {grade} {job_series} {subject} {qno}번",
        "{year}년 {exam_type} {grade} {subject} {qno}번 정답",
        "작년 {exam_type} {grade} {subject} {qno}번 정답 뭐야?",
        "올해 {exam_type} {grade} {subject} {qno}번 정답 알려줘",
        "{year}년 {exam_type} {subject} {qno}번 정답",
        "{exam_type} {grade} {subject} {qno}번 정답 뭐야?",
        "{year}년 {subject} {qno}번 문제 정답",
        "{subject} {qno}번 정답 알려줘",
    ]

    explain_templates = [
        "신뢰보호의 원칙이 이 판례에서 왜 적용 안 돼?",
        "행정법에서 신뢰보호의 원칙의 의미를 설명해줘",
        "이 문제에서 행정행위의 하자의 치유가 가능한 이유는?",
        "판례에서 이 원칙이 적용된 사례를 설명해줘",
        "행정법상 신뢰보호의 원칙과 법치주의의 관계는?",
        "이 판례의 법리를 설명해줘",
        "왜 이 경우에 행정행위가 무효인가요?",
        "이 원칙이 적용되는 요건은 무엇인가요?",
        "판례의 입장을 설명해줘",
        "이 문제의 해결 방법을 설명해줘",
        "행정법상 이 원칙의 근거는?",
        "이 판례에서 왜 이렇게 판단했나요?",
        "법리적 해석을 설명해줘",
        "이 원칙의 한계는 무엇인가요?",
        "실무에서 이 원칙이 어떻게 적용되나요?",
    ]

    advice_templates = [
        "직장인인데 하루 4시간 공부로 합격 가능할까?",
        "9급 공무원 시험 준비 방법 알려줘",
        "행정법 공부 전략 추천해줘",
        "합격을 위한 학습 계획 세우는 방법은?",
        "직장인 공무원 시험 준비 팁 알려줘",
        "공무원 시험 합격하는 방법은?",
        "효과적인 공부 방법 추천해줘",
        "시험 준비 기간은 얼마나 걸리나요?",
        "어떤 과목부터 공부해야 할까요?",
        "직장인도 합격 가능한가요?",
        "공부 시간 분배 방법은?",
        "과목별 공부 전략 알려줘",
        "시험 직전 준비 방법은?",
        "합격률 높이는 팁은?",
        "공부 습관 만드는 방법은?",
    ]

    out_of_domain_templates = [
        "오늘 날씨 어때?",
        "배고파",
        "영화 추천해줘",
        "게임하고 싶어",
        "쇼핑몰 추천",
        "음식점 추천해줘",
        "여행지 추천",
        "운동하고 싶어",
        "취미 추천해줘",
        "드라마 추천",
        "책 추천해줘",
        "음악 추천",
        "카페 추천해줘",
        "주말 뭐하지?",
        "심심해",
    ]

    # 변형 생성 함수
    def generate_variations(templates: List[str], count: int, intent: str) -> List[Dict[str, Any]]:
        """템플릿을 변형하여 데이터 생성"""
        results = []

        # 기본 변형 요소
        years = ["2024", "2023", "2022", "2021", "2020", "작년", "올해", "재작년"]
        exam_types = ["국가직", "지방직"]
        grades = ["9급", "7급"]
        job_series_list = ["교육행정직", "일반행정직", "사회복지직", "보건직"]
        subjects = ["회계학", "행정법총론", "행정학개론", "국어", "영어", "한국사", "국어", "행정학"]
        question_nos = list(range(1, 21))

        # 문장 끝 표현 변형
        endings = ["", "?", "!", "알려줘", "뭐야?", "알려주세요", "부탁해", "궁금해"]

        # 동의어 사전
        synonyms = {
            "정답": ["답", "답안", "정답지"],
            "문제": ["문항", "문제"],
            "알려줘": ["알려주세요", "알려줄래", "말해줘", "말해주세요"],
            "뭐야": ["뭐지", "뭔가", "무엇인가"],
        }

        template_idx = 0
        for i in range(count):
            if intent == "DB_QUERY":
                # DB_QUERY 템플릿 변형
                template = random.choice(db_query_templates)

                # 변수 치환
                text = template.format(
                    year=random.choice(years),
                    exam_type=random.choice(exam_types),
                    grade=random.choice(grades),
                    job_series=random.choice(job_series_list),
                    subject=random.choice(subjects),
                    qno=random.choice(question_nos)
                )

                # 동의어 치환 (30% 확률)
                if random.random() < 0.3:
                    for old, news in synonyms.items():
                        if old in text:
                            text = text.replace(old, random.choice(news), 1)

                # 문장 끝 변형 (20% 확률)
                if random.random() < 0.2 and text[-1] not in ["?", "!", "요", "해"]:
                    text += random.choice(endings)

            elif intent == "EXPLAIN":
                # EXPLAIN 템플릿 변형
                template = random.choice(explain_templates)
                text = template

                # 약간의 변형 (50% 확률)
                if random.random() < 0.5:
                    variations = [
                        text.replace("설명해줘", random.choice(["설명해주세요", "설명해줄래", "설명해"])),
                        text.replace("왜", random.choice(["어떻게", "무엇 때문에", "어떤 이유로"])),
                        text.replace("이", random.choice(["이번", "해당", "이런"])),
                    ]
                    if variations:
                        text = random.choice(variations)

            elif intent == "ADVICE":
                # ADVICE 템플릿 변형
                template = random.choice(advice_templates)
                text = template

                # 약간의 변형 (50% 확률)
                if random.random() < 0.5:
                    variations = [
                        text.replace("알려줘", random.choice(["알려주세요", "알려줄래", "가르쳐줘"])),
                        text.replace("추천해줘", random.choice(["추천해주세요", "추천해줄래", "추천"])),
                        text.replace("방법", random.choice(["방법", "전략", "팁", "노하우"])),
                    ]
                    if variations:
                        text = random.choice(variations)

            else:  # OUT_OF_DOMAIN
                # OUT_OF_DOMAIN 템플릿 변형
                template = random.choice(out_of_domain_templates)
                text = template

                # 약간의 변형 (30% 확률)
                if random.random() < 0.3:
                    variations = [
                        text.replace("추천해줘", random.choice(["추천해주세요", "추천해줄래", "추천"])),
                        text.replace("어때", random.choice(["어떠해", "어떤가", "어떤지"])),
                    ]
                    if variations:
                        text = random.choice(variations)

            results.append({"text": text, "intent": intent})

        return results

    # 각 의도별로 데이터 생성
    all_data = []

    print(f"각 의도별로 {samples_per_intent}개씩 생성 중...")

    for intent in INTENT_LABELS:
        data = generate_variations([], samples_per_intent, intent)
        all_data.extend(data)
        print(f"  {intent}: {len(data)}개 생성 완료")

    # JSONL로 저장
    with open(output_path, "w", encoding="utf-8") as f:
        for item in all_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"\n총 {len(all_data)}개 데이터 생성 완료")
    print(f"저장 위치: {output_path}")

    # 통계 출력
    from collections import Counter
    intents = [item["intent"] for item in all_data]
    counter = Counter(intents)
    print(f"\n의도별 분포:")
    for intent in INTENT_LABELS:
        count = counter.get(intent, 0)
        print(f"  {intent}: {count}개 ({count/len(all_data)*100:.1f}%)")


def main():
    parser = argparse.ArgumentParser(description="의도 분류 학습 데이터 준비")
    subparsers = parser.add_subparsers(dest="command", help="명령어")

    # collect 명령
    collect_parser = subparsers.add_parser("collect", help="DB에서 질문 수집")
    collect_parser.add_argument("--output", type=str, required=True, help="출력 파일 경로")
    collect_parser.add_argument("--limit", type=int, default=1000, help="수집할 질문 수")

    # label 명령
    label_parser = subparsers.add_parser("label", help="질문 레이블링")
    label_parser.add_argument("--input", type=str, required=True, help="입력 파일 경로")
    label_parser.add_argument("--output", type=str, required=True, help="출력 파일 경로")

    # stats 명령
    stats_parser = subparsers.add_parser("stats", help="데이터셋 통계")
    stats_parser.add_argument("--input", type=str, required=True, help="데이터 파일 경로")

    # template 명령
    template_parser = subparsers.add_parser("template", help="템플릿 데이터 생성")
    template_parser.add_argument("--output", type=str, required=True, help="출력 파일 경로")
    template_parser.add_argument("--samples", type=int, default=100, help="의도별 생성할 샘플 수 (기본값: 100)")

    args = parser.parse_args()

    if args.command == "collect":
        collect_questions_from_db(args.output, args.limit)
    elif args.command == "label":
        auto_label_questions(args.input, args.output)
    elif args.command == "stats":
        show_stats(args.input)
    elif args.command == "template":
        create_template_data(args.output, args.samples)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

