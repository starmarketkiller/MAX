FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY backtest.py .
COPY nexus_local_worker.py .
COPY static ./static

ENV NEXUS_DB_PATH=/data/nexus.db
EXPOSE 8001

# Il cloud (Render/Railway) inietta la variabile PORT; in locale usa 8001.
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8001}"]
