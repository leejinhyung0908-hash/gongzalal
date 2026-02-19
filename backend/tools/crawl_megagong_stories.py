#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
메가공 합격수기 데이터 크롤링 스크립트

메가공 웹사이트의 합격수기 페이지 구조에 맞춰 데이터를 크롤링합니다.
"""

import json
import re
import csv
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MegagongStoryCrawler:
    """메가공 합격수기 크롤러"""

    def __init__(self, output_dir: str = "data/success_stories/megagong"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def _parse_table(self, table) -> Dict[str, str]:
        """HTML 테이블을 딕셔너리로 파싱"""
        result = {}
        if not table:
            return result

        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                key = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                if key and value:
                    result[key] = value
        return result

    def parse_story_content(self, html_content: str) -> Dict[str, Any]:
        """메가공 합격수기 HTML을 파싱하여 구조화된 데이터로 변환

        Args:
            html_content: HTML 콘텐츠

        Returns:
            구조화된 합격수기 데이터
        """
        # BeautifulSoup 파싱 (response.text는 이미 디코딩된 문자열)
        soup = BeautifulSoup(html_content, 'html.parser')

        story_data = {
            "exam_info": {},
            "study_style": {},
            "daily_plan": "",
            "subject_methods": {},
            "interview_prep": "",
            "difficulties": "",
            "key_points": "",
            "raw_text": ""
        }

        # 테이블 기반 파싱 (메가공 페이지 구조)
        tables = soup.find_all('table')

        # 첫 번째 테이블: 합격 선배의 시험 정보
        if len(tables) > 0:
            exam_info_table = self._parse_table(tables[0])
            if exam_info_table:
                # 최종합격에서 정보 추출
                final_pass = exam_info_table.get("최종합격", "")
                if final_pass:
                    # "2024년 지방직 9급 일반행정직" 형식에서 추출
                    year_match = re.search(r"(\d{4})", final_pass)
                    if year_match:
                        story_data["exam_info"]["year"] = year_match.group(1)

                    exam_type_match = re.search(r"(국가직|지방직|서울시|경기도|인천시|부산시|대구시|광주시|대전시|울산시|세종시)", final_pass)
                    if exam_type_match:
                        story_data["exam_info"]["exam_type"] = exam_type_match.group(1)

                    grade_match = re.search(r"(\d)\s*급", final_pass)
                    if grade_match:
                        story_data["exam_info"]["grade"] = grade_match.group(1)

                    job_series_match = re.search(r"(보호|일반행정|교육행정|소방|경찰|세무|회계|관세|통계|기계|전기|화학|농업|임업|수산|환경|건축|토목|도시계획|조경|정보보호|정보통신|전산|방송통신)", final_pass)
                    if job_series_match:
                        job = job_series_match.group(1)
                        if job == "보호":
                            story_data["exam_info"]["job_series"] = "보호직"
                        elif job == "일반행정":
                            story_data["exam_info"]["job_series"] = "일반행정직"
                        elif job == "교육행정":
                            story_data["exam_info"]["job_series"] = "교육행정직"
                        else:
                            story_data["exam_info"]["job_series"] = job + "직"

                # 응시직렬 또는 응시과목 추출 (메가공은 "응시직렬"로 표시될 수 있음)
                subjects_text = exam_info_table.get("응시과목", "") or exam_info_table.get("응시직렬", "")
                if subjects_text:
                    # 쉼표나 공백으로 분리
                    subjects = [s.strip() for s in re.split(r'[,，\s]+', subjects_text) if s.strip()]
                    story_data["exam_info"]["subjects"] = subjects

                # 총 수험기간 (메가공은 "총수험기간" 또는 "총 수험기간"으로 표시)
                study_period = exam_info_table.get("총 수험기간", "") or exam_info_table.get("총수험기간", "")
                if study_period:
                    story_data["exam_info"]["총 수험기간"] = study_period

                # 하루 평균 학습 시간
                study_hours = exam_info_table.get("하루 평균 학습 시간", "") or exam_info_table.get("평균 학습 시간", "")
                if study_hours:
                    story_data["exam_info"]["하루 평균 학습 시간"] = study_hours

        # 두 번째 테이블: 합격 선배의 수험생활 및 학습하기
        if len(tables) > 1:
            study_style_table = self._parse_table(tables[1])
            if study_style_table:
                # 수험생활
                study_life = study_style_table.get("수험생활", "")
                if study_life:
                    story_data["study_style"]["수험생활"] = study_life

                # 평균 회독수
                review_count = study_style_table.get("평균 회독수", "")
                if review_count:
                    story_data["study_style"]["평균 회독수"] = review_count

                # 정신력
                mental_strength = study_style_table.get("정신력", "")
                if mental_strength:
                    story_data["study_style"]["정신력"] = mental_strength

                # 과목별 학습법 및 수강 강사 & 활용 교재
                subject_method_key = None
                for key in study_style_table.keys():
                    if "과목별 학습법" in key or "수강 강사" in key or "활용 교재" in key:
                        subject_method_key = key
                        break

                if subject_method_key:
                    subject_method_text = study_style_table.pop(subject_method_key, "")
                    # 과목별로 분리
                    subjects = story_data["exam_info"].get("subjects", [])
                    if isinstance(subjects, list) and subjects and subject_method_text:
                        subject_methods_dict = self._parse_subject_methods(subject_method_text, subjects)
                        if subject_methods_dict:
                            story_data["subject_methods"] = subject_methods_dict
                        else:
                            story_data["subject_methods"] = {"전체": subject_method_text}
                    else:
                        story_data["subject_methods"] = {"전체": subject_method_text} if subject_method_text else {}

                # 하루 학습 계획
                daily_plan_key = None
                for key in study_style_table.keys():
                    if "하루 학습 계획" in key or "생활 패턴" in key:
                        daily_plan_key = key
                        break

                if daily_plan_key:
                    story_data["daily_plan"] = study_style_table.pop(daily_plan_key, "")

                # 면접 준비 과정
                interview_key = None
                for key in study_style_table.keys():
                    if "면접" in key:
                        interview_key = key
                        break

                if interview_key:
                    interview_text = study_style_table.pop(interview_key, "")
                    # 다른 섹션 내용 제거
                    stop_keywords = ["수험생활중", "어려웠던 점", "합격에 도움이 된", "KEY POINT"]
                    for keyword in stop_keywords:
                        if keyword in interview_text:
                            interview_text = interview_text.split(keyword)[0].strip()
                            break
                    story_data["interview_prep"] = interview_text

                # 수험생활 중 어려웠던 점 및 극복 방법
                difficulties_key = None
                for key in study_style_table.keys():
                    if "어려웠던 점" in key or "극복 방법" in key or "극복방법" in key:
                        difficulties_key = key
                        break

                if difficulties_key:
                    story_data["difficulties"] = study_style_table.pop(difficulties_key, "")

                # 합격에 도움이 된 나만의 학습 KEY POINT
                key_points_key = None
                for key in study_style_table.keys():
                    if "KEY POINT" in key or "핵심" in key or "학습 전략" in key:
                        key_points_key = key
                        break

                if key_points_key:
                    story_data["key_points"] = study_style_table.pop(key_points_key, "")

                # 나머지는 study_style에 저장
                story_data["study_style"].update(study_style_table)

        # 텍스트 기반 섹션 추출 (테이블에서 못 찾은 경우)
        text = soup.get_text(separator='\n', strip=True)
        story_data["raw_text"] = text

        # 패턴 기반 정보 추출
        exam_info_patterns = {
            "year": r"(\d{4})\s*년",
            "exam_type": r"(국가직|지방직|서울시|경기도|인천시|부산시|대구시|광주시|대전시|울산시|세종시)",
            "grade": r"(\d)\s*급",
            "job_series": r"([가-힣]+행정직|일반행정직|교육행정직|보호직|소방직|경찰직|세무직|회계직|관세직|통계직)",
            "subjects": r"(국어|영어|한국사|행정법|행정학|회계학|경제학|세법|관세법|통계학)"
        }

        for key, pattern in exam_info_patterns.items():
            if key not in story_data["exam_info"] or not story_data["exam_info"].get(key):
                match = re.search(pattern, text)
                if match:
                    if key == "subjects":
                        subjects = re.findall(pattern, text)
                        existing = story_data["exam_info"].get("subjects", [])
                        if isinstance(existing, list):
                            story_data["exam_info"][key] = list(set(existing + subjects))
                        else:
                            story_data["exam_info"][key] = list(set(subjects))
                    else:
                        story_data["exam_info"][key] = match.group(1) if match.groups() else match.group(0)

        # 텍스트 기반 섹션 추출 (테이블에서 못 찾은 경우)
        if not story_data.get("daily_plan") or not story_data.get("subject_methods") or not story_data.get("interview_prep") or not story_data.get("difficulties") or not story_data.get("key_points"):
            sections = {
                "하루 학습 계획": "daily_plan",
                "과목별 학습법 및 수강 강사 & 활용 교재": "subject_methods",
                "과목별 학습법": "subject_methods",
                "면접 준비 과정": "interview_prep",
                "면접 준비과정": "interview_prep",
                "수험생활 중 어려웠던 점 및 극복 방법": "difficulties",
                "수험생활중 어려웠던 점과 극복방법": "difficulties",
                "합격에 도움이 된 나만의 학습 KEY POINT": "key_points",
                "합격으로 이끈 나만의 학습 전략 KEY POINT": "key_points"
            }

            lines = text.split('\n')
            current_section = None
            current_content = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                section_found = False
                for section_name, section_key in sections.items():
                    if section_name in line:
                        if story_data.get(section_key):
                            continue

                        if current_section and current_content:
                            content_text = '\n'.join(current_content)
                            for stop_keyword in ["면접", "수험생활중", "어려웠던 점", "합격에 도움이 된", "KEY POINT"]:
                                if stop_keyword in content_text and current_section != section_key:
                                    content_text = content_text.split(stop_keyword)[0].strip()
                                    break

                            if current_section == "subject_methods":
                                subjects = story_data["exam_info"].get("subjects", [])
                                story_data[current_section] = self._parse_subject_methods(content_text, subjects)
                            else:
                                story_data[current_section] = content_text

                        current_section = section_key
                        current_content = []
                        section_found = True
                        break

                if not section_found:
                    if current_section:
                        stop_keywords = {
                            "interview_prep": ["수험생활중", "어려웠던 점", "합격에 도움이 된"],
                            "difficulties": ["합격에 도움이 된", "KEY POINT"],
                            "key_points": ["목록", "TOP", "이전", "다음"]
                        }
                        should_stop = False
                        if current_section in stop_keywords:
                            for keyword in stop_keywords[current_section]:
                                if keyword in line:
                                    should_stop = True
                                    break

                        if not should_stop:
                            current_content.append(line)
                        else:
                            content_text = '\n'.join(current_content)
                            if current_section == "subject_methods":
                                subjects = story_data["exam_info"].get("subjects", [])
                                story_data[current_section] = self._parse_subject_methods(content_text, subjects)
                            else:
                                story_data[current_section] = content_text
                            current_section = None
                            current_content = []

            if current_section and current_content:
                content_text = '\n'.join(current_content)
                for stop_keyword in ["목록", "TOP", "이전", "다음"]:
                    if stop_keyword in content_text:
                        content_text = content_text.split(stop_keyword)[0].strip()
                        break

                if current_section == "subject_methods":
                    subjects = story_data["exam_info"].get("subjects", [])
                    story_data[current_section] = self._parse_subject_methods(content_text, subjects)
                else:
                    story_data[current_section] = content_text

        return story_data

    def _parse_subject_methods(self, text: str, subjects: List[str]) -> Dict[str, str]:
        """과목별 학습법 텍스트를 과목별로 분리"""
        result = {}
        if not text or not subjects:
            return result

        remaining_text = text
        for subject in subjects:
            if subject in remaining_text:
                idx = remaining_text.find(subject)
                if idx >= 0:
                    subject_part = remaining_text[idx:]

                    # 다음 과목명이나 섹션 끝까지 찾기
                    next_subject_idx = len(subject_part)
                    for other_subject in subjects:
                        if other_subject != subject:
                            other_idx = subject_part.find(other_subject, len(subject))
                            if other_idx > 0 and other_idx < next_subject_idx:
                                next_subject_idx = other_idx

                    # 섹션 종료 키워드 확인
                    stop_keywords = ["면접", "수험생활중", "어려웠던 점", "합격에 도움이 된", "KEY POINT"]
                    for keyword in stop_keywords:
                        keyword_idx = subject_part.find(keyword, len(subject))
                        if keyword_idx > 0 and keyword_idx < next_subject_idx:
                            next_subject_idx = keyword_idx

                    subject_text = subject_part[:next_subject_idx].strip()
                    if subject_text:
                        result[subject] = subject_text

                    remaining_text = remaining_text[idx + next_subject_idx:]

        if not result:
            result["전체"] = text

        return result

    def crawl_from_url(self, url: str) -> Optional[Dict[str, Any]]:
        """URL에서 합격수기 데이터 크롤링"""
        try:
            logger.info(f"크롤링 시작: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            # 인코딩 처리: apparent_encoding을 사용하여 더 정확한 인코딩 감지
            if response.apparent_encoding:
                response.encoding = response.apparent_encoding
            elif response.encoding is None or response.encoding == 'ISO-8859-1':
                # 인코딩이 감지되지 않았거나 잘못된 경우, UTF-8로 시도
                response.encoding = 'utf-8'

            # HTML 콘텐츠를 올바른 인코딩으로 디코딩
            html_content = response.text

            story_data = self.parse_story_content(html_content)
            story_data["source_url"] = url
            story_data["crawled_at"] = datetime.now().isoformat()
            story_data["source_site"] = "megagong"

            return story_data

        except Exception as e:
            logger.error(f"크롤링 실패 ({url}): {e}")
            return None

    def load_from_json(self, json_file: str) -> List[Dict[str, Any]]:
        """JSON 파일에서 데이터 로드"""
        json_path = Path(json_file)
        if not json_path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {json_file}")

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, list):
            return data
        else:
            return [data]

    def load_from_csv(self, csv_file: str) -> List[Dict[str, Any]]:
        """CSV 파일에서 데이터 로드"""
        csv_path = Path(csv_file)
        if not csv_path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {csv_file}")

        stories = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                story = {
                    "exam_info": {
                        "year": row.get("year", ""),
                        "exam_type": row.get("exam_type", ""),
                        "grade": row.get("grade", ""),
                        "job_series": row.get("job_series", ""),
                        "subjects": row.get("subjects", "").split(", ") if row.get("subjects") else [],
                        "총 수험기간": row.get("study_period", ""),
                        "하루 평균 학습 시간": row.get("study_hours", "")
                    },
                    "study_style": {
                        "수험생활": row.get("study_life", ""),
                        "평균 회독수": row.get("review_count", ""),
                        "정신력": row.get("mental_strength", "")
                    },
                    "daily_plan": row.get("daily_plan", ""),
                    "subject_methods": json.loads(row.get("subject_methods", "{}")) if row.get("subject_methods") else {},
                    "interview_prep": row.get("interview_prep", ""),
                    "difficulties": row.get("difficulties", ""),
                    "key_points": row.get("key_points", ""),
                    "source_url": row.get("source_url", ""),
                    "crawled_at": row.get("crawled_at", "")
                }
                stories.append(story)

        return stories

    def save_to_json(self, stories: List[Dict[str, Any]], filename: str = "megagong_stories.json"):
        """JSON 파일로 저장"""
        output_path = self.output_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(stories, f, ensure_ascii=False, indent=2)
        logger.info(f"JSON 저장 완료: {output_path} ({len(stories)}개)")

    def save_to_csv(self, stories: List[Dict[str, Any]], filename: str = "megagong_stories.csv"):
        """CSV 파일로 저장"""
        output_path = self.output_dir / filename

        if not stories:
            logger.warning("저장할 데이터가 없습니다.")
            return

        fieldnames = [
            "id", "year", "exam_type", "grade", "job_series", "subjects",
            "study_period", "study_hours", "study_life", "review_count", "mental_strength",
            "daily_plan", "subject_methods", "interview_prep", "difficulties",
            "key_points", "source_url", "crawled_at"
        ]

        rows = []
        for idx, story in enumerate(stories, 1):
            exam_info = story.get("exam_info", {})
            study_style = story.get("study_style", {})

            row = {
                "id": idx,
                "year": exam_info.get("year", ""),
                "exam_type": exam_info.get("exam_type", ""),
                "grade": exam_info.get("grade", ""),
                "job_series": exam_info.get("job_series", ""),
                "subjects": ", ".join(exam_info.get("subjects", [])) if isinstance(exam_info.get("subjects"), list) else exam_info.get("subjects", ""),
                "study_period": exam_info.get("총 수험기간", ""),
                "study_hours": exam_info.get("하루 평균 학습 시간", ""),
                "study_life": study_style.get("수험생활", ""),
                "review_count": study_style.get("평균 회독수", ""),
                "mental_strength": study_style.get("정신력", ""),
                "daily_plan": story.get("daily_plan", ""),
                "subject_methods": json.dumps(story.get("subject_methods", {}), ensure_ascii=False),
                "interview_prep": story.get("interview_prep", ""),
                "difficulties": story.get("difficulties", ""),
                "key_points": story.get("key_points", ""),
                "source_url": story.get("source_url", ""),
                "crawled_at": story.get("crawled_at", "")
            }
            rows.append(row)

        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        logger.info(f"CSV 저장 완료: {output_path} ({len(rows)}개)")


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="메가공 합격수기 데이터 크롤링")
    parser.add_argument("--url", type=str, help="크롤링할 URL")
    parser.add_argument("--urls-file", type=str, help="URL 목록이 담긴 파일")
    parser.add_argument("--input-json", type=str, help="기존 JSON 파일에서 로드")
    parser.add_argument("--input-csv", type=str, help="기존 CSV 파일에서 로드")
    parser.add_argument("--output-dir", type=str, default="data/success_stories/megagong", help="출력 디렉토리")
    parser.add_argument("--format", type=str, choices=["json", "csv", "both"], default="both", help="저장 형식")

    args = parser.parse_args()

    crawler = MegagongStoryCrawler(output_dir=args.output_dir)
    stories = []

    # JSON 파일에서 로드
    if args.input_json:
        stories = crawler.load_from_json(args.input_json)
        logger.info(f"JSON에서 로드: {len(stories)}개")

    # CSV 파일에서 로드
    if args.input_csv:
        stories = crawler.load_from_csv(args.input_csv)
        logger.info(f"CSV에서 로드: {len(stories)}개")

    # 기존 데이터의 URL 목록 추출 (중복 체크용)
    existing_urls = set()
    for story in stories:
        if story.get("source_url"):
            existing_urls.add(story["source_url"])

    # URL 크롤링
    if args.url:
        if args.url in existing_urls:
            logger.info(f"이미 존재하는 URL (건너뜀): {args.url}")
        else:
            story = crawler.crawl_from_url(args.url)
            if story:
                stories.append(story)
                existing_urls.add(args.url)

    if args.urls_file:
        with open(args.urls_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # 공백으로 구분된 URL도 처리
            urls = []
            for line in content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                # 한 줄에 여러 URL이 있을 수 있으므로 공백으로도 분리
                line_urls = [url.strip() for url in line.split() if url.strip() and url.startswith('https://')]
                urls.extend(line_urls)

        # 중복 URL 제거
        unique_urls = []
        seen_urls = set()
        for url in urls:
            if url not in seen_urls:
                unique_urls.append(url)
                seen_urls.add(url)

        logger.info(f"URL 파일에서 {len(urls)}개 읽음, 중복 제거 후 {len(unique_urls)}개")

        added_count = 0
        skipped_count = 0
        for url in unique_urls:
            if url in existing_urls:
                logger.info(f"이미 존재하는 URL (건너뜀): {url}")
                skipped_count += 1
                continue

            story = crawler.crawl_from_url(url)
            if story:
                stories.append(story)
                existing_urls.add(url)
                added_count += 1
                logger.info(f"크롤링 성공 및 추가: {url} (현재 총 {len(stories)}개)")
            else:
                logger.warning(f"크롤링 실패 또는 None 반환: {url}")
            time.sleep(1)

        logger.info(f"크롤링 완료: {added_count}개 추가, {skipped_count}개 건너뜀")

    if not stories:
        logger.warning("처리할 데이터가 없습니다.")
        return

    # 저장
    if args.format in ["json", "both"]:
        crawler.save_to_json(stories)

    if args.format in ["csv", "both"]:
        crawler.save_to_csv(stories)

    logger.info(f"총 {len(stories)}개의 합격수기 데이터를 처리했습니다.")


if __name__ == "__main__":
    main()

