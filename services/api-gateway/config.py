import os

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"

DATABASE_URL = os.getenv("DATABASE_URL")

AGENT_SERVICE_URL = os.getenv("AGENT_SERVICE_URL", "http://agent-service:8003")
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://ai-service:8001")

OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "api-gateway")
