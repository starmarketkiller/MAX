#!/bin/bash
# SessionStart hook — avvisa in automatico se altri agenti/sessioni hanno
# pushato commit che questa copia locale non ha ancora, cosi' nessuno deve
# ricordarsi di dirlo a voce. Vedi vault/01-Trading/TODO per il contesto
# (piu' agenti lavorano su questo repo: uno su MT5/vault, uno sul frontend).
set -euo pipefail

echo '{"async": false}'

cd "${CLAUDE_PROJECT_DIR:-.}"

if ! git rev-parse --git-dir > /dev/null 2>&1; then
  exit 0
fi

# Non bloccare mai l'avvio sessione per un problema di rete.
git fetch --all --quiet 2>/dev/null || { echo "[session-start] git fetch fallito (rete?), salto il controllo aggiornamenti."; exit 0; }

CUR_BRANCH="$(git branch --show-current 2>/dev/null || echo "(detached)")"
echo "=== Controllo aggiornamenti remoti (branch locale: $CUR_BRANCH) ==="

CHECKED_ANY=0
FOUND_DIVERGENCE=0
for ref in origin/main "origin/$CUR_BRANCH"; do
  git show-ref --verify --quiet "refs/remotes/$ref" || continue
  [ "$ref" = "origin/$CUR_BRANCH" ] && [ "$CUR_BRANCH" = "main" ] && continue
  CHECKED_ANY=1

  BEHIND="$(git rev-list --count "HEAD..$ref" 2>/dev/null || echo 0)"
  if [ "$BEHIND" != "0" ]; then
    FOUND_DIVERGENCE=1
    echo ""
    echo "⚠️  $ref ha $BEHIND commit che questa copia NON ha:"
    git log --oneline "HEAD..$ref" | head -10

    # File toccati altrove che questa sessione ha modificato anche in locale
    # (working tree sporco) o nei propri commit non ancora pushati -> segnale
    # di rischio di conflitto/duplicazione, non solo "sei indietro".
    REMOTE_FILES="$(git diff --name-only "HEAD...$ref" 2>/dev/null | sort -u)"
    LOCAL_UNPUSHED_FILES=""
    UPSTREAM="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
    if [ -n "$UPSTREAM" ]; then
      LOCAL_UNPUSHED_FILES="$(git diff --name-only "$UPSTREAM...HEAD" 2>/dev/null | sort -u)"
    fi
    if [ -n "$LOCAL_UNPUSHED_FILES" ]; then
      OVERLAP="$(comm -12 <(echo "$REMOTE_FILES") <(echo "$LOCAL_UNPUSHED_FILES") 2>/dev/null || true)"
      if [ -n "$OVERLAP" ]; then
        echo "   File modificati SIA qui che su $ref (rischio conflitto/duplicazione):"
        echo "$OVERLAP" | sed 's/^/     - /'
      fi
    fi
  fi
done

if [ "$CHECKED_ANY" = "0" ]; then
  echo "(nessun branch remoto di confronto trovato)"
elif [ "$FOUND_DIVERGENCE" = "0" ]; then
  echo "Nessun commit nuovo altrove — copia locale allineata."
fi

echo "=== Fine controllo ==="
