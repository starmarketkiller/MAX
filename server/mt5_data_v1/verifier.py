"""MT5_RUN_AND_ACCOUNT_DATA_CONTRACT_V1 - verifier di qualita' dati (sez.18).

Controlla un bundle normalizzato (output di normalize.py: deals +
trade_episodes) e produce un oggetto conforme a
contracts/mt5-account-manifest-v1.schema.json#/definitions (data_quality).
Non modifica mai i dati - solo li giudica. Un fallimento qui non blocca la
normalizzazione (che e' gia' avvenuta), ma deve bloccare/segnalare l'uso di
quei dati nei report (sez.18: "nessun report deve nascondere un fallimento
di qualita'").
"""
from __future__ import annotations

from typing import List, Optional

from . import canonical


def _fail(check: str, detail: str, affected_ids: Optional[list] = None) -> dict:
    return {"check": check, "detail": detail, "affected_ids": affected_ids or []}


def verify_bundle(bundle: dict, expected_account_id: str, raw_path: Optional[str] = None) -> dict:
    checks_passed: List[str] = []
    checks_failed: List[dict] = []

    deals = bundle.get("deals", [])
    episodes = bundle.get("trade_episodes", [])

    # 1. hash di provenance coerente col file raw effettivamente sul disco
    if raw_path is not None:
        prov = bundle.get("provenance", {})
        recorded_sha = prov.get("raw_source_sha256")
        actual_sha = canonical.file_sha256(raw_path)
        if recorded_sha and recorded_sha != actual_sha:
            checks_failed.append(_fail(
                "raw_hash_matches_disk",
                f"provenance.raw_source_sha256={recorded_sha} ma il file su disco ha sha256={actual_sha} "
                f"(il file raw e' stato modificato dopo la normalizzazione - mai permesso)."
            ))
        else:
            checks_passed.append("raw_hash_matches_disk")

    # 2. duplicate deal ids
    seen = {}
    dup_ids = []
    for d in deals:
        t = d.get("deal_ticket")
        if t in seen:
            dup_ids.append(t)
        seen[t] = True
    if dup_ids:
        checks_failed.append(_fail("no_duplicate_deal_ids",
                                   f"{len(dup_ids)} deal_ticket duplicati nel file normalizzato.", dup_ids))
    else:
        checks_passed.append("no_duplicate_deal_ids")

    # 3. negative volume
    neg_vol_deals = [d["deal_ticket"] for d in deals if (d.get("volume") or 0) < 0]
    neg_vol_eps = [e["episode_id"] for e in episodes
                   if (e.get("volume_opened") or 0) < 0 or (e.get("volume_closed") or 0) < 0]
    if neg_vol_deals or neg_vol_eps:
        checks_failed.append(_fail("no_negative_volume",
                                   "volume negativo trovato su deal o trade episode.",
                                   neg_vol_deals + neg_vol_eps))
    else:
        checks_passed.append("no_negative_volume")

    # 4. chronology: close_time >= open_time, exit_before_entry
    bad_chrono = []
    for e in episodes:
        ot, ct = e.get("open_time"), e.get("close_time")
        if ot and ct and ct < ot:
            bad_chrono.append(e["episode_id"])
    if bad_chrono:
        checks_failed.append(_fail("exit_not_before_entry",
                                   f"{len(bad_chrono)} trade episode con close_time < open_time.", bad_chrono))
    else:
        checks_passed.append("exit_not_before_entry")

    # 5. account_id coerenza
    mismatched = set()
    for d in deals:
        if d.get("account_id") != expected_account_id:
            mismatched.add(d.get("account_id"))
    for e in episodes:
        if e.get("account_id") != expected_account_id:
            mismatched.add(e.get("account_id"))
    if mismatched:
        checks_failed.append(_fail("account_id_matches_expected",
                                   f"trovati account_id {sorted(mismatched)} diversi dall'atteso {expected_account_id}.",
                                   sorted(mismatched)))
    else:
        checks_passed.append("account_id_matches_expected")

    # 6. missing required timestamps
    missing_ts_deals = [d["deal_ticket"] for d in deals if not d.get("time")]
    if missing_ts_deals:
        checks_failed.append(_fail("no_missing_timestamps",
                                   f"{len(missing_ts_deals)} deal senza timestamp.", missing_ts_deals))
    else:
        checks_passed.append("no_missing_timestamps")

    # 7. ambiguous episode pairing (EA_TRADE_LOG heuristic) - segnalato, non bloccante come failure
    # ma elencato esplicitamente cosi' non resta silenzioso.
    ambiguous = [e["episode_id"] for e in episodes
                if e.get("provenance", {}).get("pairing_method") == "AMBIGUOUS_FIFO_MULTIPLE_OPEN_PENDING"]
    if ambiguous:
        checks_failed.append(_fail("no_ambiguous_fifo_pairing",
                                   f"{len(ambiguous)} trade episode con pairing FIFO ambiguo "
                                   f"(piu' OPEN della stessa strategia senza CLOSE intermedia) - "
                                   f"open_time/avg_open_price potrebbero essere accoppiati alla posizione sbagliata.",
                                   ambiguous))
    else:
        checks_passed.append("no_ambiguous_fifo_pairing")

    status = "CLEAN" if not checks_failed else "FAILED" if len(checks_failed) > 2 else "WARNINGS"
    return {
        "last_verified_at": canonical.utc_now_iso(),
        "status": status,
        "checks_passed": checks_passed,
        "checks_failed": checks_failed,
    }
