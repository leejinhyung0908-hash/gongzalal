import psycopg2
import sys
import io

# Windows 콘솔 인코딩 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Neon에서 복사한 URL을 여기에 넣으세요
conn_string = "postgresql://neondb_owner:npg_5gUtKvmle0MI@ep-restless-surf-a1aft67h-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

try:
    conn = psycopg2.connect(conn_string)
    print("[성공] Neon PGVector 연결 성공!")

    cur = conn.cursor()
    # pgvector 확장 기능이 활성화되어 있는지 확인
    cur.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
    extension = cur.fetchone()

    if extension:
        print("[확인] PGVector 확장 프로그램이 이미 설치되어 있습니다.")
    else:
        print("[경고] 연결은 되었으나 pgvector 확장이 없습니다. 'CREATE EXTENSION vector;'가 필요합니다.")

    cur.close()
    conn.close()
except Exception as e:
    print(f"[실패] 연결 실패: {e}")
