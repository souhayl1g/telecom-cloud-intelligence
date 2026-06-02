"""Central config for pipeline-worker — reads all env vars in one place."""
import os

DATABASE_URL: str = os.getenv("DATABASE_URL", "")
AI_SERVICE_URL: str = os.getenv("AI_SERVICE_URL", "http://ai-service:8001").rstrip("/")
S3_ENDPOINT: str = os.getenv("S3_ENDPOINT", "http://minio:9000")
S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY", "minio")
S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY", "minio_pw")
RUN_MODE: str = os.getenv("RUN_MODE", "daemon")
CYCLE_SECONDS: int = int(os.getenv("CYCLE_SECONDS", "120"))

BUCKETS = ["raw", "processed", "curated"]
SYNTHETIC_N_RECORDS = 200
REGION_DEFAULT = "demo"
INTERNAL_API_KEY: str = os.getenv("INTERNAL_API_KEY", "")
