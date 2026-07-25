"""Retention per classe di dato e backup verificabile.

Copre:

* AUD0-DB-013 / NXS-DB-013 — nessuna politica di retention: shadow trade,
  notifiche, sessioni Coach, eventi di comando e storico equity crescevano
  senza limite, e cancellarli a mano avrebbe distrutto evidenza di audit.
* AUD0-DB-014 / NXS-DB-014 — persistenza ≠ backup: nessuna procedura di
  copia consistente, nessun test di ripristino.
* AUD0-DB-016 — policy di durabilità incompleta.

Il modulo è puro rispetto a FastAPI: riceve una connection factory.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional


@dataclass(frozen=True)
class RetentionRule:
    """Regola di conservazione per una classe di dato.

    `protected=True` marca le classi che NON possono essere potate
    automaticamente: sono evidenza di audit e la loro rimozione deve essere
    una decisione esplicita, non un effetto collaterale della manutenzione.
    """

    table: str
    timestamp_column: str
    days: int
    description: str
    protected: bool = False


#: Le durate sono deliberatamente generose: lo scopo è mettere un tetto alla
#: crescita, non ridurre la finestra di indagine.
RETENTION_RULES = (
    RetentionRule("shadow_trades", "created_at", 90,
                  "trade ombra: ricerca, non evidenza operativa"),
    RetentionRule("notifications", "created_at", 90,
                  "notifiche consegnate"),
    RetentionRule("coach_notifications", "created_at", 90,
                  "notifiche del Coach"),
    RetentionRule("command_events", "created_at", 365,
                  "transizioni dei comandi bridge"),
    RetentionRule("visual_objects", "updated_at", 30,
                  "oggetti grafici: proiezione rigenerabile"),
    RetentionRule("compute_jobs", "finished_at", 60,
                  "job computazionali conclusi"),
    # Protette: non vengono mai potate automaticamente.
    RetentionRule("trade_events", "created_at", 3650,
                  "ledger dei trade: evidenza primaria", protected=True),
    RetentionRule("operator_audit", "created_at", 3650,
                  "audit delle azioni privilegiate", protected=True),
    RetentionRule("license_events", "created_at", 3650,
                  "ciclo di vita delle licenze", protected=True),
    RetentionRule("trades", "synced_at", 3650,
                  "storico trade", protected=True),
)


def _table_exists(c: sqlite3.Connection, table: str) -> bool:
    row = c.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return bool(row)


def retention_report(connect: Callable[[], sqlite3.Connection]) -> list[dict]:
    """Quante righe verrebbero potate, senza cancellare nulla."""
    out = []
    now = time.time()
    with connect() as c:
        for rule in RETENTION_RULES:
            if not _table_exists(c, rule.table):
                continue
            cutoff = now - rule.days * 86400
            try:
                total = c.execute(f"SELECT COUNT(*) FROM {rule.table}").fetchone()[0]
                stale = c.execute(
                    f"SELECT COUNT(*) FROM {rule.table} "
                    f"WHERE {rule.timestamp_column} IS NOT NULL "
                    f"AND {rule.timestamp_column} < ?", (cutoff,)).fetchone()[0]
            except sqlite3.Error:
                continue
            out.append({
                "table": rule.table,
                "description": rule.description,
                "retention_days": rule.days,
                "protected": rule.protected,
                "rows_total": total,
                "rows_beyond_retention": stale,
                "would_delete": 0 if rule.protected else stale,
            })
    return out


def apply_retention(connect: Callable[[], sqlite3.Connection],
                    *, dry_run: bool = True) -> dict:
    """Applica le regole di retention alle sole classi non protette."""
    deleted: dict[str, int] = {}
    skipped: list[str] = []
    now = time.time()
    with connect() as c:
        for rule in RETENTION_RULES:
            if rule.protected:
                skipped.append(rule.table)
                continue
            if not _table_exists(c, rule.table):
                continue
            cutoff = now - rule.days * 86400
            if dry_run:
                try:
                    n = c.execute(
                        f"SELECT COUNT(*) FROM {rule.table} "
                        f"WHERE {rule.timestamp_column} IS NOT NULL "
                        f"AND {rule.timestamp_column} < ?", (cutoff,)).fetchone()[0]
                except sqlite3.Error:
                    continue
            else:
                try:
                    cur = c.execute(
                        f"DELETE FROM {rule.table} "
                        f"WHERE {rule.timestamp_column} IS NOT NULL "
                        f"AND {rule.timestamp_column} < ?", (cutoff,))
                    n = cur.rowcount or 0
                except sqlite3.Error:
                    continue
            if n:
                deleted[rule.table] = n
    return {"dry_run": dry_run, "deleted": deleted,
            "protected_skipped": skipped}


# --------------------------------------------------------------------------- #
# Backup — AUD0-DB-014
# --------------------------------------------------------------------------- #
def backup_database(db_path: str, target_dir: str) -> dict:
    """Copia consistente del database SQLite, con digest.

    Usa l'API `backup` di SQLite invece di copiare il file: con WAL attivo una
    copia con `cp` può catturare uno stato incoerente (il finding
    AUD0-DB-016 segnalava proprio l'assenza di coordinamento col WAL).
    """
    source = Path(db_path)
    if not source.exists():
        raise FileNotFoundError(f"database non trovato: {db_path}")

    target_root = Path(target_dir)
    target_root.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    target = target_root / f"nexus-{stamp}.db"

    src = sqlite3.connect(str(source))
    try:
        dst = sqlite3.connect(str(target))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()

    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    return {
        "path": str(target),
        "size_bytes": target.stat().st_size,
        "sha256": digest,
        "created_at": stamp,
        # Un backup non è valido finché non è stato ripristinato con successo.
        "verified": False,
    }


def verify_backup(backup_path: str) -> dict:
    """Verifica un backup aprendolo e controllandone l'integrità.

    AUD0-DB-014: "un backup non testato non è un backup". Qui si esegue un
    `PRAGMA integrity_check` reale e si contano le righe delle tabelle di
    evidenza, così la verifica dice qualcosa di sostanziale.
    """
    path = Path(backup_path)
    if not path.exists():
        raise FileNotFoundError(f"backup non trovato: {backup_path}")

    conn = sqlite3.connect(str(path))
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        counts = {}
        for table in ("trades", "trade_events", "operator_audit", "licenses", "kv"):
            try:
                counts[table] = conn.execute(
                    f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            except sqlite3.Error:
                counts[table] = None
        migrations = []
        try:
            migrations = [r[0] for r in conn.execute(
                "SELECT migration_id FROM schema_migrations ORDER BY migration_id")]
        except sqlite3.Error:
            pass
    finally:
        conn.close()

    ok = integrity == "ok"
    return {
        "path": str(path),
        "integrity_check": integrity,
        "ok": ok,
        "row_counts": counts,
        "migrations": migrations,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def restore_drill(db_path: str, work_dir: str) -> dict:
    """Esegue un giro completo backup → verifica → conteggio.

    È il "restore drill" che l'audit chiede come prova che il backup serva a
    qualcosa. Non tocca il database di produzione: ripristina in una
    directory di lavoro e confronta.
    """
    created = backup_database(db_path, work_dir)
    verified = verify_backup(created["path"])

    source_counts = {}
    conn = sqlite3.connect(db_path)
    try:
        for table in verified["row_counts"]:
            try:
                source_counts[table] = conn.execute(
                    f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            except sqlite3.Error:
                source_counts[table] = None
    finally:
        conn.close()

    mismatches = {t: {"source": source_counts.get(t), "backup": v}
                  for t, v in verified["row_counts"].items()
                  if source_counts.get(t) != v}

    return {
        "backup": created,
        "verification": verified,
        "source_row_counts": source_counts,
        "mismatches": mismatches,
        # Il drill riesce solo se l'integrità passa E i conteggi combaciano.
        "drill_passed": bool(verified["ok"] and not mismatches),
    }


def cleanup_old_backups(target_dir: str, keep: int = 7) -> list[str]:
    """Conserva gli ultimi N backup, elimina i precedenti."""
    root = Path(target_dir)
    if not root.exists():
        return []
    backups = sorted(root.glob("nexus-*.db"), key=lambda p: p.stat().st_mtime,
                     reverse=True)
    removed = []
    for old in backups[keep:]:
        try:
            os.remove(old)
            removed.append(str(old))
        except OSError:
            continue
    return removed
