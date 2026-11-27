#!/bin/sh
# Il disco persistente montato da Render su /data arriva DOPO il build dell'immagine: il chown fatto nel Dockerfile riguarda solo il layer
# dell'immagine, non il volume reale, che Render monta con proprietario di default (root). Senza sistemare i permessi il processo nexus
# (uid 10001) trova il database in sola lettura (sqlite3.OperationalError: attempt to write a readonly database).
#
# Questo script gira come root (nessun USER nel Dockerfile), sistema i permessi del volume montato, poi lascia il processo applicativo a un
# utente non privilegiato. Si usa `su` (gia' nell'immagine base) invece di gosu: `su -c` accetta solo una stringa, quindi si passa un
# argomento fittizio come $0 e si ricostruisce l'array con "$@" dentro la shell invocata.
#
# CHART-ONLY-DEPLOY-READY-01 / GATE 01 - autorita' persistente del Chart OPERATOR-ONLY:
#  * se NEXUS_CHART_AUTH_FILE e' impostata (autorita' persistente su /data) NON si fa piu' `chown -R nexus:nexus /data` indiscriminato:
#    `chart-authority boot` (root) rende /data root:nexus 01770, assegna a nexus tutto TRANNE i namespace protetti (chart_auth, chart_store) che restano
#    root:root in sola lettura per l'app, verifica il confine (modello + probe di kernel come utente nexus) e, se richiesto, installa il record da
#    CHART_AUTHORITY_B64 (variabile impostata solo dall'operatore nella dashboard);
#  * se il confine non e' verificato, il Chart riceve un percorso d'autorita' INESISTENTE (nega tutto) e il backend parte comunque (fail-closed solo per il Chart);
#  * se NEXUS_CHART_AUTH_FILE non e' impostata il comportamento resta quello storico (chown -R /data).
set -e

mkdir -p /data

CTL="${CHART_AUTHORITY_CTL:-/usr/local/sbin/chart-authority}"
DENIED_AUTH="/nonexistent/chart-authority-boundary-not-verified/chart_authorization.json"
APP_USER="${CHART_APP_USER:-nexus}"

legacy_chown() {
    chown -R "$APP_USER:$APP_USER" /data
}

selective_chown_fallback() {
    # usato solo se `chart-authority boot` fallisce: l'app deve poter scrivere DB/Jarvis, i namespace protetti non vengono MAI ceduti a nexus
    find /data -mindepth 1 -maxdepth 1 \
        ! -name chart_auth ! -name 'chart_auth.*' ! -name chart_store ! -name 'chart_store.*' ! -name '.chart_boundary_canary*' \
        -exec chown -R "$APP_USER:$APP_USER" {} + || true
}

if [ "$(id -u)" = "0" ]; then
    if [ -n "${NEXUS_CHART_AUTH_FILE:-}" ]; then
        rc=0
        if [ -x "$CTL" ]; then
            "$CTL" boot || rc=$?
        else
            echo "[entrypoint] ERRORE: $CTL assente" >&2
            rc=127
        fi
        if [ "$rc" != "0" ]; then
            echo "[entrypoint] confine dell'autorita' NON verificato (rc=$rc): il Chart rifiutera' ogni dato; il backend parte comunque" >&2
            selective_chown_fallback
            export NEXUS_CHART_AUTH_FILE="$DENIED_AUTH"
        fi
    else
        legacy_chown
    fi
    exec su -s /bin/sh -c 'exec "$@"' "$APP_USER" -- dummy "$@"
fi

# Avvio gia' non-root (es. `docker run --user`): il confine non puo' essere stabilito/verificato => fail-closed per il Chart
if [ -n "${NEXUS_CHART_AUTH_FILE:-}" ]; then
    echo "[entrypoint] non-root: confine dell'autorita' non verificabile, Chart in fail-closed" >&2
    export NEXUS_CHART_AUTH_FILE="$DENIED_AUTH"
fi
exec "$@"
