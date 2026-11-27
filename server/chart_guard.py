"""CHART-REAL-DATA-V1 - guardia FAIL-CLOSED sulle finestre di dati accessibili al Chart.

Regole (decisione D2 del proprietario, 2026-11-27):
 * si possono mostrare SOLO partizioni esplicitamente classificate e AUTORIZZATE; l'autorizzazione e' un record (`chart_authorization.json`) legato per hash ai manifest canonici;
 * nessuna finestra e' autorizzata "per esclusione" (es. perche' precede il 2026-02-04);
 * le finestre sigillate (`final_holdout_seal_v1.json`), le finestre consumate e la validazione bloccata (`locked_validation`) non sono mai autorizzabili da questo record;
 * qualunque anomalia (file mancante, hash diverso, JSON illeggibile, dataset sconosciuto) = nessun accesso;
 * il controllo avviene a livello di segmento dello store (non solo di API), quindi vale anche per paginazione, aggregazioni multitimeframe, cache e replay;
 * le fonti restano separate: ogni dataset ha la propria voce; l'autorizzazione di un dataset non vale per un altro.

FIX-01 (CRDV1R-01): lo stato della guardia e' DERIVATO dal contenuto dei metadata e rivalidato a ogni uso (hash dei byte letti, non TTL/mtime):
un'istanza longeva non riutilizza mai un'autorizzazione revocata, modificata, sostituita, resa illeggibile o rimossa.

FIX-02 (CRDV1R-01, residuo FIX01R-01): l'AMMISSIONE di una risposta e' una decisione su UN'UNICA revisione dell'autorita'.
 * `Guard.snapshot()` restituisce un `AuthoritySnapshot` IMMUTABILE (revisione = sha256 dei byte dei metadata, finestre, errore): non muta mai, nessun controllo successivo puo' cambiarne l'esito;
 * `Guard.verify_all(...)` e' l'UNICO punto di ammissione: acquisisce uno snapshot S, verifica TUTTI gli intervalli rispetto a S (mai a revisioni diverse), poi rilegge i metadata:
   se la revisione e' ancora S la risposta e' ammessa (punto di linearizzazione = quella rilettura di conferma), altrimenti rivaluta TUTTO su un nuovo snapshot (max `ATTEMPTS`), poi nega (AUTHORITY_UNSTABLE);
 * i `check()` per-segmento prima dell'IO sono solo un rifiuto anticipato: non decidono mai l'ammissione.
Vedi AUTHORIZATION_CONSISTENCY_CONTRACT.md per le garanzie ottenute e le finestre residue.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import threading
from pathlib import Path

AUTH_FILE = Path(__file__).with_name("chart_authorization.json")
DEFAULT_CANON_DIR = Path(__file__).with_name("research_scripts") / "phase7"
CANON_FILES = ("partition_manifest_v1.json", "final_holdout_seal_v1.json", "partition_contract_v2.json")
NEVER_AUTHORIZABLE_SEGMENTS = {"final_holdout", "locked_validation"}


class PartitionDenied(Exception):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(code + (": " + detail if detail else ""))
        self.code, self.detail = code, detail


def _day_start(s: str) -> int:
    return int(_dt.datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=_dt.timezone.utc).timestamp())


def _iso(s: str) -> int:
    return int(_dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())


def _sha(p: Path) -> str:
    # normalizzazione dei fine riga: l'hash non deve dipendere da CRLF/LF (checkout Windows vs immagine Linux)
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


class AuthoritySnapshot:
    """Revisione IMMUTABILE dell'autorita': `revision` = fingerprint dei byte dei metadata da cui sono derivate finestre ed errore."""
    __slots__ = ("revision", "_windows", "error")

    def __init__(self, revision: str, windows: dict, error: str | None):
        object.__setattr__(self, "revision", revision)
        object.__setattr__(self, "_windows", {k: tuple((int(a), int(b)) for a, b in v) for k, v in windows.items()})
        object.__setattr__(self, "error", error)

    def __setattr__(self, name, value):
        raise AttributeError("AuthoritySnapshot e' immutabile")

    def windows(self, dataset_id: str) -> list[tuple[int, int]]:
        return list(self._windows.get(dataset_id, ()))

    def check(self, dataset_id: str, t0: int, t1: int) -> None:
        """Ammesso solo se [t0, t1) e' interamente dentro UNA finestra autorizzata DI QUESTA REVISIONE. Altrimenti PartitionDenied (mai dati)."""
        if self.error:
            raise PartitionDenied("AUTHORIZATION_UNAVAILABLE", self.error)
        wins = self._windows.get(dataset_id)
        if not wins:
            raise PartitionDenied("DATASET_NOT_AUTHORIZED", dataset_id)
        if not any(a <= t0 and t1 <= b for a, b in wins):
            raise PartitionDenied("PARTITION_NOT_AUTHORIZED", "%s [%s,%s)" % (dataset_id, t0, t1))

    def clamp(self, dataset_id: str, t0: int, t1: int) -> tuple[int, int] | None:
        for a, b in self._windows.get(dataset_id, ()):
            lo, hi = max(a, t0), min(b, t1)
            if lo < hi:
                return lo, hi
        return None


class Guard:
    """Autorita' di accesso. Lo stato (finestre/errore) e' derivato dallo SNAPSHOT dei byte dei metadata; la ricostruzione usa gli stessi byte
    da cui e' calcolato il fingerprint (nessuna finestra TOCTOU tra hash e parse). Ogni snapshot e' immutabile."""

    ATTEMPTS = 3          # rivalutazioni complete ammesse se l'autorita' cambia durante la verifica; poi AUTHORITY_UNSTABLE (fail-closed)

    def __init__(self, auth_path: str | Path | None = None, canon_dir: str | Path | None = None):
        self.auth_path = Path(auth_path or os.environ.get("NEXUS_CHART_AUTH_FILE") or AUTH_FILE)
        self.canon_dir = Path(canon_dir or os.environ.get("NEXUS_CHART_PARTITION_DIR") or DEFAULT_CANON_DIR)
        self._lock = threading.Lock()
        self._state: AuthoritySnapshot = AuthoritySnapshot("", {}, "NOT_LOADED")      # ultima revisione costruita (cache di calcolo, MAI autorita': ogni uso rilegge i byte)
        self.reloads = 0
        self._refresh()

    # --------------------------------------------------------------- snapshot e rivalidazione
    def _snapshot(self) -> dict:
        snap: dict = {}
        for key, path in (("auth", self.auth_path),) + tuple((f, self.canon_dir / f) for f in CANON_FILES):
            try:
                snap[key] = path.read_bytes()
            except FileNotFoundError:
                snap[key] = None                                              # assente: stato fingerprintato, fail-closed in _build se serve
            except OSError as ex:
                snap[key] = ("UNREADABLE:" + type(ex).__name__).encode()      # illeggibile != assente: cambia comunque il fingerprint
        return snap

    @staticmethod
    def _fingerprint(snap: dict) -> str:
        h = hashlib.sha256()
        for k in sorted(snap):
            v = snap[k]
            h.update(k.encode() + b"\0" + (b"ABSENT" if v is None else hashlib.sha256(v).digest()) + b"\0")
        return h.hexdigest()

    def _refresh(self) -> AuthoritySnapshot:
        """Snapshot coerente col contenuto dei metadata LETTI ORA: finestre ed errore derivano dagli stessi byte del fingerprint (mai da una revisione diversa).
        La cache `_state` evita solo di ricalcolare il parse; la rilettura dei byte avviene sempre."""
        snap = self._snapshot()
        fp = self._fingerprint(snap)
        st = self._state
        if st.revision == fp:
            return st
        with self._lock:
            st = self._state
            if st.revision == fp:
                return st
            windows, error = self._build(snap)
            new = AuthoritySnapshot(fp, windows, error)
            self._state = new
            self.reloads += 1
            return new                                                    # ritorna lo snapshot dei SUOI byte, anche se un'altra thread ne ha pubblicato uno piu' recente

    def _build(self, snap: dict) -> tuple[dict, str | None]:
        windows: dict[str, list[tuple[int, int]]] = {}
        try:
            raw = snap["auth"]
            if raw is None or raw.startswith(b"UNREADABLE:"):
                raise ValueError("AUTHORIZATION_RECORD_UNAVAILABLE")
            auth = json.loads(raw.decode("utf-8"))
            if not isinstance(auth, dict) or auth.get("schema") != "NEXUS_CHART_AUTHORIZATION_V1" or auth.get("authorized_by") != "owner":
                raise ValueError("AUTHORIZATION_RECORD_INVALID")
            canon_cache: dict | None = None
            for dsid, rule in (auth.get("datasets") or {}).items():
                kind = rule.get("kind")
                if kind == "EXPLICIT_WINDOWS":                       # dataset non soggetto a partizioni di ricerca (es. export XM gia' autorizzato)
                    windows[dsid] = [(_iso(a), _iso(b)) for a, b in rule["windows_utc"]]
                elif kind == "PHASE7_PARTITIONS":
                    if canon_cache is None:
                        canon_cache = self._canonical(auth, snap)
                    wins = []
                    for name in rule["allowed_segment_names"]:
                        if name in NEVER_AUTHORIZABLE_SEGMENTS:
                            raise ValueError("SEGMENT_NEVER_AUTHORIZABLE:" + name)
                        seg = canon_cache["segments"].get(name)
                        if seg is None:
                            raise ValueError("SEGMENT_UNKNOWN:" + name)
                        a, b = _day_start(seg["declared_start"]), _day_start(seg["declared_end"]) + 86400
                        if a < canon_cache["seal_end"] and b > canon_cache["seal_start"]:
                            raise ValueError("SEGMENT_INTERSECTS_SEAL:" + name)
                        wins.append((a, b))
                    windows[dsid] = wins
                else:
                    raise ValueError("RULE_KIND_UNKNOWN:" + str(kind))
        except Exception as ex:                                       # fail-closed: nessuna finestra
            return {}, "%s: %s" % (type(ex).__name__, ex)
        return windows, None

    @staticmethod
    def _canonical(auth: dict, snap: dict) -> dict:
        bound = auth.get("bound_manifests") or {}
        for f in CANON_FILES:
            raw = snap.get(f)
            if raw is None or raw.startswith(b"UNREADABLE:") or bound.get(f) != hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest():
                raise ValueError("CANONICAL_MANIFEST_MISSING_OR_CHANGED:" + f)
        pm = json.loads(snap["partition_manifest_v1.json"].decode("utf-8"))["payload"]
        seal = json.loads(snap["final_holdout_seal_v1.json"].decode("utf-8"))["payload"]
        seal = json.loads(seal) if isinstance(seal, str) else seal
        segs = {s["name"]: s for s in pm["segments"]}
        return {"segments": segs, "seal_start": _day_start(seal["date_range"]["start"]), "seal_end": _day_start(seal["date_range"]["end"]) + 86400}

    # --------------------------------------------------------------- API
    def snapshot(self) -> AuthoritySnapshot:
        """Revisione immutabile dei metadata letti ORA (rilettura dei byte a ogni chiamata)."""
        return self._refresh()

    @property
    def error(self) -> str | None:
        return self._refresh().error

    def windows(self, dataset_id: str) -> list[tuple[int, int]]:
        return self._refresh().windows(dataset_id)

    def check(self, dataset_id: str, t0: int, t1: int) -> None:
        """Rifiuto ANTICIPATO (prima dell'IO) su una revisione appena letta. NON e' la decisione di ammissione della risposta (vedi verify_all)."""
        self._refresh().check(dataset_id, t0, t1)

    def verify_all(self, requests: list[tuple[str, int, int]]) -> AuthoritySnapshot:
        """UNICO punto di ammissione di una risposta: tutti gli intervalli `(dataset, t0, t1)` sono verificati rispetto a UN SOLO snapshot S; poi la revisione
        corrente viene riletta: se e' ancora S la risposta e' ammessa (linearizzazione = rilettura di conferma); se e' cambiata, TUTTO e' rivalutato su un nuovo snapshot
        (mai si combinano esiti di revisioni diverse). Dopo `ATTEMPTS` cambi consecutivi: PartitionDenied(AUTHORITY_UNSTABLE). Qualunque intervallo negato nega l'intera risposta."""
        for _ in range(self.ATTEMPTS):
            s = self._refresh()
            for dsid, t0, t1 in requests:
                s.check(dsid, t0, t1)                    # PartitionDenied => risposta negata nella sua interezza
            if self._refresh().revision == s.revision:
                return s
        raise PartitionDenied("AUTHORITY_UNSTABLE", "autorita' modificata durante la verifica (%d tentativi)" % self.ATTEMPTS)

    def recheck(self, dataset_id: str, ranges: list[tuple[int, int]]) -> None:
        """Compatibilita': verifica atomica (verify_all) di tutti gli intervalli letti, subito prima di restituire i dati."""
        self.verify_all([(dataset_id, t0, t1) for t0, t1 in ranges])

    def clamp(self, dataset_id: str, t0: int, t1: int) -> tuple[int, int] | None:
        """Intersezione con la finestra autorizzata che contiene l'ultimo istante richiesto; None se vuota. Non serve a leggere: serve a dichiarare i limiti disponibili."""
        return self._refresh().clamp(dataset_id, t0, t1)
