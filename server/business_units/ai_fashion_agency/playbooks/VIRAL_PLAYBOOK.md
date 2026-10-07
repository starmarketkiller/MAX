# AI Fashion Agency — Viral Playbook v1

Playbook creativo della Business Unit AI_FASHION_AGENCY (migrato da
`marketing/ai-creator/`). È il know-how usato dalle skill `VIRAL_FORMAT_ANALYSIS`,
`CONTENT_BRIEF_DRAFT` e `CONTENT_REVIEW`; le regole vincolanti (store gate, compliance,
approvazione crediti) sono codificate in `pipeline.py` e prevalgono su questo testo.

Obiettivo: creator AI (umani realistici, inglese, lifestyle/intrattenimento/fashion) che
rifanno i format virali nella propria versione, crescono un pubblico e monetizzano con
prodotti trovati dalle automazioni NEXUS, sempre dopo lo STORE_READY.

## 1. Il "modello ad hoc": anatomia di un video che prende like e commenti

Ogni video (7–25 s) segue questa struttura:

| Tempo | Blocco | Cosa deve succedere |
|---|---|---|
| 0–1.5 s | **HOOK visivo** | Si parte a metà azione (mai "ciao ragazzi"). Movimento, faccia vicina, qualcosa di strano/inatteso nel frame. |
| 0–3 s | **HOOK testuale** | Testo grande on-screen, max 8 parole: curiosity gap ("I didn't expect THIS"), POV, claim forte, "unpopular opinion". |
| 3–N s | **Tensione** | Un'interruzione ogni 3–5 s: taglio, zoom, cambio angolo, sound effect, reazione. Zero tempi morti. Sottotitoli sempre. |
| finale | **Payoff + loop** | Il colpo di scena arriva tardi; l'ultimo frame si ricollega al primo così il video ricomincia (rewatch = segnale forte). |
| dopo | **Comment bait** | Domanda polarizzante o "A o B?", piccolo dettaglio "sbagliato" che la gente vuole correggere, finale aperto. |

Leve emotive che funzionano: sorpresa, cringe/imbarazzo simpatico, soddisfazione,
"relatable" (situazioni quotidiane), animali buffi, aspirazione.

## 2. Identità del creator (la "particolarità")

- Look fisso riconoscibile in 1 frame: cuffie bianche al collo, orecchini argento,
  streetwear oversize. Sempre uguali → riconoscimento nel feed.
- Firma ricorrente: stessa frase/gesto finale in ogni video (es. sguardo in camera + "...anyway").
- Format seriali (la gente segue le serie): "Trying viral trends so you don't have to",
  "POV: …", "Rating TikTok-famous products", "Me vs. my pet" (animali = reach facile).
- Stile phone-camera, non patinato: più credibile e meno "pubblicità".

## 3. Pipeline: video virale → versione del creator

1. **Input**: `TREND_VIDEO` / `TREND_FORMAT` / `TREND_AUDIO` sull'Agency Input Bus.
2. **Analisi**: skill `VIRAL_FORMAT_ANALYSIS` (Orchestrator) → solo struttura: hook, beat,
   payoff, comment bait, strategia audio. Nessun media conservato.
3. **Brief + modella**: `CONTENT_BRIEF` → compliance → `MODEL_ASSIGNMENT`.
4. **Remake** su Higgsfield (motion transfer / generazione nuova) tramite Generation Pack:
   preventivo → approvazione esplicita → esecuzione.
5. **Pubblicazione**: futura, tramite il Social subsystem; audio dalla libreria della
   piattaforma, etichetta AI attiva.

Regola d'oro: si copia il **format**, mai il video. Ripubblicare clip altrui con il
personaggio sopra = rischio strike/copyright e ban del monetization.

## 4. Monetizzazione (in ordine di arrivo realistico)

1. Affiliazioni / prodotti trend trovati da NEXUS (link in bio, TikTok Shop) — da subito.
2. Prodotti propri — quando c'è pubblico.
3. Sponsorizzazioni di brand — dopo ~10k follower e metriche stabili.
4. Creator fund / bonus piattaforme — tardi, soglie alte.

## 5. Regole obbligatorie (altrimenti la reach crolla o arrivano sanzioni)

- **Etichetta AI**: Instagram dal 2026 riduce la reach dei profili con persona AI non
  dichiarata ("AI-generated profile" label); TikTok richiede l'etichetta sui contenuti AI
  realistici; EU AI Act art. 50 dal 2 agosto 2026. → Etichetta attiva + "AI creator" in bio.
- **Pubblicità**: regole AGCOM influencer (vincolanti dal 2025) → ogni prodotto sponsorizzato
  o in affiliazione va marcato (#ad / "Paid partnership" / tag affiliazione).
- **Clickbait sì, inganno no**: hook curiosi ok; promesse false sul prodotto, finti
  "prima/dopo", claim su soldi/guadagni = rimozione + rischio legale. Prodotti di trading
  NEXUS: niente promesse di rendimento.

## 6. Ritmo e misure

- 1–2 video al giorno per 30 giorni prima di giudicare.
- Metriche guida: % visione dei primi 3 s, completion rate, rewatch, commenti/1k views.
- Ogni settimana: tieni i 3 format migliori, elimina i 3 peggiori.
