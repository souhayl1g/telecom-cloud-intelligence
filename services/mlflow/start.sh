#!/bin/sh
# Create the mlflow bucket in MinIO before starting the server.
# Swallows BucketAlreadyOwnedByYou — idempotent on every restart.
python3 - <<'PY'
import sys
try:
    import boto3, botocore
    s3 = boto3.client(
        "s3",
        endpoint_url="http://minio:9000",
        aws_access_key_id="minio",
        aws_secret_access_key="minio_pw",
    )
    s3.create_bucket(Bucket="mlflow")
    print("mlflow bucket created")
except Exception as e:
    print(f"bucket init: {e} (likely already exists — ok)")
PY

# Cap workers at 2 (single-user demo) — the default of 4 sync workers overruns the
# mem_limit and gunicorn OOM-kills them mid-response, which surfaces in the browser as
# ERR_EMPTY_RESPONSE on both static chunks and API calls. A longer worker timeout keeps
# slow artifact/DB calls from being reaped at the 30s default.
exec mlflow server \
    --backend-store-uri "postgresql://telecom:telecom_pw@postgres:5432/telecom_intel" \
    --default-artifact-root "s3://mlflow/artifacts" \
    --host 0.0.0.0 \
    --port 5000 \
    --serve-artifacts \
    --workers 2 \
    --gunicorn-opts "--timeout 120 --graceful-timeout 30"
