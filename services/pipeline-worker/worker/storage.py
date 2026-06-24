"""MinIO/S3 helpers for pipeline-worker."""

import json
from io import BytesIO

import boto3

from worker.config import S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY


def get_s3():
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
    )


def ensure_buckets(s3, buckets: list[str]) -> None:
    existing = {b["Name"] for b in s3.list_buckets().get("Buckets", [])}
    for bucket in buckets:
        if bucket not in existing:
            s3.create_bucket(Bucket=bucket)
            print(f"  created bucket: {bucket}")
        else:
            print(f"  bucket exists:  {bucket}")


def upload_json(s3, bucket: str, key: str, records: list[dict]) -> None:
    body = json.dumps(records, indent=2).encode()
    s3.put_object(Bucket=bucket, Key=key, Body=BytesIO(body), ContentLength=len(body))
    print(
        f"  uploaded s3://{bucket}/{key}  ({len(records)} records, {len(body):,} bytes)"
    )
