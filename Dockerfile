# API Trilha Atitus — use este Dockerfile no serviço da API (raiz do repo).
FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# SQLite persistente: no Railway, adicione um Volume montado em /data
ENV PYTHONUNBUFFERED=1
ENV TRILHA_DATA_DIR=/data
RUN mkdir -p /data
EXPOSE 8000

CMD ["sh", "-c", "mkdir -p \"$TRILHA_DATA_DIR\" && uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
