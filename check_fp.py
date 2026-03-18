import psycopg, os
from dotenv import load_dotenv
load_dotenv('/home/ubuntu/rag/.env')
url = os.getenv('DATABASE_URL','').replace('postgresql+psycopg://','postgresql://')
with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        cur.execute('SELECT id, file_path FROM question_images LIMIT 5')
        for row in cur.fetchall():
            print(row[0], repr(row[1]))
