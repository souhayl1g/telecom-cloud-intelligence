FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8003
ENV DATABASE_URL=postgresql://telecom:telecom_pw@postgres:5432/telecom_intel
ENV OLLAMA_URL=http://host.docker.internal:11434
ENV OLLAMA_MODEL=qwen2.5:7b

EXPOSE 8003

CMD ["python", "main.py"]
