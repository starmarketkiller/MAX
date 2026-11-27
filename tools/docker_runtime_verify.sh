#!/usr/bin/env bash
# CHART-ONLY-DEPLOY-READY-01 / GATE 02 - verifica runtime dell'IMMAGINE EFFETTIVA su Linux/Docker (CI o host autorizzato).
#
# NON eseguito nella sessione di sviluppo (nessun Docker locale). Cosa fa: build dell'immagine da server/Dockerfile, avvio con configurazione equivalente a Render
# (cgroup 512 MiB, volume su /data, utente nexus dopo l'entrypoint, health check /api/ready), poi: login, caricamento dello store, lettura/paginazione storica,
# richieste concorrenti, tentativi di modifica dell'autorita' COME UTENTE APPLICATIVO, revoca/ripristino senza redeploy, restart x2, redeploy sullo stesso volume,
# upgrade dal layout storico (tutto nexus), fail-closed (strumento assente / percorso non protetto), misura della memoria (working set vs totale container vs limite cgroup).
# Dati: fixture SINTETICA (tools/make_synthetic_chart_fixture.py) salvo REAL_STORE_DIR/REAL_TRANSFER_MANIFEST/REAL_EXPECTED/REAL_RECORD. Credenziali effimere, mai salvate.
# Uso:  bash tools/docker_runtime_verify.sh        (da qualunque directory; richiede docker, python3, curl, base64, sha256sum)
set -uo pipefail
cd "$(dirname "$0")/.."
OUT="${OUT:-docker_verify_out}"; mkdir -p "$OUT"
IMG="${IMG:-nexus-backend:chartonly}"; NAME="${NAME:-chartverify}"; VOL="${VOL:-chartverify_data}"; VOL2="${VOL}_legacy"; PORT="${PORT:-18001}"
MEM="${MEM:-512m}"; CPUS="${CPUS:-0.5}"
RESULTS="$OUT/results.tsv"; : > "$RESULTS"
export CO_TEST_USER="tester-${RANDOM}@local"
CO_TEST_PASS="$(python3 -c 'import secrets;print(secrets.token_urlsafe(18))')"; export CO_TEST_PASS
BASE="http://127.0.0.1:$PORT"
DS="XM-GOLD-2026-11-16-20"
LIVE_REF="${LIVE_REF:-16eff18b8dd570e780e8bbafba6e7fbc8b88530a}"; LIVE_IMG="${LIVE_IMG:-nexus-backend:live16eff18b}"

rec() { printf '%s\t%s\t%s\n' "$1" "$2" "${3:-}" >> "$RESULTS"; echo "[$2] $1 ${3:-}"; }
ok() { rec "$1" PASS "${2:-}"; }
bad() { rec "$1" FAIL "${2:-}"; }
expect_ok() { local n="$1"; shift; if "$@" >"$OUT/$n.log" 2>&1; then ok "$n"; else bad "$n" "rc=$?"; fi; }
expect_fail() { local n="$1"; shift; if "$@" >"$OUT/$n.log" 2>&1; then bad "$n" "ATTESO FALLIMENTO ma riuscito"; else ok "$n"; fi; }
cleanup() { docker rm -f "$NAME" >/dev/null 2>&1 || true; docker volume rm -f "$VOL" "$VOL2" >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup

# ---------------------------------------------------------------- 1. build e fixture
expect_ok build_image docker build -f server/Dockerfile -t "$IMG" .
docker image inspect --format '{{.Id}}' "$IMG" > "$OUT/image_id.txt" 2>&1
expect_ok entrypoint_and_ctl_root_owned sh -c "docker run --rm --entrypoint sh '$IMG' -c 'test \"\$(stat -c %U:%G /usr/local/sbin/docker-entrypoint.sh)\" = root:root && test \"\$(stat -c %U:%G /usr/local/sbin/chart-authority)\" = root:root && test \"\$(stat -c %a /usr/local/sbin/chart-authority)\" = 755'"

if [ -n "${REAL_STORE_DIR:-}" ]; then
  FIXSTORE="$REAL_STORE_DIR"; TRANSFER="$REAL_TRANSFER_MANIFEST"; EXPECTED="$REAL_EXPECTED"; RECORD="$REAL_RECORD"
else
  python3 tools/make_synthetic_chart_fixture.py "$OUT/fixture" > "$OUT/fixture.log" 2>&1 || bad make_fixture "rc=$?"
  FIXSTORE="$OUT/fixture/store"; TRANSFER="$OUT/fixture/transfer_manifest.json"; EXPECTED="$OUT/fixture/expected.json"; RECORD="$OUT/fixture/authorization_record.json"
fi
TSHA="$(sha256sum "$TRANSFER" | cut -d' ' -f1)"
B64="$(base64 -w0 "$RECORD")"

run_container() {   # configurazione equivalente a Render (limiti cgroup, volume /data, variabili Chart minime)
  docker run -d --name "$NAME" -m "$MEM" --memory-swap "$MEM" --cpus "$CPUS" -p "$PORT:8001" -v "$1:/data" \
    -e NEXUS_ENV=DEV -e NEXUS_COOKIE_SECURE=false -e NEXUS_ADMIN_USER="$CO_TEST_USER" -e NEXUS_ADMIN_PASSWORD="$CO_TEST_PASS" \
    -e NEXUS_DB_PATH=/data/nexus.db -e JARVIS_STATE_DIR=/data/jarvis -e NEXUS_DUKASCOPY_AUTOFETCH=false -e NEXUS_SEED_ON_START=false \
    -e NEXUS_QUEUE_DISPATCHER_ENABLED=false -e NEXUS_LOCAL_OPERATIONS_ENABLED=false -e NEXUS_REVENUE_AUTOMATION_ENABLED=false \
    -e NEXUS_CHART_STORE_ROOT=/data/chart_store -e NEXUS_CHART_AUTH_FILE=/data/chart_auth/chart_authorization.json -e NEXUS_CHART_DEFAULT_SOURCE="$DS" \
    "${@:2}" "${RUN_IMG:-$IMG}"
}
wait_ready() {      # health check del Dockerfile (/api/ready) deve diventare healthy
  local i
  for i in $(seq 1 90); do curl -fsS "$BASE/api/health" >/dev/null 2>&1 && break; sleep 2; done
  for i in $(seq 1 90); do [ "$(docker inspect --format '{{.State.Health.Status}}' "$NAME" 2>/dev/null)" = healthy ] && return 0; sleep 2; done
  return 1
}
http() { python3 tools/docker_runtime_http.py "$BASE" "$EXPECTED" --phase "$1" --out "$OUT/http_$1.json" "${@:2}" >"$OUT/http_$1.log" 2>&1 && ok "http_$1" || bad "http_$1" "vedi http_$1.json"; }
as_app() { docker exec -u nexus "$NAME" "$@"; }
as_root() { docker exec -u 0 "$NAME" "$@"; }

boundary_checks() {   # $1 = etichetta di fase
  local p="$1"
  expect_fail "${p}_app_cannot_append_record"   as_app sh -c 'echo x >> /data/chart_auth/chart_authorization.json'
  expect_fail "${p}_app_cannot_truncate_record" as_app sh -c ': > /data/chart_auth/chart_authorization.json'
  expect_fail "${p}_app_cannot_delete_record"   as_app rm -f /data/chart_auth/chart_authorization.json
  expect_fail "${p}_app_cannot_rename_record"   as_app mv /data/chart_auth/chart_authorization.json /data/chart_auth/x
  expect_fail "${p}_app_cannot_chmod_record"    as_app chmod 666 /data/chart_auth/chart_authorization.json
  expect_fail "${p}_app_cannot_create_in_auth_dir" as_app touch /data/chart_auth/new
  expect_fail "${p}_app_cannot_symlink_in_auth_dir" as_app ln -s /etc/passwd /data/chart_auth/l
  expect_fail "${p}_app_cannot_rename_auth_dir" as_app mv /data/chart_auth /data/chart_auth.moved
  expect_fail "${p}_app_cannot_remove_auth_dir" as_app rm -rf /data/chart_auth
  expect_fail "${p}_app_cannot_write_store_manifest" as_app sh -c "echo x > /data/chart_store/$DS/manifest.json"
  expect_fail "${p}_app_cannot_remove_store" as_app rm -rf /data/chart_store
  expect_fail "${p}_app_cannot_run_operator_tool" as_app /usr/local/sbin/chart-authority revoke
  expect_ok   "${p}_app_can_read_record"        as_app cat /data/chart_auth/chart_authorization.json
  expect_ok   "${p}_app_can_write_own_files_in_data" as_app sh -c 'touch /data/nexus_probe && rm /data/nexus_probe'
  expect_ok   "${p}_app_can_write_database"     as_app python -c "import sqlite3;c=sqlite3.connect('/data/nexus.db');c.execute('create table if not exists _verify(x)');c.execute('insert into _verify values (1)');c.commit()"
  docker exec "$NAME" stat -c '%U:%G %a %F %n' /data /data/chart_auth /data/chart_auth/chart_authorization.json /data/chart_store "/data/chart_store/$DS/manifest.json" > "$OUT/${p}_perms.txt" 2>&1
  grep -q '^root:nexus 1770 directory /data$' "$OUT/${p}_perms.txt" && ok "${p}_perm_data_root_nexus_1770" || bad "${p}_perm_data_root_nexus_1770" "$(head -1 "$OUT/${p}_perms.txt")"
  grep -q '^root:root 755 directory /data/chart_auth$' "$OUT/${p}_perms.txt" && ok "${p}_perm_auth_dir" || bad "${p}_perm_auth_dir"
  grep -q '^root:root 644 regular file /data/chart_auth/chart_authorization.json$' "$OUT/${p}_perms.txt" && ok "${p}_perm_record" || bad "${p}_perm_record"
  grep -q '^root:root 755 directory /data/chart_store$' "$OUT/${p}_perms.txt" && ok "${p}_perm_store_dir" || bad "${p}_perm_store_dir"
  expect_ok "${p}_ctl_verify_root" as_root /usr/local/sbin/chart-authority verify
  expect_ok "${p}_ctl_status_root" as_root /usr/local/sbin/chart-authority status
}

memory_sample() {   # $1 = etichetta. working set (docker stats: current - inactive_file) != totale container (memory.current, include page cache) != limite cgroup
  local p="$1"
  {
    echo "== cgroup =="; as_root sh -c 'for f in memory.max memory.current memory.peak memory.events; do echo "$f: $(cat /sys/fs/cgroup/$f 2>/dev/null)"; done; grep -E "^(anon|file|inactive_file|active_file|kernel|slab) " /sys/fs/cgroup/memory.stat 2>/dev/null; for f in memory.limit_in_bytes memory.usage_in_bytes memory.max_usage_in_bytes; do echo "v1 $f: $(cat /sys/fs/cgroup/memory/$f 2>/dev/null)"; done'
    echo "== processi (VmRSS/VmHWM) =="; as_root sh -c 'for d in /proc/[0-9]*; do c=$(tr "\0" " " < $d/cmdline 2>/dev/null | cut -c1-60); case "$c" in *uvicorn*|*python*) echo "$c"; grep -E "VmRSS|VmHWM" $d/status;; esac; done'
    echo "== docker stats =="; docker stats --no-stream --format '{{json .}}' "$NAME"
    echo "== OOM =="; docker inspect --format 'OOMKilled={{.State.OOMKilled}} RestartCount={{.RestartCount}} MemoryLimit={{.HostConfig.Memory}}' "$NAME"
  } > "$OUT/memory_$p.txt" 2>&1
  python3 - "$OUT/memory_$p.txt" "$p" "$OUT" <<'PY'
import json, re, sys
t = open(sys.argv[1]).read()
def num(k):
    m = re.search(r"^%s: (\d+)" % k, t, re.M)
    return int(m.group(1)) if m else None
lim = num("memory.max") or num("v1 memory.limit_in_bytes")
cur = num("memory.current") or num("v1 memory.usage_in_bytes")
peak = num("memory.peak") or num("v1 memory.max_usage_in_bytes")
m = re.search(r"^inactive_file (\d+)", t, re.M)
inactive = int(m.group(1)) if m else 0
ws = (cur - inactive) if cur is not None else None
hwm = [int(x) for x in re.findall(r"VmHWM:\s+(\d+) kB", t)]
oom = "OOMKilled=true" in t
r = {"phase": sys.argv[2], "cgroup_limit_bytes": lim, "container_total_current_bytes": cur, "container_peak_bytes": peak, "working_set_bytes(current-inactive_file)": ws,
     "process_VmHWM_kB_max": max(hwm) if hwm else None, "oom_killed": oom,
     "verdict": "PASS" if (lim and ws is not None and not oom and ws < 0.85 * lim and (peak is None or peak < lim)) else "FAIL"}
json.dump(r, open("%s/memory_%s.json" % (sys.argv[3], sys.argv[2]), "w"), indent=1)
print(json.dumps(r))
PY
  [ "$(python3 -c "import json;print(json.load(open('$OUT/memory_$p.json'))['verdict'])" 2>/dev/null)" = PASS ] && ok "memory_$p" || bad "memory_$p" "vedi memory_$p.json"
}

# ---------------------------------------------------------------- 2. SCENARIO A: volume Render appena montato (root:root), record da CHART_AUTHORITY_B64
docker volume create "$VOL" >/dev/null
docker run --rm -v "$VOL:/data" --entrypoint sh "$IMG" -c 'chown root:root /data && chmod 755 /data' >/dev/null 2>&1
run_container "$VOL" -e CHART_AUTHORITY_B64="$B64" > "$OUT/container_id.txt" 2>&1
wait_ready && ok A_container_healthy_ready_endpoint || bad A_container_healthy_ready_endpoint
docker logs "$NAME" > "$OUT/A_boot_logs.txt" 2>&1
grep -q 'KERNEL_PROBE' "$OUT/A_boot_logs.txt" && bad A_boot_kernel_probe "violazione nel boot" || ok A_boot_kernel_probe
docker exec "$NAME" id nexus > "$OUT/A_id_nexus.txt" 2>&1
as_root rm -rf /tmp/inbox; docker cp "$FIXSTORE/." "$NAME:/tmp/inbox" >/dev/null 2>&1; docker cp "$TRANSFER" "$NAME:/tmp/transfer_manifest.json" >/dev/null 2>&1
expect_ok A_install_store as_root /usr/local/sbin/chart-authority install-store --from /tmp/inbox --manifest /tmp/transfer_manifest.json --manifest-sha256 "$TSHA"
docker cp "$RECORD" "$NAME:/tmp/record.json" >/dev/null 2>&1
http A_authorized
boundary_checks A
memory_sample A_after_load

# revoca / ripristino senza redeploy (operatore root)
expect_ok A_revoke_as_root as_root /usr/local/sbin/chart-authority revoke
http A_revoked --expect-denied
expect_ok A_publish_as_root as_root /usr/local/sbin/chart-authority publish --file /tmp/record.json
http A_restored
expect_fail A_publish_invalid_record_rejected as_root sh -c 'echo "{broken" > /tmp/bad.json && /usr/local/sbin/chart-authority publish --file /tmp/bad.json'

# ---------------------------------------------------------------- 3. restart x2 e redeploy sullo stesso volume (nessun B64: il record persistente deve sopravvivere)
for i in 1 2; do
  docker restart "$NAME" >/dev/null 2>&1
  wait_ready && ok "R${i}_healthy_after_restart" || bad "R${i}_healthy_after_restart"
  http "R${i}_after_restart"
  boundary_checks "R${i}"
done
as_app python -c "import sqlite3;print(sqlite3.connect('/data/nexus.db').execute('select count(*) from _verify').fetchone())" > "$OUT/R_sentinel.txt" 2>&1 && ok R_database_sentinel_persisted || bad R_database_sentinel_persisted
docker rm -f "$NAME" >/dev/null 2>&1
run_container "$VOL" > "$OUT/container_id_redeploy.txt" 2>&1
wait_ready && ok D_healthy_after_redeploy || bad D_healthy_after_redeploy
http D_after_redeploy
boundary_checks D
memory_sample D_after_redeploy
docker rm -f "$NAME" >/dev/null 2>&1

# ---------------------------------------------------------------- 3b. ROLLBACK in ambiente isolato: immagine LIVE (16eff18b) sullo STESSO volume, poi roll-forward
if git worktree add --detach "$OUT/live_src" "$LIVE_REF" >"$OUT/live_worktree.log" 2>&1; then
  ok RB_live_ref_checked_out "$LIVE_REF"
  expect_ok RB_build_live_image docker build -f "$OUT/live_src/server/Dockerfile" -t "$LIVE_IMG" "$OUT/live_src"
  docker image inspect --format '{{.Id}}' "$LIVE_IMG" > "$OUT/live_image_id.txt" 2>&1
  RUN_IMG="$LIVE_IMG" run_container "$VOL" > "$OUT/container_id_rollback.txt" 2>&1
  wait_ready && ok RB_live_image_healthy_on_new_layout_volume || bad RB_live_image_healthy_on_new_layout_volume
  expect_ok RB_db_sentinel_readable_and_writable_by_live_code docker exec -u nexus "$NAME" python -c "import sqlite3;c=sqlite3.connect('/data/nexus.db');assert c.execute('select count(*) from _verify').fetchone()[0]>=1;c.execute('insert into _verify values (2)');c.commit()"
  python3 - "$BASE" "$CO_TEST_USER" "$CO_TEST_PASS" > "$OUT/RB_live_api.json" 2>&1 <<'PY' && ok RB_live_login_and_old_chart_endpoint || bad RB_live_login_and_old_chart_endpoint "vedi RB_live_api.json"
import json, sys, urllib.request
base, u, p = sys.argv[1:4]
def call(path, tok=None, body=None):
    h = {"Content-Type": "application/json"}
    if tok: h["Authorization"] = "Bearer " + tok
    r = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None, headers=h, method="POST" if body is not None else "GET")
    with urllib.request.urlopen(r, timeout=60) as resp: return json.loads(resp.read())
tok = call("/api/auth/login", body={"email": u, "password": p})["token"]
j = call("/api/chart/ohlc?symbol=XAUUSD&tf=M15&limit=3", tok)
print(json.dumps({"source": j.get("source"), "bars": len(j.get("bars", []))}))
assert j.get("source") == "SYNTHETIC_DATA" and len(j.get("bars", [])) == 3      # comportamento precedente della live: ritorno effettivo al codice vecchio
PY
  docker exec "$NAME" stat -c '%U:%G %a %n' /data /data/chart_auth /data/chart_auth/chart_authorization.json /data/chart_store > "$OUT/RB_perms_after_legacy_entrypoint.txt" 2>&1
  expect_ok RB_chart_data_preserved_after_rollback docker exec "$NAME" sh -c "test -f /data/chart_store/$DS/manifest.json && test -f /data/chart_auth/chart_authorization.json"
  docker rm -f "$NAME" >/dev/null 2>&1
  # roll-forward: il boot trova i namespace ceduti a nexus dall'entrypoint storico => quarantena del record + DENY-ALL; poi pubblicazione operatore
  run_container "$VOL" > "$OUT/container_id_rollforward.txt" 2>&1
  wait_ready && ok RB_rollforward_healthy || bad RB_rollforward_healthy
  docker exec "$NAME" ls -la /data/chart_auth > "$OUT/RB_rollforward_auth_dir.txt" 2>&1
  grep -q 'untrusted-' "$OUT/RB_rollforward_auth_dir.txt" && ok RB_rollforward_quarantines_app_owned_record || bad RB_rollforward_quarantines_app_owned_record
  http RB_rollforward_denied_until_operator_publishes --expect-denied
  docker cp "$RECORD" "$NAME:/tmp/record.json" >/dev/null 2>&1
  expect_ok RB_rollforward_publish_as_root as_root /usr/local/sbin/chart-authority publish --file /tmp/record.json
  http RB_rollforward_authorized
  boundary_checks RB
  docker rm -f "$NAME" >/dev/null 2>&1
else
  bad RB_live_ref_checked_out "git worktree add fallito (serve fetch-depth: 0)"
fi

# ---------------------------------------------------------------- 4. SCENARIO B: upgrade dal layout storico (tutto nexus, record modificabile dall'app)
docker volume create "$VOL2" >/dev/null
docker run --rm -v "$VOL2:/data" -v "$PWD/$RECORD:/rec.json:ro" --entrypoint sh "$IMG" -c 'mkdir -p /data/chart_auth /data/chart_store && cp /rec.json /data/chart_auth/chart_authorization.json && chown -R nexus:nexus /data' >/dev/null 2>&1
run_container "$VOL2" > "$OUT/container_id_legacy.txt" 2>&1
wait_ready && ok B_healthy_after_legacy_upgrade || bad B_healthy_after_legacy_upgrade
docker exec "$NAME" ls -la /data/chart_auth > "$OUT/B_auth_dir.txt" 2>&1
grep -q 'untrusted-' "$OUT/B_auth_dir.txt" && ok B_app_modifiable_record_quarantined || bad B_app_modifiable_record_quarantined
as_root rm -rf /tmp/inbox; docker cp "$FIXSTORE/." "$NAME:/tmp/inbox" >/dev/null 2>&1; docker cp "$TRANSFER" "$NAME:/tmp/transfer_manifest.json" >/dev/null 2>&1
expect_ok B_install_store as_root /usr/local/sbin/chart-authority install-store --from /tmp/inbox --manifest /tmp/transfer_manifest.json --manifest-sha256 "$TSHA"
http B_legacy_record_is_not_authority --expect-denied     # lo store e' presente: l'unica causa del diniego e' l'autorita' (DENY-ALL dopo la quarantena)
docker rm -f "$NAME" >/dev/null 2>&1

# ---------------------------------------------------------------- 5. fail-closed: strumento assente / percorso non protetto (il backend deve partire, il Chart nega)
run_container "$VOL" -e CHART_AUTHORITY_CTL=/nonexistent > "$OUT/container_id_noctl.txt" 2>&1
wait_ready && ok F1_backend_healthy_without_ctl || bad F1_backend_healthy_without_ctl
http F1_ctl_missing_chart_denied --expect-denied
docker rm -f "$NAME" >/dev/null 2>&1
docker rm -f "$NAME" >/dev/null 2>&1
run_container "$VOL" -e NEXUS_CHART_AUTH_FILE=/data/a/b/c.json > "$OUT/container_id_badpath.txt" 2>&1
wait_ready && ok F2_backend_healthy_with_unprotectable_path || bad F2_backend_healthy_with_unprotectable_path
http F2_unprotectable_path_chart_denied --expect-denied
docker rm -f "$NAME" >/dev/null 2>&1

# ---------------------------------------------------------------- riepilogo
python3 - "$RESULTS" "$OUT" <<'PY'
import json, sys
rows = [l.rstrip("\n").split("\t") for l in open(sys.argv[1])]
s = {"total": len(rows), "pass": sum(r[1] == "PASS" for r in rows), "fail": sum(r[1] == "FAIL" for r in rows), "failed": [r[0] for r in rows if r[1] == "FAIL"]}
json.dump(s, open(sys.argv[2] + "/summary.json", "w"), indent=1)
print(json.dumps(s))
sys.exit(1 if s["fail"] else 0)
PY
