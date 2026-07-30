# NEXUS backend — immagine di produzione.
#
# Il build context è la ROOT del repository (non ./server): il backend serve
# anche il worker LocalBridge e il manifest di deployment, che vivono fuori da
# server/ (AUD0-DEP-010, AUD0-DEP-011, AUD0-DEPLOY-DOCKER-002).
#
# Build:  docker build -f server/Dockerfile -t nexus-backend .
# AUD0-SUPPLY-002 — IMMAGINE BASE NON ANCORATA AL DIGEST.
#
# `python:3.12-slim` e' un tag MUTABILE: lo stesso Dockerfile, ricostruito fra
# una settimana, produce un'immagine diversa. Una build non riproducibile
# significa che non si puo' sapere cosa sta girando in produzione ne' tornare
# esattamente alla versione precedente.
#
# Il digest va aggiornato deliberatamente (rinnovo pianificato delle patch di
# sicurezza), non subito in silenzio a ogni build. Per aggiornarlo:
#   docker pull python:3.12-slim && docker inspect --format='{{index .RepoDigests 0}}' python:3.12-slim
#
# NOTA: il digest qui sotto va sostituito con quello effettivamente verificato
# nel proprio ambiente prima del rilascio; finche' resta il tag, la build NON e'
# riproducibile e questo e' un difetto aperto, non una scelta.
FROM python:3.12-slim

# AUD0-DEP-008 / AUD0-DEPLOY-DOCKER-003: il container girava come root.
RUN groupadd --system --gid 10001 nexus \
 && useradd --system --uid 10001 --gid nexus --home /app --shell /usr/sbin/nologin nexus

WORKDIR /app

# AUD0-SUPPLY-001: se esiste il lock riproducibile lo si usa con verifica degli
# hash; altrimenti si ricade sul file di intento, dichiarandolo nel log della
# build invece di far sembrare riproducibile una build che non lo e'.
COPY server/requirements.txt ./requirements.txt
COPY server/requirements.lock.tx[t] ./
RUN if [ -f requirements.lock.txt ]; then \
        echo "[build] installo dal lock riproducibile (hash verificati)"; \
        pip install --no-cache-dir --require-hashes -r requirements.lock.txt; \
    else \
        echo "[build][ATTENZIONE] requirements.lock.txt assente: build NON riproducibile"; \
        pip install --no-cache-dir -r requirements.txt; \
    fi

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

# /data è un volume: il chown qui riguarda solo il layer immagine. Il disco
# persistente reale viene montato da Render a runtime con proprietario
# proprio (root di norma), quindi va risistemato dall'entrypoint a ogni
# avvio — vedi docker-entrypoint.sh.
RUN mkdir -p /data && chown -R nexus:nexus /app /data \
 && chmod +x docker-entrypoint.sh

EXPOSE 8001

# AUD0-DEP-005: nessun healthcheck. Si usa /api/ready (database + migrazioni +
# preflight di sicurezza), non /api/health che prova solo la liveness.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os,urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:%s/api/ready' % os.environ.get('PORT','8001'), timeout=4).status == 200 else 1)"

# Resta root fino all'entrypoint: serve per il chown del volume montato a
# runtime. L'entrypoint droppa a nexus (uid 10001) via su prima di eseguire
# il comando applicativo — il processo servito non gira mai come root.
ENTRYPOINT ["./docker-entrypoint.sh"]

# Il cloud (Render/Railway) inietta la variabile PORT; in locale usa 8001.
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8001}"]
