import json
import random
import re
from typing import List, Dict, Any

def extract_key_info(story: Dict[str, Any]) -> Dict[str, Any]:
    """합격 수기에서 핵심 정보 추출"""
    exam_info = story.get("exam_info", {})
    study_style = story.get("study_style", {})

    # megagong은 "총 수험 기간"이 raw_text에 있을 수 있으므로 추출 시도
    period = ""
    raw_text = story.get("raw_text", "")
    period_patterns = [
        r"총 수험 기간\s*[:\n]\s*([0-9개월~년\s]+)",
        r"수험 기간\s*[:\n]\s*([0-9개월~년\s]+)",
        r"([0-9개월~년\s]+)\s*수험기간",
    ]
    for pattern in period_patterns:
        match = re.search(pattern, raw_text)
        if match:
            period = match.group(1).strip()
            break

    return {
        "year": exam_info.get("year", ""),
        "exam_type": exam_info.get("exam_type", ""),
        "grade": exam_info.get("grade", ""),
        "job_series": exam_info.get("job_series", ""),
        "period": period,
        "subjects": exam_info.get("subjects", []),
        "study_type": study_style.get("수험생활", ""),
        "daily_plan": story.get("daily_plan", ""),
        "subject_methods": story.get("subject_methods", {}),
        "difficulties": story.get("difficulties", ""),
        "key_points": story.get("key_points", ""),
        "interview_prep": story.get("interview_prep", "")
    }

def generate_questions_and_responses(key_info: Dict[str, Any], story_index: int) -> List[Dict[str, Any]]:
    """합격 수기 정보를 바탕으로 학습 데이터 생성"""
    training_data = []

    exam_type = key_info.get("exam_type", "")
    grade = key_info.get("grade", "")
    job_series = key_info.get("job_series", "")
    period = key_info.get("period", "")
    study_type = key_info.get("study_type", "")
    subjects = key_info.get("subjects", [])

    # 1. 직장인/전업 수험생 관련 질문
    if study_type:
        if "직장인" in study_type or "아르바이트" in study_type or "병행" in study_type:
            question_variants = [
                "직장인인데 공무원 시험 준비 어떻게 해야 할까요?",
                "직장인 초시생인데 시간이 부족해요. 어떻게 공부해야 하나요?",
                "퇴근 후 공부하는 직장인 수험생인데 효율적인 학습 방법이 궁금해요.",
                "직장인인데 공무원 시험 준비 어떻게 해야 해?",
                "직장인 초시생인데 시간이 부족해. 어떻게 공부해야 해?",
                "퇴근 후 공부하는 직장인 수험생인데 효율적인 학습 방법 알려줘."
            ]
            question = random.choice(question_variants)
            thought = f"1. 질문자가 직장인임을 인지함. 2. 합격 수기 {story_index}번에서 {period if period else '일정 기간'} 수험기간 동안 {study_type}으로 합격한 사례 확인. 3. 시간 관리와 효율적 학습 전략이 핵심임을 판단. 4. 해당 합격자의 일일 학습 계획과 핵심 전략을 인용하기로 함."
            context = f"합격자 수기: {period if period else '일정 기간'} 수험기간, {study_type}. 핵심 포인트: {key_info.get('key_points', '')[:200]}"
            response = f"직장인 수험생 여러분, 시간이 생명입니다! {period if period else '일정 기간'} 수험기간 동안 합격하신 선배님의 조언을 들려드릴게요. {key_info.get('key_points', '')[:300]}... 직장인이라면 퇴근 후 시간을 어떻게 활용하느냐가 합격을 좌우합니다. 오늘부터 바로 시작해보시는 건 어떨까요?"
        else:  # 전업 수험생
            question_variants = [
                "전업 수험생으로 공부하는데 하루 일과를 어떻게 구성해야 할까요?",
                "전업 수험생인데 시간 분배가 어려워요. 하루 계획을 어떻게 세워야 할까요?",
                "전업 수험생으로 공부하는데 효율적인 일일 루틴이 궁금해요.",
                "전업 수험생인데 하루 일과 어떻게 구성해야 해?",
                "전업 수험생인데 시간 분배가 어려워. 하루 계획 어떻게 세워야 해?",
                "전업 수험생인데 효율적인 일일 루틴 알려줘."
            ]
            question = random.choice(question_variants)
            thought = f"1. 전업 수험생의 일일 계획 질문임을 인지. 2. 합격 수기 {story_index}번의 daily_plan 분석. 3. 시간 분배와 과목별 학습 순서가 중요함을 판단. 4. 구체적인 일일 루틴을 제시하기로 함."
            context = f"합격자 수기: {period if period else '일정 기간'} 수험기간, 일일 학습 계획: {key_info.get('daily_plan', '')[:200]}"
            response = f"전업 수험생이시군요! 시간이 많다고 해서 방심하면 안 됩니다. {period if period else '일정 기간'} 수험기간 동안 합격하신 선배님의 하루 일과를 참고해보세요. {key_info.get('daily_plan', '')[:300]}... 핵심은 규칙적인 루틴과 꾸준함입니다!"

        training_data.append({
            "instruction": "공무원 수험 멘토로서, 제공된 합격 수기를 바탕으로 질문자에게 공감하고 구체적인 학습 전략을 제시하세요. 답변은 항상 따뜻하고 전문적인 어조를 유지하세요.",
            "input": {
                "question": question,
                "intent": "ADVICE",
                "context": context
            },
            "output": {
                "thought_process": thought,
                "response": response
            }
        })

    # 2. 과목별 학습법 질문
    subject_methods = key_info.get("subject_methods", {})
    if isinstance(subject_methods, dict):
        # megagong은 이미 과목별로 분리되어 있음
        for subject_key, methods_text in subject_methods.items():
            if subject_key in subjects and methods_text and len(methods_text.strip()) >= 50:
                # 과목명이 중복되어 있는 경우 제거 (예: "국어국어는..." -> "국어는...")
                methods_text_clean = methods_text.strip()
                if methods_text_clean.startswith(subject_key):
                    # "국어국어는" 같은 경우 처리
                    if len(methods_text_clean) > len(subject_key) and methods_text_clean[len(subject_key):len(subject_key)+len(subject_key)] == subject_key:
                        methods_text_clean = methods_text_clean[len(subject_key):]
                    elif methods_text_clean.startswith(f"{subject_key}{subject_key}"):
                        methods_text_clean = methods_text_clean[len(subject_key):]

                question_variants = [
                    f"{subject_key} 공부 방법이 너무 막막해요. 합격자들은 어떻게 했나요?",
                    f"{subject_key}가 너무 어려워요. 어떻게 접근해야 할까요?",
                    f"{subject_key} 학습 전략이 궁금해요. 합격자들의 조언을 듣고 싶어요.",
                    f"{subject_key} 공부 방법 너무 막막한데 합격자들은 어떻게 했어?",
                    f"{subject_key} 너무 어려운데 어떻게 접근해야 해?",
                    f"{subject_key} 학습 전략 알려줘. 합격자들은 어떻게 했어?"
                ]
                question = random.choice(question_variants)
                thought = f"1. {subject_key} 과목 학습법 질문임을 인지. 2. 합격 수기 {story_index}번의 {subject_key} 관련 학습법 확인. 3. 구체적인 교재, 강사, 학습 순서를 제시해야 함을 판단. 4. 해당 합격자의 {subject_key} 학습 전략을 인용하기로 함."
                context = f"합격자 수기: {subject_key} 학습법 - {methods_text_clean[:300]}"
                # 문법 오류 수정: "노동법는" → "노동법은", "경제학는" → "경제학은"
                subject_display = f"{subject_key}은" if subject_key.endswith("법") or subject_key.endswith("학") else f"{subject_key}는"
                response = f"{subject_display} 정말 중요한 과목이에요! 합격하신 선배님의 {subject_key} 학습법을 들려드릴게요. {methods_text_clean[:400]}... 핵심은 꾸준함과 반복입니다. 오늘부터 바로 시작해보세요!"

                training_data.append({
                    "instruction": "공무원 수험 멘토로서, 제공된 합격 수기를 바탕으로 질문자에게 공감하고 구체적인 학습 전략을 제시하세요. 답변은 항상 따뜻하고 전문적인 어조를 유지하세요.",
                    "input": {
                        "question": question,
                        "intent": "ADVICE",
                        "context": context
                    },
                    "output": {
                        "thought_process": thought,
                        "response": response
                    }
                })

    # 3. 수험 기간 관련 질문
    if period:
        question_period_variants = [
            f"{period} 수험기간이면 합격 가능할까요?",
            f"{period} 동안 공부하면 합격할 수 있을까요?",
            f"{period} 수험기간으로는 부족한가요?",
            f"{period} 수험기간이면 합격 가능해?",
            f"{period} 동안 공부하면 합격할 수 있어?",
            f"{period} 수험기간으로는 부족한 거 아니야?"
        ]
        question_period = random.choice(question_period_variants)
        thought_period = f"1. 수험 기간에 대한 불안감 질문임을 인지. 2. 합격 수기 {story_index}번에서 정확히 {period} 기간으로 합격한 사례 확인. 3. 기간보다는 학습 방법과 집중도가 중요함을 강조. 4. 해당 합격자의 핵심 전략을 제시하기로 함."
        context_period = f"합격자 수기: {period} 수험기간, {grade}급 {job_series if job_series else ''} 합격. 핵심: {key_info.get('key_points', '')[:200]}"
        response_period = f"물론 가능합니다! {period} 수험기간 동안 {grade}급 {job_series if job_series else ''}에 합격하신 선배님이 계세요. {key_info.get('key_points', '')[:300]}... 기간보다는 매일 꾸준히 하는 것이 중요합니다. 여러분도 충분히 가능해요!"

        training_data.append({
            "instruction": "공무원 수험 멘토로서, 제공된 합격 수기를 바탕으로 질문자에게 공감하고 구체적인 학습 전략을 제시하세요. 답변은 항상 따뜻하고 전문적인 어조를 유지하세요.",
            "input": {
                "question": question_period,
                "intent": "ADVICE",
                "context": context_period
            },
            "output": {
                "thought_process": thought_period,
                "response": response_period
            }
        })

        # 나이/시작 시기 질문
        if "직장인" in study_type or "아르바이트" in study_type or random.random() < 0.5:
            question_age_variants = [
                "30대에 시작해도 합격 가능할까요?",
                "나이가 많아서 걱정이에요. 늦게 시작해도 될까요?",
                "직장인인데 나이 때문에 불안해요. 합격 가능할까요?",
                "30대에 시작해도 합격 가능해?",
                "나이가 많아서 걱정되는데 늦게 시작해도 돼?",
                "직장인인데 나이 때문에 불안한데 합격 가능해?"
            ]
            question_age = random.choice(question_age_variants)
            thought_age = f"1. 나이에 대한 불안감 질문임을 인지. 2. 합격 수기 {story_index}번에서 {period} 수험기간 동안 합격한 사례 확인. 3. 나이보다는 학습 방법과 집중도가 중요함을 강조. 4. 해당 합격자의 경험을 통해 격려하기로 함."
            context_age = f"합격자 수기: {period} 수험기간, {grade}급 {job_series if job_series else ''} 합격. 핵심: {key_info.get('key_points', '')[:200]}"
            response_age = f"나이는 전혀 문제되지 않습니다! {period} 수험기간 동안 {grade}급 {job_series if job_series else ''}에 합격하신 선배님들도 계세요. {key_info.get('key_points', '')[:300]}... 나이보다는 매일 꾸준히 하는 것이 중요합니다. 여러분도 충분히 가능해요!"

            training_data.append({
                "instruction": "공무원 수험 멘토로서, 제공된 합격 수기를 바탕으로 질문자에게 공감하고 구체적인 학습 전략을 제시하세요. 답변은 항상 따뜻하고 전문적인 어조를 유지하세요.",
                "input": {
                    "question": question_age,
                    "intent": "ADVICE",
                    "context": context_age
                },
                "output": {
                    "thought_process": thought_age,
                    "response": response_age
                }
            })

    # 4. 어려움 극복 관련 질문
    difficulties = key_info.get("difficulties", "")
    if difficulties and len(difficulties.strip()) >= 50:
        question_variants = [
            "수험 생활이 너무 힘들어요. 어떻게 극복해야 할까요?",
            "슬럼프가 왔을 때 어떻게 대처해야 할까요?",
            "공부하면서 지치는데, 멘탈 관리 팁이 있을까요?",
            "수험 생활 너무 힘든데 어떻게 극복해야 해?",
            "수험 생활이 힘들어서 포기하고 싶어. 어떻게 해야 해?"
        ]
        question = random.choice(question_variants)
        thought = f"1. 수험생의 정신적 어려움 질문임을 인지. 2. 합격 수기 {story_index}번의 difficulties 섹션 확인. 3. 공감과 함께 구체적인 극복 방법 제시 필요. 4. 해당 합격자의 경험과 조언을 인용하기로 함."
        context = f"합격자 수기: 어려웠던 점과 극복 방법 - {difficulties[:200]}"
        response = f"정말 힘드시겠어요. 하지만 이 고비를 넘기면 합격이 보입니다! {difficulties[:400]}... 여러분도 이렇게 극복하실 수 있어요. 지금의 고생이 나중에 큰 힘이 됩니다!"

        training_data.append({
            "instruction": "공무원 수험 멘토로서, 제공된 합격 수기를 바탕으로 질문자에게 공감하고 구체적인 학습 전략을 제시하세요. 답변은 항상 따뜻하고 전문적인 어조를 유지하세요.",
            "input": {
                "question": question,
                "intent": "ADVICE",
                "context": context
            },
            "output": {
                "thought_process": thought,
                "response": response
            }
        })

    # 5. 면접 준비 관련 질문
    interview_prep = key_info.get("interview_prep", "")
    if interview_prep and len(interview_prep.strip()) >= 50:
        question_variants = [
            "면접 준비는 언제부터 시작해야 할까요? 어떻게 준비해야 하나요?",
            "면접 스터디가 도움이 될까요? 면접 팁이 궁금해요.",
            "면접에서 좋은 인상을 남기려면 어떻게 해야 할까요?",
            "면접 준비 언제부터 시작해야 해? 어떻게 준비해야 해?",
            "면접 준비 시기와 방법 알려줘."
        ]
        question = random.choice(question_variants)
        thought = f"1. 면접 준비 시기와 방법 질문임을 인지. 2. 합격 수기 {story_index}번의 interview_prep 섹션 확인. 3. 필기 합격 후 준비해도 충분하지만, 구체적인 준비 방법 제시 필요. 4. 해당 합격자의 면접 준비 전략을 인용하기로 함."
        context = f"합격자 수기: 면접 준비 과정 - {interview_prep[:200]}"
        response = f"면접 준비는 필기 합격 후 시작해도 충분합니다! 합격하신 선배님의 면접 준비 노하우를 들려드릴게요. {interview_prep[:400]}... 면접 스터디는 꼭 추천드려요!"

        training_data.append({
            "instruction": "공무원 수험 멘토로서, 제공된 합격 수기를 바탕으로 질문자에게 공감하고 구체적인 학습 전략을 제시하세요. 답변은 항상 따뜻하고 전문적인 어조를 유지하세요.",
            "input": {
                "question": question,
                "intent": "ADVICE",
                "context": context
            },
            "output": {
                "thought_process": thought,
                "response": response
            }
        })

    return training_data

def main():
    # JSON 파일 읽기
    with open("data/success_stories/megagong/megagong_stories.json", "r", encoding="utf-8") as f:
        stories = json.load(f)

    print(f"총 {len(stories)}개의 합격 수기를 읽었습니다.")

    all_training_data = []

    # 각 합격 수기에서 학습 데이터 생성
    for idx, story in enumerate(stories):
        try:
            key_info = extract_key_info(story)
            training_data = generate_questions_and_responses(key_info, idx + 1)
            all_training_data.extend(training_data)

            if (idx + 1) % 100 == 0:
                print(f"{idx + 1}개 처리 완료...")
        except Exception as e:
            print(f"에러 발생 (인덱스 {idx}): {e}")
            continue

    print(f"\n총 {len(all_training_data)}개의 학습 데이터가 생성되었습니다.")

    # JSONL 파일로 저장
    output_file = "data/success_stories/megagong/megagong_stories_training.jsonl"
    with open(output_file, "w", encoding="utf-8") as f:
        for data in all_training_data:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

    print(f"학습 데이터가 {output_file}에 저장되었습니다.")

    # 샘플 출력
    print("\n=== 샘플 데이터 (첫 3개) ===")
    for i, data in enumerate(all_training_data[:3]):
        print(f"\n[샘플 {i+1}]")
        print(json.dumps(data, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()

