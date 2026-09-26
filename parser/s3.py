"""Upload the downloaded photos to S3-compatible object storage.

Targets any S3 API — here Yandex Object Storage via AWS_ENDPOINT_URL. Uploads
are idempotent: a photo whose s3_key is already recorded in the database is
skipped, so the sync can run repeatedly while a crawl is still going.
"""
import mimetypes
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from . import config, db

BUCKET = os.getenv("S3_BUCKET", "").strip()
PREFIX = os.getenv("S3_PREFIX", "guazi/images").strip("/")
ENDPOINT = os.getenv("AWS_ENDPOINT_URL", "").strip() or None
REGION = os.getenv("AWS_REGION", "").strip() or None
WORKERS = int(os.getenv("S3_CONCURRENCY", "8"))


def client():
    return boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        region_name=REGION,
        config=Config(retries={"max_attempts": 5, "mode": "standard"},
                      s3={"addressing_style": "path"}),
    )


def list_buckets() -> list[str]:
    return [b["Name"] for b in client().list_buckets().get("Buckets", [])]


def key_for(car_id: str, filename: str) -> str:
    return f"{PREFIX}/{car_id}/{filename}"


def public_url(key: str) -> str:
    host = (ENDPOINT or "https://storage.yandexcloud.net").rstrip("/")
    return f"{host}/{BUCKET}/{key}"


def ensure_columns() -> None:
    """Add the S3 columns if this database predates them."""
    with db.connect() as conn:
        conn.execute("ALTER TABLE car_images ADD COLUMN IF NOT EXISTS s3_key text")
        conn.execute("ALTER TABLE car_images ADD COLUMN IF NOT EXISTS s3_url text")
        conn.execute("ALTER TABLE car_images ADD COLUMN IF NOT EXISTS s3_uploaded_at timestamptz")


def _pending() -> list[tuple[int, str, str]]:
    """(image id, local path, car listing_id) for photos not yet in the bucket."""
    with db.connect() as conn:
        return conn.execute("""
            select i.id, i.file_path, c.listing_id
            from car_images i join cars c on c.id = i.car_id
            where i.downloaded and i.file_path is not null and i.s3_key is null
            order by c.listing_id, i.position
        """).fetchall()


def _upload_one(s3, row) -> tuple[int, str, str] | None:
    img_id, path, listing_id = row
    local = Path(path)
    if not local.is_absolute():
        local = Path.cwd() / local
    if not local.exists():
        return None
    key = key_for(listing_id, local.name)

    # Already there (for instance after the database was rebuilt): record the
    # key rather than sending the bytes again.
    try:
        s3.head_object(Bucket=BUCKET, Key=key)
        return img_id, key, public_url(key)
    except ClientError as e:
        if e.response["Error"].get("Code") not in ("404", "NoSuchKey", "403"):
            print(f"[s3] head failed {key}: {e.response['Error'].get('Code')}")

    ctype = mimetypes.guess_type(local.name)[0] or "application/octet-stream"
    try:
        s3.upload_file(str(local), BUCKET, key,
                       ExtraArgs={"ContentType": ctype})
    except ClientError as e:
        print(f"[s3] failed {key}: {e.response['Error'].get('Code')}")
        return None
    return img_id, key, public_url(key)


def sync() -> int:
    """Upload every photo that is not in the bucket yet; record keys in the DB."""
    if not BUCKET:
        print("[s3] S3_BUCKET is not set in .env — nothing to upload to")
        return 1
    if not db.enabled():
        print("[s3] DATABASE_URL is not set")
        return 1

    ensure_columns()
    rows = _pending()
    if not rows:
        print("[s3] nothing to upload — every downloaded photo is already in the bucket")
        return 0

    print(f"[s3] uploading {len(rows)} photos to s3://{BUCKET}/{PREFIX}/ "
          f"via {ENDPOINT or 'aws'}")
    s3 = client()
    done, failed = [], 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for i, res in enumerate(pool.map(lambda r: _upload_one(s3, r), rows), 1):
            if res is None:
                failed += 1
            else:
                done.append(res)
            if i % 100 == 0:
                print(f"[s3]   {i}/{len(rows)}")

    if done:
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.executemany(
                    "update car_images set s3_key=%s, s3_url=%s, s3_uploaded_at=now()"
                    " where id=%s",
                    [(k, u, i) for i, k, u in done])
    print(f"[s3] uploaded {len(done)}, failed {failed}")
    return 0 if not failed else 1


def status() -> None:
    ensure_columns()
    with db.connect() as conn:
        total, up = conn.execute(
            "select count(*), count(s3_key) from car_images where downloaded").fetchone()
    print(f"[s3] {up}/{total} photos in the bucket")


if __name__ == "__main__":
    import sys
    raise SystemExit(sync() if len(sys.argv) < 2 or sys.argv[1] == "sync"
                     else (status() or 0))
