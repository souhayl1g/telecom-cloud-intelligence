# syntax=docker/dockerfile:1
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# Copy pre-downloaded torch wheel to avoid network timeout
COPY wheels/torch-2.5.1+cpu-cp311-cp311-linux_x86_64.whl /tmp/
RUN pip install /tmp/torch-2.5.1+cpu-cp311-cp311-linux_x86_64.whl \
    numpy==2.0.1 scipy==1.17.1 scikit-learn==1.5.2 joblib==1.4.2 \
    lightgbm==4.6.0 \
    fastapi==0.115.0 "uvicorn[standard]==0.30.6" pydantic==2.8.2 \
    opentelemetry-api==1.25.0 opentelemetry-sdk==1.25.0 \
    opentelemetry-exporter-otlp-proto-grpc==1.25.0 \
    opentelemetry-instrumentation-fastapi==0.46b0 \
    opentelemetry-instrumentation-logging==0.46b0

# Install xgboost without GPU deps (nvidia-nccl is huge + unnecessary for CPU inference)
RUN pip install --no-deps xgboost==2.1.4

COPY . /app
RUN mkdir -p /app/models
EXPOSE 8001
CMD ["sh", "-c", "python bootstrap_models.py && uvicorn main:app --host 0.0.0.0 --port 8001"]
