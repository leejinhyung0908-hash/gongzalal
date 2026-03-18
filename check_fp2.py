import psycopg, os
from dotenv import load_dotenv
load_dotenv('/home/ubuntu/rag/.env')
url = os.getenv('DATABASE_URL','').replace('postgresql+psycopg://','postgresql://')
with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        # 전체 이미지 수 및 S3 URL vs 로컬 경로 분류
        cur.execute("SELECT COUNT(*) FROM question_images")
        total = cur.fetchone()[0]
        print(f"전체 이미지 수: {total}")

        cur.execute("SELECT COUNT(*) FROM question_images WHERE file_path LIKE 'https://%'")
        s3_count = cur.fetchone()[0]
        print(f"S3 URL 이미지: {s3_count}")
        print(f"로컬 경로 이미지: {total - s3_count}")

        # 로컬 경로 샘플 5개
        cur.execute("SELECT id, file_path FROM question_images WHERE file_path NOT LIKE 'https://%' LIMIT 5")
        rows = cur.fetchall()
        if rows:
            print("\n[로컬 경로 샘플]")
            for row in rows:
                print(f"  id={row[0]}, path={repr(row[1])}")
        else:
            print("\n로컬 경로 이미지 없음 - 모두 S3 URL")
