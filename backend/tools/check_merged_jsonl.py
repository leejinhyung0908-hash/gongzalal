#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json

with open('data/gongmuwon/dataset/commentary_merged.jsonl', 'r', encoding='utf-8') as f:
    items = [json.loads(line) for line in f if line.strip()]

korean_history = [i for i in items if i.get("subject") == "한국사"]
english = [i for i in items if i.get("subject") == "영어"]

print(f"총 {len(items)}개 항목")
print(f"한국사: {len(korean_history)}개")
print(f"영어: {len(english)}개")
print(f"\n영어 첫 번째 항목:")
print(f"  ID: {english[0].get('id')}")
print(f"  Subject: {english[0].get('subject')}")
print(f"  Answer: {english[0].get('answer')}")
print(f"  Question 길이: {len(english[0].get('question', ''))}자")

