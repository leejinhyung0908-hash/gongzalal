import psycopg, os
import urllib.request
from dotenv import load_dotenv
load_dotenv('/home/ubuntu/rag/.env')
url = os.getenv('DATABASE_URL','').replace('postgresql+psycopg://','postgresql://')

with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        # 교육학개론-B 외 다른 시험 이미지 5개 가져오기
        cur.execute("""
            SELECT qi.id, qi.file_path, e.year, e.subject
            FROM question_images qi
            JOIN questions q ON qi.question_id = q.id
            JOIN exams e ON q.exam_id = e.id
            WHERE qi.file_path LIKE 'https://%'
              AND qi.file_path NOT LIKE '%교육학개론%'
            LIMIT 5
        """)
        rows = cur.fetchall()

print("=== 교육학개론 외 이미지 S3 접근 테스트 ===")
for row in rows:
    img_id, fp, year, subject = row
    print(f"\nID={img_id}, {year}년 {subject}")
    print(f"URL: {fp}")
    try:
        req = urllib.request.Request(fp, method='HEAD')
        resp = urllib.request.urlopen(req, timeout=5)
        print(f"  → HTTP {resp.status} OK")
    except urllib.error.HTTPError as e:
        print(f"  → HTTP {e.code} 접근 불가")
    except Exception as e:
        print(f"  → 오류: {e}")
