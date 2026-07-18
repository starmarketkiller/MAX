"""Backtest Analyst — primo modulo OpenAI di NEXUS.

Riceve un report/statistiche di backtest MT5 e restituisce un'analisi
strutturata: sintesi, punti di forza, rischi, anomalie, raccomandazioni e
livello di confidenza.

Completamente separato dall'AI Coach (Claude/ANTHROPIC_API_KEY): usa
OPENAI_API_KEY e NEXUS_OPENAI_MODEL. Se la chiave manca, ogni chiamata
ritorna un errore controllato (mai un'eccezione che blocchi il backend) e
la chiave non viene mai loggata ne' inclusa in nessuna risposta.
"""
from __future__ import annotations

import json
import os

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("NEXUS_OPENAI_MODEL", "gpt-4o-mini")

# Campi che l'analisi deve sempre contenere (contratto dell'endpoint).
RESULT_FIELDS = ("sintesi", "punti_di_forza", "rischi", "anomalie",
                 "raccomandazioni", "confidenza")

_SYSTEM_PROMPT = (
    "Sei il Backtest Analyst del sistema NEXUS EA (Expert Advisor MetaTrader 5 "
    "multi-strategia su XAUUSD). Ricevi report o statistiche di backtest MT5 "
    "(profit factor, win rate, drawdown, numero trade, distribuzione per "
    "strategia/periodo, ecc.) e produci un'analisi critica e onesta.\n"
    "Rispondi SOLO con un oggetto JSON con esattamente queste chiavi:\n"
    '  "sintesi": stringa (2-4 frasi, il quadro complessivo);\n'
    '  "punti_di_forza": array di stringhe;\n'
    '  "rischi": array di stringhe;\n'
    '  "anomalie": array di stringhe (dati sospetti, incoerenze, possibili '
    "bug di misura - se non ne vedi, array vuoto);\n"
    '  "raccomandazioni": array di stringhe (azioni concrete, ordinate per '
    "priorita');\n"
    '  "confidenza": numero 0-100 (quanto ti fidi della TUA analisi dato il '
    "campione/qualita' dei dati ricevuti).\n"
    "Non inventare dati non presenti nel report. Se il campione e' piccolo o "
    "il report e' ambiguo, dillo nei rischi e abbassa la confidenza."
)


def is_configured() -> bool:
    """True se la chiave OpenAI e' presente. Non espone mai il valore."""
    return bool(OPENAI_API_KEY)


def diagnostics() -> dict:
    """Stato di configurazione senza segreti (stesso pattern di coach_configured)."""
    return {
        "openai_configured": is_configured(),
        "openai_model": OPENAI_MODEL,
        "sdk_available": _sdk_available(),
    }


def _sdk_available() -> bool:
    try:
        import openai  # noqa: F401
        return True
    except ImportError:
        return False


def analyze(report, question: str | None = None, max_tokens: int = 1500):
    """Analizza un report di backtest. Ritorna (dict_analisi, errore).

    `report` puo' essere una stringa (testo/CSV del report) o un dict/list
    (statistiche gia' strutturate). Errori sempre controllati: (None, msg).
    """
    if not OPENAI_API_KEY:
        return None, ("OPENAI_API_KEY non configurata sul backend "
                      "(impostala su Render).")
    if not _sdk_available():
        return None, ("Pacchetto 'openai' non installato sul backend "
                      "(aggiungilo ai requirements e rideploya).")
    if report is None or (isinstance(report, str) and not report.strip()):
        return None, "Nessun report fornito: passa 'report' (testo o JSON)."

    if isinstance(report, (dict, list)):
        report_text = json.dumps(report, ensure_ascii=False, default=str)
    else:
        report_text = str(report)
    # Cap difensivo: i report MT5 possono essere enormi, il modello non ha
    # bisogno di piu' di cosi' per un'analisi di sintesi.
    report_text = report_text[:60000]

    user_msg = f"Report/statistiche backtest MT5:\n\n{report_text}"
    if question and str(question).strip():
        user_msg += f"\n\nDomanda specifica dell'utente: {str(question).strip()}"

    from openai import OpenAI

    try:
        client = OpenAI(api_key=OPENAI_API_KEY, timeout=90.0)
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            max_completion_tokens=max_tokens,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
        )
        raw = resp.choices[0].message.content or ""
    except Exception as e:  # errore di rete/API/modello: mai propagare la chiave
        return None, f"OpenAI: {type(e).__name__}: {_safe_error(e)}"

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None, "Risposta del modello non in formato JSON valido."

    # Normalizza il contratto: tutte le chiavi presenti, tipi prevedibili.
    out = {}
    for field in RESULT_FIELDS:
        val = data.get(field)
        if field == "sintesi":
            out[field] = str(val) if val else ""
        elif field == "confidenza":
            try:
                out[field] = max(0, min(100, int(float(val))))
            except (TypeError, ValueError):
                out[field] = 0
        else:
            if isinstance(val, list):
                out[field] = [str(x) for x in val]
            elif val:
                out[field] = [str(val)]
            else:
                out[field] = []
    out["model"] = OPENAI_MODEL
    return out, None


def _safe_error(e: Exception) -> str:
    """Messaggio d'errore troncato e ripulito: la chiave non deve mai finire
    in un log o in una risposta, nemmeno dentro il testo di un'eccezione."""
    msg = str(e)[:300]
    if OPENAI_API_KEY and OPENAI_API_KEY in msg:
        msg = msg.replace(OPENAI_API_KEY, "***")
    return msg
