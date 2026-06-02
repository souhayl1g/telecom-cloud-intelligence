# retrain-service — runs ML training notebooks on demand via papermill.
# Built on top of the notebooks image (LightGBM/XGBoost/PyTorch already installed).
# Adds FastAPI/uvicorn/papermill layer.

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc libpq-dev curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Reuse the same training-deps set as notebooks image.
COPY notebooks/requirements.txt /tmp/nb-req.txt
RUN pip install --no-cache-dir -r /tmp/nb-req.txt \
    && pip install --no-cache-dir \
        lightgbm==4.5.0 xgboost==2.1.1 torch==2.4.1 nbformat==5.10.4

COPY services/retrain-service/requirements.txt /tmp/svc-req.txt
RUN pip install --no-cache-dir -r /tmp/svc-req.txt

COPY services/retrain-service/main.py /app/main.py

EXPOSE 8004

HEALTHCHECK --interval=15s --timeout=5s --retries=3 --start-period=20s \
    CMD curl -fsS "http://127.0.0.1:8004/health" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]
