import json
import re

# JSONL 파일 읽기
data = []
with open('data/success_stories/megagong/megagong_stories_training.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        try:
            data.append(json.loads(line.strip()))
        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류: {e}")
            print(f"문제가 있는 라인: {line[:100]}...")

print(f"총 데이터 수: {len(data)}\n")

# 1. 필수 필드 확인
print("=== 필수 필드 확인 ===")
issues = []
for i, d in enumerate(data):
    if "instruction" not in d:
        issues.append(f"라인 {i+1}: instruction 필드 없음")
    if "input" not in d:
        issues.append(f"라인 {i+1}: input 필드 없음")
    if "output" not in d:
        issues.append(f"라인 {i+1}: output 필드 없음")
    if "input" in d:
        if "question" not in d["input"]:
            issues.append(f"라인 {i+1}: input.question 필드 없음")
        if "intent" not in d["input"]:
            issues.append(f"라인 {i+1}: input.intent 필드 없음")
        if "context" not in d["input"]:
            issues.append(f"라인 {i+1}: input.context 필드 없음")
    if "output" in d:
        if "thought_process" not in d["output"]:
            issues.append(f"라인 {i+1}: output.thought_process 필드 없음")
        if "response" not in d["output"]:
            issues.append(f"라인 {i+1}: output.response 필드 없음")

if issues:
    print(f"[오류] 발견된 문제: {len(issues)}개")
    for issue in issues[:10]:
        print(f"  - {issue}")
    if len(issues) > 10:
        print(f"  ... 외 {len(issues)-10}개")
else:
    print("[OK] 모든 필수 필드가 존재합니다.")

# 2. 빈 필드 확인
print("\n=== 빈 필드 확인 ===")
empty_fields = []
for i, d in enumerate(data):
    if "instruction" in d and not d["instruction"].strip():
        empty_fields.append(f"라인 {i+1}: instruction이 비어있음")
    if "input" in d and "question" in d["input"] and not d["input"]["question"].strip():
        empty_fields.append(f"라인 {i+1}: question이 비어있음")
    if "input" in d and "context" in d["input"] and not d["input"]["context"].strip():
        empty_fields.append(f"라인 {i+1}: context가 비어있음")
    if "output" in d and "thought_process" in d["output"] and not d["output"]["thought_process"].strip():
        empty_fields.append(f"라인 {i+1}: thought_process가 비어있음")
    if "output" in d and "response" in d["output"] and not d["output"]["response"].strip():
        empty_fields.append(f"라인 {i+1}: response가 비어있음")

if empty_fields:
    print(f"[오류] 발견된 문제: {len(empty_fields)}개")
    for field in empty_fields[:10]:
        print(f"  - {field}")
    if len(empty_fields) > 10:
        print(f"  ... 외 {len(empty_fields)-10}개")
else:
    print("[OK] 빈 필드가 없습니다.")

# 3. 문법 오류 확인
print("\n=== 문법 오류 확인 ===")
grammar_errors = []
for i, d in enumerate(data):
    if "output" in d and "response" in d["output"]:
        response = d["output"]["response"]
        if re.search(r'[법학]는', response):
            grammar_errors.append(f"라인 {i+1}: '{re.search(r'[법학]는', response).group()}' 문법 오류")

if grammar_errors:
    print(f"[오류] 발견된 문제: {len(grammar_errors)}개")
    for error in grammar_errors[:10]:
        print(f"  - {error}")
    if len(grammar_errors) > 10:
        print(f"  ... 외 {len(grammar_errors)-10}개")
else:
    print("[OK] 문법 오류가 없습니다.")

# 4. 질문 문체 통계
print("\n=== 질문 문체 통계 ===")
formal_count = 0
informal_count = 0
for d in data:
    if "input" in d and "question" in d["input"]:
        question = d["input"]["question"]
        if re.search(r'[요까나세]요', question):
            formal_count += 1
        elif re.search(r'[어해야니냐지줘]$|줘', question):
            informal_count += 1

print(f"존댓말 질문: {formal_count}개")
print(f"반말 질문: {informal_count}개")
print(f"기타: {len(data) - formal_count - informal_count}개")

# 5. 답변 문체 확인
print("\n=== 답변 문체 확인 ===")
response_formal_count = 0
response_informal_count = 0
for d in data:
    if "output" in d and "response" in d["output"]:
        response = d["output"]["response"]
        if re.search(r'[요까나세]요|입니다|입니다|세요|세요', response):
            response_formal_count += 1
        elif re.search(r'[어해야니냐지줘]$|줘', response):
            response_informal_count += 1

print(f"존댓말 답변: {response_formal_count}개")
if response_informal_count > 0:
    print(f"[경고] 반말 답변: {response_informal_count}개 (수정 필요)")
else:
    print("[OK] 모든 답변이 존댓말입니다.")

# 6. Context 길이 확인
print("\n=== Context 길이 통계 ===")
context_lengths = []
for d in data:
    if "input" in d and "context" in d["input"]:
        context_lengths.append(len(d["input"]["context"]))

if context_lengths:
    print(f"평균 길이: {sum(context_lengths) / len(context_lengths):.1f}자")
    print(f"최소 길이: {min(context_lengths)}자")
    print(f"최대 길이: {max(context_lengths)}자")
    short_contexts = [i+1 for i, length in enumerate(context_lengths) if length < 50]
    if short_contexts:
        print(f"[경고] 50자 미만 context: {len(short_contexts)}개 (라인: {short_contexts[:5]}{'...' if len(short_contexts) > 5 else ''})")

# 7. Response 길이 확인
print("\n=== Response 길이 통계 ===")
response_lengths = []
for d in data:
    if "output" in d and "response" in d["output"]:
        response_lengths.append(len(d["output"]["response"]))

if response_lengths:
    print(f"평균 길이: {sum(response_lengths) / len(response_lengths):.1f}자")
    print(f"최소 길이: {min(response_lengths)}자")
    print(f"최대 길이: {max(response_lengths)}자")
    short_responses = [i+1 for i, length in enumerate(response_lengths) if length < 50]
    if short_responses:
        print(f"[경고] 50자 미만 response: {len(short_responses)}개 (라인: {short_responses[:5]}{'...' if len(short_responses) > 5 else ''})")

print("\n=== 점검 완료 ===")

