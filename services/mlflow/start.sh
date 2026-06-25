#!/bin/sh
# Install backend driver + S3 client (not bundled in ghcr.io/mlflow/mlflow).
pip install --quiet psycopg2-binary boto3

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

exec mlflow server \
    --backend-store-uri "postgresql://telecom:telecom_pw@postgres:5432/telecom_intel" \
    --default-artifact-root "s3://mlflow/artifacts" \
    --host 0.0.0.0 \
    --port 5000 \
    --serve-artifacts
