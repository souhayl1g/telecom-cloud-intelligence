FROM ghcr.io/mlflow/mlflow:v2.15.1
RUN pip install --no-cache-dir psycopg2-binary boto3
COPY start.sh /start.sh
RUN chmod +x /start.sh
