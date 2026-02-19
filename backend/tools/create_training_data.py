import json
import random
from typing import List, Dict, Any

def extract_key_info(story: Dict[str, Any]) -> Dict[str, Any]:
    """합격 수기에서 핵심 정보 추출"""
    exam_info = story.get("exam_info", {})
    study_style = story.get("study_style", {})

    return {
        "year": exam_info.get("year", ""),
        "exam_type": exam_info.get("exam_type", ""),
        "grade": exam_info.get("grade", ""),
        "job_series": exam_info.get("job_series", ""),
        "period": exam_info.get("총 수험기간", ""),
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

    # 1. 직장인/초시생 관련 질문
    if study_type:
        if "직장인" in study_type:
            question_variants = [
                "직장인인데 공무원 시험 준비 어떻게 해야 할까요?",
                "직장인 초시생인데 시간이 부족해요. 어떻게 공부해야 하나요?",
                "퇴근 후 공부하는 직장인 수험생인데 효율적인 학습 방법이 궁금해요.",
                "직장인인데 공무원 시험 준비 어떻게 해야 해?",
                "직장인 초시생인데 시간이 부족해. 어떻게 공부해야 해?",
                "퇴근 후 공부하는 직장인 수험생인데 효율적인 학습 방법 알려줘."
            ]
            question = random.choice(question_variants)
            thought = f"1. 질문자가 직장인임을 인지함. 2. 합격 수기 {story_index}번에서 {period} 수험기간 동안 {study_type}으로 합격한 사례 확인. 3. 시간 관리와 효율적 학습 전략이 핵심임을 판단. 4. 해당 합격자의 일일 학습 계획과 핵심 전략을 인용하기로 함."
            context = f"합격자 수기: {period} 수험기간, {study_type}. 핵심 포인트: {key_info.get('key_points', '')[:200]}"
            response = f"직장인 수험생 여러분, 시간이 생명입니다! {period} 수험기간 동안 합격하신 선배님의 조언을 들려드릴게요. {key_info.get('key_points', '')[:300]}... 직장인이라면 퇴근 후 시간을 어떻게 활용하느냐가 합격을 좌우합니다. 오늘부터 바로 시작해보시는 건 어떨까요?"
        else:
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
            context = f"합격자 수기: {period} 수험기간, 일일 학습 계획: {key_info.get('daily_plan', '')[:200]}"
            response = f"전업 수험생이시군요! 시간이 많다고 해서 방심하면 안 됩니다. {period} 수험기간 동안 합격하신 선배님의 하루 일과를 참고해보세요. {key_info.get('daily_plan', '')[:300]}... 핵심은 규칙적인 루틴과 꾸준함입니다!"

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
        # "전체" 키가 있으면 실제로 해당 과목이 언급되는지 확인
        if "전체" in subject_methods:
            methods_text = subject_methods["전체"]

            # "전체" 텍스트에서 실제로 언급된 과목 찾기
            # 과목별로 구분된 패턴 확인 (예: "국어-", "영어-", "[국어]" 등)
            mentioned_subjects = []
            for subject in subjects:
                # 과목명이 명시적으로 언급되는지 확인 (우선순위: 명확한 구분자 > 조사)
                patterns = [
                    f"[{subject}]",  # [국어] 형태가 가장 명확
                    f"{subject}-",   # 국어- 형태
                    f"{subject} ",   # 국어 (공백)
                ]
                # 조사 패턴은 "영어가장" 같은 경우를 피하기 위해 더 신중하게
                if any(pattern in methods_text for pattern in patterns):
                    mentioned_subjects.append(subject)
                elif f"{subject}은" in methods_text or f"{subject}는" in methods_text:
                    # "은/는" 조사는 안전
                    mentioned_subjects.append(subject)
                elif f"{subject}가" in methods_text:
                    # "가" 조사는 "가장" 같은 경우를 확인
                    idx = methods_text.find(f"{subject}가")
                    if idx + len(f"{subject}가") < len(methods_text):
                        next_char = methods_text[idx + len(f"{subject}가")]
                        if next_char != "장":  # "가장"이 아닌 경우만
                            mentioned_subjects.append(subject)

            # 실제로 언급된 과목이 있으면 그 중에서만 선택
            if mentioned_subjects:
                subject = random.choice(mentioned_subjects)
                # 해당 과목의 내용만 추출 시도
                subject_content = ""
                # 과목별로 구분된 경우 해당 부분만 추출
                # 패턴 우선순위: [과목], 과목-, 과목은/는/가 (단, "과목가장" 같은 경우 제외)
                patterns = [
                    (f"[{subject}]", len(f"[{subject}]")),
                    (f"{subject}-", len(f"{subject}-")),
                    (f"{subject}은", len(f"{subject}은")),
                    (f"{subject}는", len(f"{subject}는")),
                    (f"{subject}가", len(f"{subject}가")),
                ]

                found_pattern = None
                for pattern, pattern_len in patterns:
                    if pattern in methods_text:
                        # "영어가장" 같은 경우 제외
                        if pattern.endswith("가"):
                            idx = methods_text.find(pattern)
                            if idx + pattern_len < len(methods_text):
                                next_char = methods_text[idx + pattern_len]
                                if next_char == "장":  # "가장"인 경우 스킵
                                    continue
                        idx = methods_text.find(pattern)
                        # 다음 과목이나 문단까지 추출
                        next_subject_idx = len(methods_text)
                        for other_subject in subjects:
                            if other_subject != subject:
                                other_patterns = [
                                    f"[{other_subject}]",
                                    f"{other_subject}-",
                                    f"{other_subject}은",
                                    f"{other_subject}는",
                                ]
                                # "가" 패턴은 "가장" 같은 경우를 피하기 위해 조심스럽게
                                if f"{other_subject}가" in methods_text:
                                    other_idx = methods_text.find(f"{other_subject}가", idx + pattern_len)
                                    if other_idx != -1 and other_idx + len(f"{other_subject}가") < len(methods_text):
                                        if methods_text[other_idx + len(f"{other_subject}가")] != "장":  # "가장"이 아닌 경우만
                                            other_patterns.append(f"{other_subject}가")

                                for other_pattern in other_patterns:
                                    if other_pattern in methods_text[idx + pattern_len:]:
                                        next_idx = methods_text.find(other_pattern, idx + pattern_len)
                                        if next_idx < next_subject_idx:
                                            next_subject_idx = next_idx
                        subject_content = methods_text[idx:next_subject_idx].strip()
                        # 과목명 패턴 제거 (예: "한국사- " 제거)
                        if subject_content.startswith(f"{subject}-"):
                            subject_content = subject_content[len(f"{subject}-"):].strip()
                        elif subject_content.startswith(f"[{subject}]"):
                            subject_content = subject_content[len(f"[{subject}]"):].strip()
                        elif subject_content.startswith(f"{subject}은"):
                            subject_content = subject_content[len(f"{subject}은"):].strip()
                        elif subject_content.startswith(f"{subject}는"):
                            subject_content = subject_content[len(f"{subject}는"):].strip()
                        elif subject_content.startswith(f"{subject}가"):
                            subject_content = subject_content[len(f"{subject}가"):].strip()
                        break

                # 과목 내용이 너무 짧거나 없으면 스킵
                if not subject_content or len(subject_content) < 50:
                    return training_data

                # 과목별 질문 변형
                question_variants = [
                    f"{subject} 공부 방법이 너무 막막해요. 합격자들은 어떻게 했나요?",
                    f"{subject}가 너무 어려워요. 어떻게 접근해야 할까요?",
                    f"{subject} 학습 전략이 궁금해요. 합격자들의 조언을 듣고 싶어요.",
                    f"{subject} 공부 방법 너무 막막한데 합격자들은 어떻게 했어?",
                    f"{subject} 너무 어려운데 어떻게 접근해야 해?",
                    f"{subject} 학습 전략 알려줘. 합격자들은 어떻게 했어?"
                ]
                question = random.choice(question_variants)
                thought = f"1. {subject} 과목 학습법 질문임을 인지. 2. 합격 수기 {story_index}번의 {subject} 관련 학습법 확인. 3. 구체적인 교재, 강사, 학습 순서를 제시해야 함을 판단. 4. 해당 합격자의 {subject} 학습 전략을 인용하기로 함."
                context = f"합격자 수기: {subject} 학습법 - {subject_content[:300]}"
                # 문법 오류 수정: "노동법는" → "노동법은", "경제학는" → "경제학은"
                subject_display = f"{subject}은" if subject.endswith("법") or subject.endswith("학") else f"{subject}는"
                response = f"{subject_display} 정말 중요한 과목이에요! 합격하신 선배님의 {subject} 학습법을 들려드릴게요. {subject_content[:400]}... 핵심은 꾸준함과 반복입니다. 오늘부터 바로 시작해보세요!"

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
            else:
                # 과목별로 구분되지 않은 경우, 전체 학습법에 대한 일반 질문만 생성
                question_variants = [
                    "과목별 학습 전략이 궁금해요. 합격자들은 어떻게 공부했나요?",
                    "과목별 학습 전략 알려줘. 합격자들은 어떻게 공부했어?",
                    "합격자들은 어떻게 공부했는지 궁금해."
                ]
                question = random.choice(question_variants)
                thought = f"1. 전체 학습 전략 질문임을 인지. 2. 합격 수기 {story_index}번의 전체 학습법 확인. 3. 구체적인 학습 방법을 제시해야 함을 판단. 4. 해당 합격자의 전체 학습 전략을 인용하기로 함."
                context = f"합격자 수기: 전체 학습법 - {methods_text[:300]}"
                response = f"합격하신 선배님의 학습 전략을 들려드릴게요. {methods_text[:400]}... 핵심은 꾸준함과 반복입니다. 여러분도 이렇게 시작해보세요!"

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

        # 개별 과목 키가 있는 경우 (예: "국어", "영어" 등)
        for subject_key in subject_methods.keys():
            if subject_key != "전체" and subject_key in subjects:
                methods_text = subject_methods[subject_key]
                # 내용이 너무 짧으면 스킵
                if not methods_text or len(methods_text) < 50:
                    continue

                question_variants = [
                    f"{subject_key} 공부 방법이 너무 막막해요. 합격자들은 어떻게 했나요?",
                    f"{subject_key}가 너무 어려워요. 어떻게 접근해야 할까요?",
                    f"{subject_key} 학습 전략이 궁금해요.",
                    f"{subject_key} 공부 방법 너무 막막한데 합격자들은 어떻게 했어?",
                    f"{subject_key} 너무 어려운데 어떻게 접근해야 해?",
                    f"{subject_key} 학습 전략 알려줘."
                ]
                question = random.choice(question_variants)
                thought = f"1. {subject_key} 과목 학습법 질문임을 인지. 2. 합격 수기 {story_index}번의 {subject_key} 관련 학습법 확인. 3. 구체적인 교재, 강사, 학습 순서를 제시해야 함을 판단. 4. 해당 합격자의 {subject_key} 학습 전략을 인용하기로 함."
                context = f"합격자 수기: {subject_key} 학습법 - {methods_text[:300]}"
                # 문법 오류 수정
                subject_display = f"{subject_key}은" if subject_key.endswith("법") or subject_key.endswith("학") else f"{subject_key}는"
                response = f"{subject_display} 정말 중요한 과목이에요! 합격하신 선배님의 {subject_key} 학습법을 들려드릴게요. {methods_text[:400]}... 핵심은 꾸준함과 반복입니다. 오늘부터 바로 시작해보세요!"

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

    # 3. 수험 기간/나이 관련 질문
    if period:
        question_variants = [
            f"{period} 수험기간이면 합격 가능할까요?",
            f"{period} 동안 공부하면 합격할 수 있을까요?",
            f"{period} 수험기간으로는 부족한가요?",
            f"{period} 수험기간이면 합격 가능해?",
            f"{period} 동안 공부하면 합격할 수 있어?",
            f"{period} 수험기간으로는 부족한 거 아니야?"
        ]
        question = random.choice(question_variants)
        thought = f"1. 수험 기간에 대한 불안감 질문임을 인지. 2. 합격 수기 {story_index}번에서 정확히 {period} 기간으로 합격한 사례 확인. 3. 기간보다는 학습 방법과 집중도가 중요함을 강조. 4. 해당 합격자의 핵심 전략을 제시하기로 함."
        context = f"합격자 수기: {period} 수험기간, {grade}급 {job_series} 합격. 핵심: {key_info.get('key_points', '')[:200]}"
        response = f"물론 가능합니다! {period} 수험기간 동안 {grade}급 {job_series}에 합격하신 선배님이 계세요. {key_info.get('key_points', '')[:300]}... 기간보다는 매일 꾸준히 하는 것이 중요합니다. 여러분도 충분히 가능해요!"

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

    # 3-1. 나이 관련 질문 (30대, 40대 등)
    if "30" in str(period) or "40" in str(period) or study_type:
        age_questions = [
            "30대에 시작해도 합격 가능할까요?",
            "나이가 많아서 걱정이에요. 늦게 시작해도 될까요?",
            "직장인인데 나이 때문에 불안해요. 합격 가능할까요?",
            "30대에 시작해도 합격 가능해?",
            "나이가 많아서 걱정되는데 늦게 시작해도 돼?",
            "직장인인데 나이 때문에 불안한데 합격 가능해?"
        ]
        question = random.choice(age_questions)
        thought = f"1. 나이에 대한 불안감 질문임을 인지. 2. 합격 수기 {story_index}번에서 {period} 수험기간 동안 합격한 사례 확인. 3. 나이보다는 학습 방법과 집중도가 중요함을 강조. 4. 해당 합격자의 경험을 통해 격려하기로 함."
        context = f"합격자 수기: {period} 수험기간, {grade}급 {job_series} 합격. 핵심: {key_info.get('key_points', '')[:200]}"
        response = f"나이는 전혀 문제되지 않습니다! {period} 수험기간 동안 {grade}급 {job_series}에 합격하신 선배님들도 계세요. {key_info.get('key_points', '')[:300]}... 나이보다는 매일 꾸준히 하는 것이 중요합니다. 여러분도 충분히 가능해요!"

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

    # 4. 어려움 극복 관련 질문
    difficulties = key_info.get("difficulties", "")
    if difficulties and len(difficulties.strip()) >= 50:  # 최소 50자 이상만 사용
        question_variants = [
            "수험 생활이 너무 힘들어요. 어떻게 극복해야 할까요?",
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
    if interview_prep and len(interview_prep.strip()) >= 50:  # 최소 50자 이상만 사용
        question_variants = [
            "면접 준비는 언제부터 시작해야 할까요? 어떻게 준비해야 하나요?",
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
    with open("data/success_stories/gongdanki/success_stories.json", "r", encoding="utf-8") as f:
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
    output_file = "data/success_stories/gongdanki/success_stories_training.jsonl"
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

