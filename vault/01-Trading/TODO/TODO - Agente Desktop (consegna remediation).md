---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, todo, agente-desktop, consegna]
created: 2026-07-25
updated: 2026-07-25
---

# TODO — agente desktop: consegna della remediation

Piano d'azione ordinato per **chi ha accesso alla macchina** (MetaEditor, MT5,
Docker, terminale). Tutto ciò che non era producibile in ambiente remoto è qui.

Branch da usare: **`main`** — la remediation è stata unita il 25/07/2026
(13 commit, avanzamento lineare da `ef807ab` a `3cf2b3b`, nessun merge commit).
Il branch di lavoro `claude/file-review-complete-rwq562` punta allo stesso commit
e non serve più.

> ⚠️ `main` è la baseline da cui `DEPLOY.md` fa partire il deploy. `autoDeploy`
> è **disattivato** in `render.yaml`, quindi questo push non ha messo nulla in
> produzione da solo. Non attivarlo prima dei punti 1 e 2 qui sotto.

Ordine non arbitrario: 1 è una falla di sicurezza attiva, 2-3 sbloccano tutto il
resto, il seguito è consolidamento.

---

## 🔴 1. Ricostruire e ridistribuire il bundle React

**Perché per primo:** il file servito agli utenti sotto `/app` mostra ancora
utente e password di default sulla schermata di login, e non invia il token
anti-CSRF. Il sorgente è corretto, **il bundle no** — non è mai stato ricostruito
dopo le correzioni.

```bash
cd frontend
npm install --legacy-peer-deps
npm run build
rm -rf ../server/static/app
cp -r build ../server/static/app
```

**Verifica — deve dare zero e uno:**

```bash
# 0 = le credenziali non ci sono più
grep -c "nexus123" server/static/app/static/js/main.*.js
# ≥1 = la protezione CSRF c'è
grep -c "X-Nexus-Csrf" server/static/app/static/js/*.js
```

Poi commit del bundle. Finché questo non è fatto, **non esporre la dashboard**.

---

## 🔴 2. Compilare l'EA in MetaEditor

**Nessuna riga di `MQL5/` è mai stata compilata.** Le modifiche sono estese: 3 file
nuovi (`NXS_Intent.mqh`, `NXS_Outbox.mqh` + il registro rigenerato) e ~20 modificati.

1. aprire `MQL5/Experts/NEXUS_EA_v2.mq5` in MetaEditor;
2. compilare, **pretendere 0 errori e 0 warning**;
3. se ci sono errori, quasi certamente sono di due tipi:
   - **simbolo non dichiarato** → ordine di inclusione (l'inclusione MQL5 è
     testuale). I moduli nuovi vanno in questo ordine, già impostato nel `.mq5`:
     `NXS_Globals` → `NXS_Outbox` → `NXS_Intent` → tutto il resto;
   - **firma di funzione** → un chiamante che non è stato aggiornato.

Annotare l'esito in [[NEXUS EA - Log Versioni]] con la build MetaEditor usata.

---

## 🔴 3. Strategy Tester — la parità cambia i numeri

Prima passata di riferimento **con `InpTesterProtectionParity = true`** (default).

Aspettarsi **meno trade e curve diverse** da tutti i backtest precedenti: prima il
tester disattivava in blocco protezioni e cap di conto. I numeri nuovi sono quelli
confrontabili col live; i vecchi no. Vedi
[[DEC - Cambi di comportamento post-remediation]] §1.

Cosa guardare nel log, oltre al risultato:

- `rischio iniziale ignoto — trade ESCLUSO dalle statistiche in R` → se compare
  spesso, molti ingressi non registrano il budget di rischio: da indagare;
- `DERIVA CONTRATTO` o `non e' nel registro canonico` → una lista di strategie
  scritta a mano è disallineata;
- `lista counter-HTF coerente con il registro canonico` e `router allineato al
  registro canonico (37 strategie)` → i due controlli di coerenza sono passati;
- `OPEN BLOCCATO: ...` con i motivi nuovi (tabella in [[DEC - Cambi di comportamento post-remediation]] §7).

Poi una seconda passata con `false` **solo** se serve confrontare con lo storico.

---

## 🟠 4. Test su demo, prima del reale

1. `InpEnvironment = "DEMO"` sull'EA e `NEXUS_ENV=DEMO` sul backend;
2. generare un token dedicato — `InpWebToken` non ha più default e la WebSync si
   spegne senza:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
3. verificare che l'EA parta **senza** `Alert` di credenziali;
4. su conto **non-hedging** l'EA rifiuterà di partire: è voluto
   ([[DEC - Cambi di comportamento post-remediation]] §4);
5. provare un `reset_protections` dalla dashboard: deve chiedere la password
   (`401 STEPUP_REQUIRED`), poi funzionare.

---

## 🟠 5. Ri-eseguire i backtest con report identici

Cinque coppie di report dichiarano strategie diverse ma sono lo stesso file, e due
gruppi da 6 snapshot da 25 MB sono copie della stessa passata. Elenco completo in
[[NEXUS EA - Igiene Repository e Duplicati]] §1 e §2.

Da fare: ri-eseguirle con l'identità di run attiva (il CSV porta ora `run_id`,
agente e istante di avvio), **oppure** archiviarle dichiarandole non valide. Non
lasciarle con quei nomi: qualsiasi conclusione tratta da lì è priva di fondamento.

Se una di queste passate è finita in
[[NEXUS EA - Screening Strategie (sito 10y)]] o nel ranking per strategia, quel
giudizio va rifatto.

---

## 🟡 6. Recuperare 250 MB di duplicati

Solo **dopo** il punto 5, perché quei file sono l'evidenza da rifare.

```bash
# elenco dei gruppi identici prima di toccare qualsiasi cosa
python3 - <<'EOF'
import hashlib, subprocess, collections, os
files=[f for f in subprocess.run(["git","ls-files"],capture_output=True,text=True).stdout.split() if os.path.isfile(f)]
h=collections.defaultdict(list)
for f in files: h[hashlib.sha256(open(f,'rb').read()).hexdigest()].append(f)
for k,v in h.items():
    if len(v)>1: print(f"{os.path.getsize(v[0])/1e6:.1f} MB × {len(v)}"); [print("   ",x) for x in v]
EOF
```

Conservare **un** file per gruppo. `results/` è il 98% del peso del repository e
più della metà sono copie: valutare se spostarlo fuori da git (Git LFS o archivio
separato) — non è codice, è evidenza sperimentale, e git non è il posto giusto per
250 MB di CSV identici.

**Non cancellare nulla senza aver deciso il punto 5.**

---

## 🟡 7. Decidere la fonte di `seed_recipe.json`

`results/best_per_strategy_multitf_XAUUSD.json` e `server/seed_recipe.json` sono lo
stesso file. Un artefatto di ricerca è diventato configurazione operativa per copia
manuale. Scegliere quale è la fonte e generare l'altro con uno script versionato.

Mitigazione già attiva: i seed non girano negli ambienti induriti
(`NEXUS_SEED_ON_START=false` di default in DEMO/PAPER/LIVE).

---

## 🟡 8. Lock riproducibile delle dipendenze Python

```bash
pip install pip-tools
pip-compile --generate-hashes --output-file=server/requirements.lock.txt server/requirements.txt
```

Il `Dockerfile` lo rileva da solo: se il lock c'è installa con `--require-hashes`,
altrimenti stampa `build NON riproducibile` e prosegue.

---

## 🟡 9. Ancorare l'immagine base al digest

```bash
docker pull python:3.12-slim
docker inspect --format='{{index .RepoDigests 0}}' python:3.12-slim
```

Sostituire `FROM python:3.12-slim` con `FROM python:3.12-slim@sha256:<digest>` in
`server/Dockerfile`. Finché resta il tag mutabile, due build dello stesso commit
producono immagini diverse.

---

## 🟢 10. Prima di andare in produzione

- [ ] `NEXUS_ENV=LIVE`, tutti i segreti generati (il backend rifiuta di avviarsi
      con valori di default: è voluto)
- [ ] `NEXUS_AUTO_MIGRATE=false` + `python -m app --migrate` **prima** di mettere
      in servizio la nuova versione (obbligatorio con più repliche)
- [ ] `python -m app --verify-ledger` → deve dare `ok: True`
- [ ] `/api/ready` risponde 200 (non `/api/health`: quello prova solo che il
      processo risponda)
- [ ] backup con restore drill superato: `POST /api/admin/backup/drill`
- [ ] `InpProtScopeAccountWide` — se fai girare più istanze sullo stesso conto
      divise per simbolo, mettilo a `false`

---

## Cosa NON è stato fatto e perché

| Voce | Motivo |
|---|---|
| Compilazione MetaEditor | Strumento assente nell'ambiente remoto |
| Strategy Tester | Idem |
| Forward test su broker | Idem |
| Credenziale per istanza EA | Cambio di protocollo, non correzione puntuale (`NEXUS-ID-004`) |
| Firma degli artefatti | Serve una chiave e un punto di fiducia (`NEXUS-SEC-003`) |
| Gate di approvazione strategie | Decisione di prodotto: renderlo bloccante cambia il modo di lavorare |

## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Remediation Audit v18]] ·
[[NEXUS EA - Igiene Repository e Duplicati]] ·
[[DEC - Cambi di comportamento post-remediation]] · [[TODO - Backtest 10Y]]
