import { useState, useEffect } from "react";
import { X, ChevronRight, ChevronLeft, Check, Download, Globe, KeyRound,
         Cpu, Sparkles, Activity, FlaskConical, ShieldCheck } from "lucide-react";
import api from "@/lib/api";

// Wizard-completion flag is a non-sensitive UI hint ("user has seen the
// 5-step onboarding"). Persisted in localStorage so reloading the page
// doesn't re-trigger the wizard. No tokens, PII or trading state are stored
// here — those live in httpOnly cookies / the backend DB.
const WIZARD_KEY = "nexus_wizard_done_v1";

function classNames(...c) { return c.filter(Boolean).join(" "); }

function stepDotClass(idx, currentStep) {
  if (idx === currentStep) return "w-6 bg-sky-500";
  if (idx < currentStep)   return "w-1.5 bg-sky-500/60";
  return "w-1.5 bg-secondary";
}

const STEPS = [
  {
    title: "Benvenuto in NEXUS",
    icon: Sparkles,
    body: (props) => (
      <div className="space-y-4">
        <p className="text-base">
          Ciao <strong>{props.user?.name || "trader"}</strong>! NEXUS è un EA professionale per MetaTrader 5
          con dashboard remota, AI Coach e backtest integrato.
        </p>
        <p className="text-sm text-muted-foreground">
          Questo wizard ti porta dal download dell&apos;EA al primo trade in <strong>5 step da 1 minuto</strong>.
        </p>
        <div className="grid grid-cols-2 gap-3 pt-2">
          {[
            ["35 strategie", Activity],
            ["AI Coach Claude", Sparkles],
            ["Backtest Yahoo", FlaskConical],
            ["License + Sync", ShieldCheck],
          ].map(([t, Icon]) => (
            <div key={t} className="flex items-center gap-2 p-3 rounded-lg bg-secondary/40 border border-border">
              <Icon className="h-4 w-4 text-sky-500"/>
              <span className="text-sm font-medium">{t}</span>
            </div>
          ))}
        </div>
      </div>
    ),
  },
  {
    title: "1. Scarica l'EA",
    icon: Download,
    body: () => (
      <div className="space-y-4">
        <p className="text-sm">
          Scarica il pacchetto <code className="px-1.5 py-0.5 rounded bg-secondary text-xs">NEXUS_EA_v2.0.1.zip</code> dal
          tuo container Emergent oppure dal pulsante <strong>Save to GitHub</strong>.
        </p>
        <div className="rounded-lg bg-secondary/40 border border-border p-3 text-xs font-mono">
          /app/downloads/NEXUS_EA_v2.0.1.zip
        </div>
        <p className="text-sm">Lo zip contiene:</p>
        <ul className="text-sm space-y-1 ml-4 list-disc text-muted-foreground">
          <li><code className="text-xs">MQL5/Experts/NEXUS_EA_v2.mq5</code> (entry point)</li>
          <li><code className="text-xs">MQL5/Include/NEXUS_v1/</code> (32 moduli .mqh)</li>
          <li><code className="text-xs">MQL5/Presets/*.set</code> (3 preset Conservative/Balanced/Aggressive)</li>
          <li><code className="text-xs">docs/</code> (User Manual, Quick Start, EULA)</li>
        </ul>
      </div>
    ),
  },
  {
    title: "2. Installa in MetaTrader 5",
    icon: Cpu,
    body: () => (
      <div className="space-y-4">
        <ol className="text-sm space-y-2 list-decimal ml-4">
          <li>In MT5: <strong>File → Open Data Folder</strong></li>
          <li>Entra in <code className="text-xs px-1 py-0.5 bg-secondary rounded">MQL5/</code></li>
          <li>Copia dal zip:
            <ul className="ml-4 mt-1 list-disc text-muted-foreground space-y-0.5">
              <li><code className="text-xs">Experts/NEXUS_EA_v2.mq5</code> → <code className="text-xs">MQL5/Experts/</code></li>
              <li><code className="text-xs">Include/NEXUS_v1/</code> → <code className="text-xs">MQL5/Include/NEXUS_v1/</code></li>
              <li><code className="text-xs">Presets/*.set</code> → <code className="text-xs">MQL5/Presets/</code></li>
            </ul>
          </li>
          <li>MT5 → <strong>Navigator → Expert Advisors → tasto destro → Refresh</strong></li>
          <li>Doppio-click <code className="text-xs">NEXUS_EA_v2</code> → premi <strong>F7</strong> → &quot;0 errors, 0 warnings&quot;</li>
        </ol>
      </div>
    ),
  },
  {
    title: "3. Autorizza il backend in MT5",
    icon: Globe,
    body: (props) => (
      <div className="space-y-4">
        <p className="text-sm">
          MT5 blocca le richieste HTTP per default. Devi autorizzare il backend NEXUS:
        </p>
        <ol className="text-sm space-y-2 list-decimal ml-4">
          <li>MT5 → <strong>Tools → Options → Expert Advisors</strong></li>
          <li>Spunta <strong>&quot;Allow WebRequest for listed URL&quot;</strong></li>
          <li>Aggiungi questo URL esatto (senza slash finale):</li>
        </ol>
        <div className="rounded-lg border border-sky-500/30 bg-sky-500/5 p-3 flex items-center gap-2">
          <code className="text-xs font-mono flex-1 select-all break-all">{props.host}</code>
          <button onClick={() => navigator.clipboard.writeText(props.host)}
                  className="px-2 py-1 rounded bg-sky-600 hover:bg-sky-500 text-white text-xs"
                  data-testid="wizard-copy-host">
            Copia
          </button>
        </div>
        <p className="text-sm text-muted-foreground">Click <strong>OK</strong> per salvare.</p>
      </div>
    ),
  },
  {
    title: "4. Crea la tua licenza",
    icon: KeyRound,
    body: (props) => (
      <div className="space-y-4">
        <p className="text-sm">Ti genero una licenza valida 365 giorni adesso:</p>
        {!props.licenseKey ? (
          <button onClick={props.generateLicense} disabled={props.licenseBusy}
                  className="w-full py-3 rounded-md bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white font-semibold"
                  data-testid="wizard-generate-license">
            {props.licenseBusy ? "Genero..." : "Genera la mia licenza"}
          </button>
        ) : (
          <div className="space-y-2">
            <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3">
              <div className="text-xs text-emerald-700 dark:text-emerald-300 font-bold uppercase mb-1">
                ✓ License creata
              </div>
              <code className="font-mono text-base font-bold select-all break-all">{props.licenseKey}</code>
            </div>
            <button onClick={() => navigator.clipboard.writeText(props.licenseKey)}
                    className="w-full py-2 rounded-md border border-border text-sm hover:bg-secondary"
                    data-testid="wizard-copy-license">
              Copia chiave
            </button>
          </div>
        )}
        <p className="text-xs text-muted-foreground">
          Inseriscila nel campo <code className="text-[10px]">InpLicenseKey</code> quando attacchi l&apos;EA al grafico.
          Lasciandolo vuoto parte una TRIAL 14gg con cap 0.01 lotti.
        </p>
      </div>
    ),
  },
  {
    title: "5. Attacca l'EA al grafico",
    icon: Activity,
    body: () => (
      <div className="space-y-4">
        <ol className="text-sm space-y-2 list-decimal ml-4">
          <li>Apri grafico <strong>XAUUSD M15</strong> (o <strong>GOLD</strong>)</li>
          <li>Trascina <code className="text-xs">NEXUS_EA_v2</code> dalla Navigator sul grafico</li>
          <li>Imposta inputs:
            <ul className="ml-4 mt-1 list-disc text-muted-foreground space-y-0.5 text-xs">
              <li><code>InpRiskProfile</code> = 2 (Balanced)</li>
              <li><code>InpEnableWebSync</code> = true</li>
              <li><code>InpLicenseKey</code> = la tua chiave</li>
              <li><code>InpShowDashboard</code> = true</li>
            </ul>
          </li>
          <li>Click <strong>OK</strong></li>
        </ol>
        <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3 text-sm">
          <strong className="text-emerald-700 dark:text-emerald-300">Verifica successo:</strong>
          <ul className="mt-1 space-y-0.5 text-muted-foreground list-disc ml-4 text-xs">
            <li>Pannello on-chart in alto a sinistra con badge <strong>LIVE</strong></li>
            <li>Bridge &quot;live&quot; sulla dashboard remota entro 5 sec</li>
            <li>Log Experts: <code>[NEXUS v2.0] Initialized on XAUUSD ...</code></li>
          </ul>
        </div>
      </div>
    ),
  },
  {
    title: "Tutto pronto! 🚀",
    icon: Check,
    body: () => (
      <div className="space-y-4 text-center py-4">
        <div className="h-20 w-20 mx-auto rounded-full bg-emerald-500/15 flex items-center justify-center">
          <Check className="h-10 w-10 text-emerald-600"/>
        </div>
        <h2 className="text-xl font-bold">L&apos;EA è operativo!</h2>
        <p className="text-sm text-muted-foreground">
          Esplora la dashboard: <strong>AI Coach</strong> per analisi natural language,
          <strong> Journal</strong> per taggare i trade, <strong>Backtest</strong> per testare su Gold storico,
          <strong> Risk</strong> per controlli avanzati.
        </p>
        <p className="text-xs text-muted-foreground pt-2">
          Puoi riaprire questo wizard dal menu Settings → Reset onboarding.
        </p>
      </div>
    ),
  },
];

export default function SetupWizard({ user, onClose }) {
  const [step, setStep] = useState(0);
  const [licenseKey, setLicenseKey] = useState("");
  const [licenseBusy, setLicenseBusy] = useState(false);
  const host = typeof window !== "undefined" ? window.location.origin : "";

  const generateLicense = async () => {
    if (licenseBusy) return;
    setLicenseBusy(true);
    try {
      const { data } = await api.post("/license/create", {
        client: user?.name || user?.email || "Onboarding",
        plan: "STANDARD", days: 365,
      });
      setLicenseKey(data.key);
    } catch (e) { console.error(e); }
    finally { setLicenseBusy(false); }
  };

  const close = () => {
    localStorage.setItem(WIZARD_KEY, "1");
    onClose && onClose();
  };

  const StepIcon = STEPS[step].icon;
  const StepBody = STEPS[step].body;
  const isLast = step === STEPS.length - 1;
  const progress = ((step + 1) / STEPS.length) * 100;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
         data-testid="setup-wizard-overlay" onClick={(e) => e.target === e.currentTarget && close()}>
      <div className="bg-card border border-border rounded-2xl w-full max-w-xl max-h-[90vh] flex flex-col shadow-2xl">
        {/* Progress bar */}
        <div className="h-1 bg-secondary rounded-t-2xl overflow-hidden">
          <div className="h-full bg-gradient-to-r from-sky-500 to-indigo-500 transition-all duration-300"
               style={{ width: `${progress}%` }}/>
        </div>

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-sky-500/15 flex items-center justify-center">
              <StepIcon className="h-5 w-5 text-sky-600 dark:text-sky-400"/>
            </div>
            <div>
              <div className="text-[10px] uppercase text-muted-foreground tracking-wider">
                Step {step + 1} di {STEPS.length}
              </div>
              <div className="font-bold">{STEPS[step].title}</div>
            </div>
          </div>
          <button onClick={close} className="text-muted-foreground hover:text-foreground p-1"
                  data-testid="wizard-close">
            <X className="h-5 w-5"/>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          <StepBody host={host} user={user}
                    licenseKey={licenseKey} licenseBusy={licenseBusy}
                    generateLicense={generateLicense}/>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-3 border-t border-border bg-secondary/30">
          <button onClick={() => setStep(s => Math.max(0, s - 1))} disabled={step === 0}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-md text-sm hover:bg-secondary disabled:opacity-40"
                  data-testid="wizard-prev">
            <ChevronLeft className="h-4 w-4"/> Indietro
          </button>
          <div className="flex gap-1">
            {STEPS.map((s, i) => (
              <div key={s.title} className={classNames("h-1.5 rounded-full transition-all",
                stepDotClass(i, step))}/>
            ))}
          </div>
          {isLast ? (
            <button onClick={close}
                    className="flex items-center gap-1 px-4 py-1.5 rounded-md bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold"
                    data-testid="wizard-finish">
              Inizia <Check className="h-4 w-4"/>
            </button>
          ) : (
            <button onClick={() => setStep(s => Math.min(STEPS.length - 1, s + 1))}
                    className="flex items-center gap-1 px-4 py-1.5 rounded-md bg-sky-600 hover:bg-sky-500 text-white text-sm font-semibold"
                    data-testid="wizard-next">
              Avanti <ChevronRight className="h-4 w-4"/>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export function shouldShowWizard() {
  if (typeof window === "undefined") return false;
  return !localStorage.getItem(WIZARD_KEY);
}

export function resetWizard() {
  localStorage.removeItem(WIZARD_KEY);
}
