"""
Purge MinIO `raw/` bucket of everything except `bss/` + `oss/` datasets.

Why
---
Old pipeline cycles dumped `run-*.json` files into `raw/`. The agreed semantic
for the raw bucket is "operator-supplied datasets only" — same content as
TT_data/ on disk. This script enforces that invariant by deleting any key
whose prefix is not `bss/` or `oss/`.

Re-runnable. Idempotent.

Run
---
    python services/data-ingest/cleanup_minio_raw.py
    # or
    make clean-minio-raw
"""

from __future__ import annotations

import os

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "http://localhost:9000")
S3_KEY = os.environ.get("S3_ACCESS_KEY", "minio")
S3_SECRET = os.environ.get("S3_SECRET_KEY", "minio_pw")
BUCKET = "raw"

ALLOWED_PREFIXES = ("bss/", "oss/")


def main():
    s3 = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_KEY,
        aws_secret_access_key=S3_SECRET,
        config=Config(signature_version="s3v4"),
    )

    try:
        s3.head_bucket(Bucket=BUCKET)
    except ClientError:
        print("raw bucket does not exist; nothing to clean.")
        return

    paginator = s3.get_paginator("list_objects_v2")
    to_delete = []
    kept = 0
    for page in paginator.paginate(Bucket=BUCKET):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if any(key.startswith(p) for p in ALLOWED_PREFIXES):
                kept += 1
                continue
            to_delete.append({"Key": key})

    if not to_delete:
        print(f"raw bucket clean — {kept} dataset objects retained.")
        return

    print(
        f"Found {len(to_delete)} stale objects to delete (keeping {kept} dataset objects)."
    )

    # S3 delete_objects accepts max 1000 keys per call
    deleted = 0
    for i in range(0, len(to_delete), 1000):
        chunk = to_delete[i : i + 1000]
        resp = s3.delete_objects(
            Bucket=BUCKET, Delete={"Objects": chunk, "Quiet": True}
        )
        deleted += len(chunk)
        errors = resp.get("Errors", [])
        if errors:
            print(f"  WARNING — {len(errors)} errors on batch {i // 1000}")

    print(f"Deleted {deleted} objects. Raw bucket now contains only bss/ + oss/.")


if __name__ == "__main__":
    main()
