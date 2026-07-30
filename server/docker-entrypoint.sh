#!/bin/sh
# Il disco persistente montato da Render su /data arriva DOPO il build
# dell'immagine: il chown fatto nel Dockerfile riguarda solo il layer
# dell'immagine, non il volume reale, che Render monta con proprietario
# di default (root). Senza questo passo il processo nexus (uid 10001)
# trova il database in sola lettura (sqlite3.OperationalError: attempt
# to write a readonly database).
#
# Questo script gira come root (nessun USER nel Dockerfile), sistema i
# permessi del volume montato, poi lascia il processo applicativo vero
# e proprio a un utente non privilegiato. Si usa `su` (gia' nell'immagine
# base, niente da scaricare a build-time) invece di gosu: `su -c` accetta
# solo una stringa, non un argv array, quindi si passa un argomento fittizio
# come $0 e si ricostruisce l'array con "$@" dentro la shell invocata — è il
# solo modo per preservare l'array di comando (qui: sh -c "uvicorn ...")
# senza perdere il quoting.
set -e

mkdir -p /data
chown -R nexus:nexus /data

exec su -s /bin/sh -c 'exec "$@"' nexus -- dummy "$@"
