# NEXUS backend — immagine di produzione.
#
# Il build context è la ROOT del repository (non ./server): il backend serve
# anche il worker LocalBridge e il manifest di deployment, che vivono fuori da
# server/ (AUD0-DEP-010, AUD0-DEP-011, AUD0-DEPLOY-DOCKER-002).
#
# Build:  docker build -f server/Dockerfile -t nexus-backend .
FROM python:3.12-slim

# AUD0-DEP-008 / AUD0-DEPLOY-DOCKER-003: il container girava come root.
RUN groupadd --system --gid 10001 nexus \
 && useradd --system --uid 10001 --gid nexus --home /app --shell /usr/sbin/nologin nexus

WORKDIR /app

COPY server/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# AUD0-DEP-006 / AUD0-DEPLOY-DOCKER-001: la lista fissa di COPY ometteva
# moduli importati da app.py (strategy_registry, settings_contract,
# settings_schema, command_contract, ledger_analytics), quindi un'immagine
# pulita falliva all'import. Si copia l'intero package applicativo.
COPY server/ ./

# Artefatti serviti dal backend ma originati fuori dal build context di server/.
COPY LocalBridge/nexus_local_worker.py /app/protected/nexus_local_worker.py
COPY deploy/deployment-manifest.json /app/protected/deployment-manifest.json
COPY contracts/ /app/contracts/

ENV NEXUS_DB_PATH=/data/nexus.db \
    NEXUS_WORKER_FILE=/app/protected/nexus_local_worker.py \
    NEXUS_DEPLOY_MANIFEST=/app/protected/deployment-manifest.json \
    NEXUS_DOWNLOADS_DIR=/app/protected/downloads \
    PYTHONUNBUFFERED=1

# /data è un volume: deve essere scrivibile dall'utente non privilegiato.
RUN mkdir -p /data && chown -R nexus:nexus /app /data

USER nexus
EXPOSE 8001

# AUD0-DEP-005: nessun healthcheck. Si usa /api/ready (database + migrazioni +
# preflight di sicurezza), non /api/health che prova solo la liveness.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os,urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:%s/api/ready' % os.environ.get('PORT','8001'), timeout=4).status == 200 else 1)"

# Il cloud (Render/Railway) inietta la variabile PORT; in locale usa 8001.
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8001}"]
