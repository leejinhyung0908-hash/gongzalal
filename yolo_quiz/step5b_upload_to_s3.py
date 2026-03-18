"""
5b단계: 크롭된 문항 이미지를 S3에 업로드하고 DB file_path를 S3 URL로 업데이트

사용법:
    python step5b_upload_to_s3.py
    python step5b_upload_to_s3.py --dry-run       # 실제 업로드 없이 미리보기
    python step5b_upload_to_s3.py --skip-upload   # 이미 업로드된 경우 DB 업데이트만

환경변수 (.env):
    DATABASE_URL  - Neon PostgreSQL 연결 문자열
    AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY
    AWS_REGION        (기본값: ap-northeast-2)
    S3_BUCKET_NAME    (기본값: gongzalal)
    S3_PREFIX         (기본값: question_images)
"""

import os
import sys
import argparse
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# ── 설정 ──────────────────────────────────────────────
DATABASE_URL   = os.getenv("DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://")
AWS_REGION     = os.getenv("AWS_REGION", "ap-northeast-2")
S3_BUCKET      = os.getenv("S3_BUCKET_NAME", "gongzalal")
S3_PREFIX      = os.getenv("S3_PREFIX", "question_images").rstrip("/")
CROPS_BASE_DIR = Path(__file__).parent / "data" / "crops"
# ──────────────────────────────────────────────────────


def s3_url(key: str) -> str:
    return f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}"


def local_path_from_db(file_path: str) -> Path:
    """DB의 file_path(상대/절대 모두)를 실제 로컬 경로로 변환."""
    p = Path(file_path)
    # "data/crops/..." 형태이면 yolo_quiz/ 기준으로 해석
    if not p.is_absolute():
        candidate = Path(__file__).parent / p
        if candidate.exists():
            return candidate
        # "data/crops" 없이 파일명만 있는 경우 전체 탐색
        name = p.name
        for found in CROPS_BASE_DIR.rglob(name):
            return found
    return p


def s3_key_from_db(file_path: str) -> str:
    """DB file_path → S3 키 (question_images/[폴더]/[파일])."""
    p = Path(file_path)
    # "data/crops/폴더/파일" → "폴더/파일"
    parts = p.parts
    try:
        idx = parts.index("crops")
        relative = "/".join(parts[idx + 1:])
    except ValueError:
        relative = p.name
    return f"{S3_PREFIX}/{relative}"


def upload_file(s3_client, local: Path, key: str) -> bool:
    """파일을 S3에 업로드. 이미 존재하면 건너뜀."""
    try:
        s3_client.head_object(Bucket=S3_BUCKET, Key=key)
        return False  # 이미 존재
    except ClientError as e:
        if e.response["Error"]["Code"] != "404":
            raise

    content_type = "image/webp" if local.suffix == ".webp" else "image/jpeg"
    s3_client.upload_file(
        str(local),
        S3_BUCKET,
        key,
        ExtraArgs={"ContentType": content_type},
    )
    return True  # 새로 업로드


def run(dry_run: bool = False, skip_upload: bool = False):
    if not DATABASE_URL:
        print("❌ DATABASE_URL 환경변수가 설정되지 않았습니다.")
        sys.exit(1)

    # S3 클라이언트
    if not skip_upload:
        s3 = boto3.client(
            "s3",
            region_name=AWS_REGION,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )

    # DB 연결
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, file_path
            FROM question_images
            WHERE file_path NOT LIKE 'https://%'
            ORDER BY id
            """
        )
        rows = cur.fetchall()

    print(f"\n📋 업데이트 대상: {len(rows)}건")
    if not rows:
        print("✅ 이미 모든 레코드가 S3 URL입니다.")
        conn.close()
        return

    uploaded = 0
    skipped  = 0
    failed   = 0
    updated  = 0

    for row in rows:
        db_id     = row["id"]
        file_path = row["file_path"]
        local     = local_path_from_db(file_path)
        key       = s3_key_from_db(file_path)
        url       = s3_url(key)

        if dry_run:
            exists = "✅" if local.exists() else "❌"
            print(f"  [{db_id}] {exists} {local.name} → {key}")
            continue

        # 업로드
        if not skip_upload:
            if not local.exists():
                print(f"  ⚠️  [{db_id}] 로컬 파일 없음: {local}")
                failed += 1
                continue
            try:
                new = upload_file(s3, local, key)
                if new:
                    uploaded += 1
                else:
                    skipped += 1
            except Exception as e:
                print(f"  ❌ [{db_id}] 업로드 실패: {e}")
                failed += 1
                continue

        # DB 업데이트
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE question_images SET file_path = %s WHERE id = %s",
                (url, db_id),
            )
        conn.commit()
        updated += 1

        if updated % 50 == 0:
            print(f"  ... {updated}건 처리 중")

    conn.close()

    if not dry_run:
        print(f"\n✅ 완료")
        print(f"   업로드(신규): {uploaded}건")
        print(f"   업로드(스킵): {skipped}건")
        print(f"   실패:        {failed}건")
        print(f"   DB 업데이트: {updated}건")
        print(f"\n🔗 S3 기본 경로: https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{S3_PREFIX}/")


def main():
    parser = argparse.ArgumentParser(description="크롭 이미지 S3 업로드 + DB URL 업데이트")
    parser.add_argument("--dry-run",     action="store_true", help="업로드 없이 미리보기")
    parser.add_argument("--skip-upload", action="store_true", help="업로드 건너뛰고 DB만 업데이트")
    args = parser.parse_args()

    print("=" * 55)
    print(" 📤 문항 이미지 S3 업로드 + DB URL 업데이트")
    print("=" * 55)
    print(f"  버킷:   {S3_BUCKET}")
    print(f"  프리픽스: {S3_PREFIX}/")
    print(f"  리전:   {AWS_REGION}")
    print(f"  로컬:   {CROPS_BASE_DIR}")

    run(dry_run=args.dry_run, skip_upload=args.skip_upload)


if __name__ == "__main__":
    main()
