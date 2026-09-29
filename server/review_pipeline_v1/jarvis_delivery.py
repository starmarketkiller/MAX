#!/usr/bin/env python3
"""NEXUS TASK #0008 punto 13 - come Jarvis presenta un FINAL_RESULT_PACKET_V1
all'utente: per default un riepilogo compatto, mai l'intera chain-of-work
interna. Le query esplicite ('chi ha lavorato...', 'perche' hai chiamato
Claude...', 'cosa ha corretto il reviewer...') restano disponibili su
richiesta, lette dallo stesso packet - mai inventate."""


def format_task_completed_summary(final_result_packet):
    p = final_result_packet
    reviewers = ", ".join(p["reviewers"]) if p["reviewers"] else "nessuno (non richiesta)"
    verifiers = ", ".join(p["verifiers"]) if p["verifiers"] else "nessuno"
    header = (
        "TASK COMPLETED\n"
        f"Producer: {p['producer']}\n"
        f"Reviewer: {reviewers}\n"
        f"Verifier: {verifiers}\n"
        f"Confidence: {p['confidence']}\n"
        f"Premium calls: {p['premium_calls']}\n"
        f"Status: {'FINALIZED' if not p['remaining_risks'] else 'FINALIZED_WITH_LIMITATIONS'}"
    )
    return header


def explain(final_result_packet, question):
    """Risponde SOLO con fatti gia' presenti nel packet - mai un giudizio
    non tracciabile a una fonte. Ritorna None se la domanda non e' fra
    quelle riconosciute (il chiamante decide come gestire quel caso, non
    inventa una risposta qui)."""
    p = final_result_packet
    q = (question or "").strip().lower()

    if any(k in q for k in ("chi ha lavorato", "who worked")):
        parts = [f"producer: {p['producer']}"]
        if p["reviewers"]:
            parts.append(f"reviewer: {', '.join(p['reviewers'])}")
        if p["verifiers"]:
            parts.append(f"verifier: {', '.join(p['verifiers'])}")
        return "; ".join(parts)

    if "perch" in q and ("claude" in q or "premium" in q or "chiamato" in q or "called" in q):
        if not p["premium_agents_used"]:
            return "Nessun provider premium e' stato chiamato per questa task."
        return (f"Provider premium usati: {', '.join(p['premium_agents_used'])}. "
               f"Motivo: {p.get('next_recommended_action') or 'vedi limitations/remaining_risks'} "
               f"- limitazioni: {'; '.join(p['limitations']) or 'nessuna dichiarata'}.")

    if any(k in q for k in ("cosa ha corretto", "what did the reviewer", "reviewer corretto")):
        if not p["changes_made_during_review"]:
            return "Il reviewer non ha richiesto correzioni: approvato cosi' com'era."
        return "Correzioni durante la review: " + "; ".join(p["changes_made_during_review"])

    return None
