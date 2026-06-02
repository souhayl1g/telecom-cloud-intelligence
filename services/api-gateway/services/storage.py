"""MinIO/S3 helpers shared across api-gateway routers.

Lazy-inits a single boto3 client at first use to avoid import-time failures
when MinIO is not reachable (e.g. during tests).
"""

from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from io import BytesIO
from typing import Optional

import boto3
from botocore.client import Config

S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://minio:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "minio")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "minio_pw")
REPORTS_BUCKET = os.getenv("REPORTS_BUCKET", "reports")
REPORTS_URL_TTL_SECONDS = int(os.getenv("REPORTS_URL_TTL_SECONDS", str(7 * 24 * 3600)))
PUBLIC_S3_ENDPOINT = os.getenv("PUBLIC_S3_ENDPOINT", "http://localhost:9000")

_client = None          # internal client (uploads/list/get over docker network)
_presign_client = None  # signing client bound to PUBLIC_S3_ENDPOINT


def _build_client(endpoint_url: str):
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        config=Config(signature_version="s3v4"),
    )


def get_s3():
    """Return a cached boto3 S3 client for in-cluster operations (uploads, list)."""
    global _client
    if _client is None:
        _client = _build_client(S3_ENDPOINT)
    return _client


def get_presign_s3():
    """Return a cached boto3 S3 client whose endpoint_url matches the browser-reachable host.

    SigV4 binds the Host header into the signature. Generating the presigned URL
    against PUBLIC_S3_ENDPOINT guarantees the signature stays valid when the browser
    requests it from localhost (or whatever externally-reachable host you set).
    """
    global _presign_client
    if _presign_client is None:
        endpoint = PUBLIC_S3_ENDPOINT or S3_ENDPOINT
        _presign_client = _build_client(endpoint)
    return _presign_client


def ensure_bucket(bucket: str) -> None:
    s3 = get_s3()
    try:
        existing = {b["Name"] for b in s3.list_buckets().get("Buckets", [])}
        if bucket not in existing:
            s3.create_bucket(Bucket=bucket)
    except Exception as e:
        print(f"[storage] ensure_bucket({bucket}) failed: {e}")


def upload_bytes(
    *,
    bucket: str,
    key: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    ensure_bucket(bucket)
    s3 = get_s3()
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=BytesIO(data),
        ContentLength=len(data),
        ContentType=content_type,
    )
    return key


def presign_url(*, bucket: str, key: str, ttl_seconds: int = REPORTS_URL_TTL_SECONDS) -> tuple[str, datetime]:
    """Generate a presigned GET URL signed against PUBLIC_S3_ENDPOINT.

    Returns (url, expires_at). The signing client's endpoint matches what the
    browser will request, so the SigV4 Host header check passes.
    """
    s3 = get_presign_s3()
    url = s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=ttl_seconds,
    )
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    return url, expires_at


def download_bytes(*, bucket: str, key: str) -> bytes:
    """Fetch object bytes from MinIO (uses internal client)."""
    s3 = get_s3()
    obj = s3.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read()


def upload_report_pdf(
    *,
    pdf_bytes: bytes,
    report_id: str,
    area: Optional[str] = None,
) -> tuple[str, str, datetime]:
    """Upload a capacity report PDF to MinIO + return (key, presigned_url, expires_at)."""
    date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    area_seg = (area or "all").replace("/", "_").replace(" ", "_")
    key = f"{date_prefix}/{area_seg}/{report_id}.pdf"
    upload_bytes(
        bucket=REPORTS_BUCKET,
        key=key,
        data=pdf_bytes,
        content_type="application/pdf",
    )
    url, expires_at = presign_url(bucket=REPORTS_BUCKET, key=key)
    return key, url, expires_at


def upload_notebook_artifact(
    *,
    notebook_bytes: bytes,
    run_id: str,
    model_name: str,
) -> tuple[str, str, datetime]:
    """Upload an executed retrain notebook .ipynb to MinIO."""
    date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    bucket = "retrain-runs"
    key = f"{date_prefix}/{model_name}/{run_id}.ipynb"
    upload_bytes(
        bucket=bucket,
        key=key,
        data=notebook_bytes,
        content_type="application/x-ipynb+json",
    )
    url, expires_at = presign_url(bucket=bucket, key=key)
    return key, url, expires_at
