FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY . /app
# Copy pre-trained models from notebooks (if available at build time)
# Models can also be mounted via Docker volume at /app/models/
RUN mkdir -p /app/models
EXPOSE 8001
CMD ["sh", "-c", "python bootstrap_models.py && uvicorn main:app --host 0.0.0.0 --port 8001"]
