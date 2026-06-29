import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { useTheme } from "@/lib/theme";
import { formatApiError } from "@/lib/api";
import { Activity, ShieldCheck, Sun, Moon, ArrowRight, TrendingUp, TrendingDown } from "lucide-react";

// Mock ticker data — pure visual flourish (no live API call from the auth page).
const TICKER_FEED = [
  { sym: "XAUUSD", px: "2384.21", chg: "+1.24%", dir: "up" },
  { sym: "EURUSD", px: "1.0742",  chg: "-0.18%", dir: "dn" },
  { sym: "GBPUSD", px: "1.2654",  chg: "+0.42%", dir: "up" },
  { sym: "BTCUSD", px: "68 412",  chg: "+2.81%", dir: "up" },
  { sym: "USDJPY", px: "156.32",  chg: "-0.34%", dir: "dn" },
  { sym: "WTI",    px: "78.45",   chg: "+0.92%", dir: "up" },
  { sym: "DXY",    px: "104.18",  chg: "-0.21%", dir: "dn" },
  { sym: "SPX500", px: "5 487",   chg: "+0.67%", dir: "up" },
];

function TickerTape() {
  // Double the array so vertical scroll loops seamlessly
  const doubled = [...TICKER_FEED, ...TICKER_FEED];
  return (
    <div className="absolute inset-y-0 right-8 w-44 overflow-hidden pointer-events-none opacity-80 hidden lg:block">
      <div className="absolute inset-x-0 top-0 h-24 bg-gradient-to-b from-[#080c14] to-transparent z-10" />
      <div className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-[#080c14] to-transparent z-10" />
      <div className="ticker-vertical flex flex-col gap-2 pt-12">
        {doubled.map((t, i) => (
          <div
            key={`${t.sym}-${i}`}
            className="rounded-lg border border-cyan-500/15 bg-cyan-500/5 backdrop-blur-sm px-3 py-2 text-xs"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono font-bold tracking-wider text-cyan-300">{t.sym}</span>
              {t.dir === "up"
                ? <TrendingUp className="h-3 w-3 text-emerald-400" />
                : <TrendingDown className="h-3 w-3 text-rose-400" />
              }
            </div>
            <div className="font-mono text-base font-semibold text-white mt-0.5 tabular">{t.px}</div>
            <div className={`font-mono text-[10px] mt-0.5 tabular ${t.dir === "up" ? "text-emerald-400" : "text-rose-400"}`}>
              {t.chg}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function AnimatedGrid() {
  return (
    <>
      <div
        className="absolute inset-0 opacity-[0.18]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(34,211,238,0.35) 1px, transparent 1px), linear-gradient(90deg, rgba(34,211,238,0.35) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
          maskImage: "radial-gradient(ellipse 70% 60% at 30% 50%, black 30%, transparent 100%)",
          WebkitMaskImage: "radial-gradient(ellipse 70% 60% at 30% 50%, black 30%, transparent 100%)",
        }}
      />
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 700px 500px at 20% 30%, rgba(34,211,238,0.18) 0%, transparent 60%), radial-gradient(ellipse 600px 400px at 80% 75%, rgba(99,102,241,0.12) 0%, transparent 55%)",
        }}
      />
    </>
  );
}

export default function Login() {
  const { login } = useAuth();
  const { theme, toggle } = useTheme();
  const nav = useNavigate();
  const [email, setEmail] = useState("admin@nexus.local");
  const [password, setPassword] = useState("nexus123");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [clock, setClock] = useState("");

  useEffect(() => {
    const tick = () => {
      const d = new Date();
      const hh = String(d.getUTCHours()).padStart(2, "0");
      const mm = String(d.getUTCMinutes()).padStart(2, "0");
      const ss = String(d.getUTCSeconds()).padStart(2, "0");
      setClock(`${hh}:${mm}:${ss} UTC`);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(email, password);
      nav("/", { replace: true });
    } catch (err) {
      setError(formatApiError(err?.response?.data?.detail) || err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-background text-foreground" data-testid="login-page">
      {/* Brand / cockpit panel */}
      <div className="hidden md:flex md:w-1/2 lg:w-[55%] relative overflow-hidden bg-[#080c14] text-white p-12 flex-col justify-between">
        <AnimatedGrid />
        <TickerTape />

        <div className="relative flex items-center gap-3 z-10">
          <div className="h-11 w-11 rounded-xl bg-cyan-400/10 backdrop-blur flex items-center justify-center ring-1 ring-cyan-400/30 shadow-[0_0_24px_rgba(34,211,238,0.35)]">
            <Activity className="h-5 w-5 text-cyan-300" strokeWidth={2.25} />
          </div>
          <div>
            <div className="font-bold text-2xl tracking-tight">NEXUS</div>
            <div className="text-[10px] uppercase tracking-[0.24em] text-cyan-300/70 mt-0.5">EA Control Center</div>
          </div>
        </div>

        <div className="relative space-y-7 max-w-lg z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-400/10 ring-1 ring-cyan-400/25 backdrop-blur">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75 animate-ping" />
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-400" />
            </span>
            <span className="text-[11px] font-mono tracking-wider text-cyan-200 tabular">
              SYSTEM ONLINE · {clock}
            </span>
          </div>

          <h1 className="text-5xl lg:text-6xl font-bold tracking-tight leading-[1.02]">
            Mission control<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 to-emerald-300">
              for GOLD
            </span>{" "}
            automation.
          </h1>
          <p className="text-white/65 text-base leading-relaxed max-w-md">
            35 strategie (Trend · Reversal · SMC · Institutional), gate intelligenti, structure-reaction engine
            e risk management completo. Stato live e controllo remoto del tuo Expert Advisor MetaTrader 5.
          </p>
          <div className="flex flex-wrap gap-2 pt-2">
            {[
              { label: "XAUUSD", glow: true },
              { label: "MT5 / MQL5" },
              { label: "JWT secured" },
              { label: "Shadow Trading v2.0.8" },
            ].map((p) => (
              <span
                key={p.label}
                className={`px-3 py-1 rounded-full text-[11px] font-mono tracking-wide ring-1 ${
                  p.glow
                    ? "bg-cyan-400/15 text-cyan-200 ring-cyan-400/30 shadow-[0_0_12px_rgba(34,211,238,0.25)]"
                    : "bg-white/5 text-white/70 ring-white/15"
                }`}
              >
                {p.label}
              </span>
            ))}
          </div>
        </div>

        <div className="relative text-[10px] font-mono tracking-wider text-white/40 z-10">
          © 2026 NEXUS EA · ITALIAN TRADERS CLUB · v2.0.9
        </div>
      </div>

      {/* Form panel */}
      <div className="flex-1 flex flex-col">
        <div className="flex justify-end p-5">
          <button
            onClick={toggle}
            data-testid="theme-toggle-login"
            className="h-9 w-9 rounded-full border border-border flex items-center justify-center text-muted-foreground hover:text-primary hover:border-primary/40 transition-colors"
            aria-label="Toggle theme"
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
        </div>

        <div className="flex-1 flex items-center justify-center px-6 pb-12">
          <form onSubmit={submit} className="w-full max-w-sm space-y-7 fade-in" data-testid="login-form">
            <div className="space-y-2 md:hidden">
              <div className="flex items-center gap-2">
                <div className="h-9 w-9 rounded-lg bg-primary/15 text-primary ring-1 ring-primary/30 flex items-center justify-center">
                  <Activity className="h-4 w-4" />
                </div>
                <span className="font-bold text-xl tracking-tight">NEXUS</span>
              </div>
            </div>

            <div>
              <div className="eyebrow mb-2">Sign in</div>
              <h2 className="text-3xl font-semibold tracking-tight">Welcome back</h2>
              <p className="text-sm text-muted-foreground mt-2">
                Use your admin credentials to control the EA.
              </p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-1.5 block">Email</label>
                <input
                  data-testid="login-email-input"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  className="w-full h-11 px-3.5 rounded-lg bg-background border border-border text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary/50 transition-all"
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-1.5 block">Password</label>
                <input
                  data-testid="login-password-input"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  className="w-full h-11 px-3.5 rounded-lg bg-background border border-border text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary/50 transition-all"
                />
              </div>
            </div>

            {error && (
              <div
                data-testid="login-error"
                className="px-3.5 py-2.5 rounded-lg text-sm bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/30"
              >
                {error}
              </div>
            )}

            <button
              data-testid="login-submit-button"
              type="submit"
              disabled={busy}
              className="group relative w-full h-11 rounded-lg bg-primary text-primary-foreground text-sm font-semibold transition-all disabled:opacity-60 flex items-center justify-center gap-2 shadow-[0_0_24px_hsl(var(--primary)/0.35)] hover:shadow-[0_0_32px_hsl(var(--primary)/0.55)] hover:brightness-110 active:scale-[0.98] overflow-hidden"
            >
              <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
              {busy ? "Signing in…" : (
                <>
                  Sign in to dashboard
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                </>
              )}
            </button>

            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <ShieldCheck className="h-3.5 w-3.5" />
              Secured with JWT · default: admin@nexus.local / nexus123
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
