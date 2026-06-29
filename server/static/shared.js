// NEXUS EA — Shared utilities

function getLang() { return localStorage.getItem('nexus_lang') || 'it'; }
function setLang(l) { localStorage.setItem('nexus_lang', l); location.reload(); }
function getToken() { return localStorage.getItem('nexus_token'); }
function setToken(t) { localStorage.setItem('nexus_token', t); }
function clearToken() { localStorage.removeItem('nexus_token'); }
function isLoggedIn() { return !!getToken(); }
function requireAuth() { if (!isLoggedIn()) { location.href = 'login.html'; return false; } return true; }
// Il sito è servito dallo stesso backend (Render), quindi di default usa la
// stessa origine. Resta possibile forzare un altro URL da Impostazioni.
function getBackend() { return localStorage.getItem('nexus_backend_url') || window.location.origin; }

async function api(path, opts = {}) {
  const base = getBackend();
  const headers = { 'Content-Type': 'application/json' };
  const token = getToken();
  if (token) headers['Authorization'] = 'Bearer ' + token;
  try {
    const r = await fetch(base + path, { headers, ...opts });
    if (r.status === 401) { clearToken(); location.href = 'login.html'; return null; }
    if (!r.ok) throw new Error('API ' + r.status);
    return r.json();
  } catch(e) { console.warn('API error:', e); return null; }
}

function initNav(active) {
  const it = getLang() === 'it';
  const L = it
    ? { strategia:'Strategia', performance:'Performance', prezzi:'Prezzi', faq:'FAQ', cta:'Acquista ora', login:'Accedi' }
    : { strategia:'Strategy', performance:'Performance', prezzi:'Pricing', faq:'FAQ', cta:'Buy now', login:'Sign in' };
  const links = { strategia:'strategia.html', performance:'performance.html', prezzi:'prezzi.html', faq:'faq.html' };
  const nav = document.getElementById('main-nav');
  if (!nav) return;
  nav.innerHTML = `
    <div style="position:sticky;top:0;z-index:50;display:flex;align-items:center;justify-content:space-between;padding:18px 40px;background:rgba(8,11,17,.72);backdrop-filter:blur(14px);border-bottom:1px solid rgba(255,255,255,.07);font-family:'IBM Plex Sans',sans-serif;">
      <div style="display:flex;align-items:center;gap:42px;">
        <a href="index.html" style="display:flex;align-items:center;gap:11px;text-decoration:none;">
          <div style="width:30px;height:30px;border-radius:9px;background:linear-gradient(135deg,#4F8CFF,#3DDC97);display:flex;align-items:center;justify-content:center;font-family:'Sora',sans-serif;font-weight:800;color:#06101f;font-size:17px;">N</div>
          <span style="font-family:'Sora',sans-serif;font-weight:700;font-size:18px;color:#EAF0F8;">Nexus<span style="font-family:'JetBrains Mono',monospace;color:#3DDC97;font-weight:500;font-size:14px;margin-left:2px;">_EA</span></span>
        </a>
        <div style="display:flex;gap:28px;font-size:14.5px;">
          ${Object.entries(links).map(([k,href]) => `<a href="${href}" style="text-decoration:none;color:${active===k?'#FFFFFF':'#94a1b5'};">${L[k]}</a>`).join('')}
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:18px;">
        <div style="display:flex;align-items:center;font-family:'JetBrains Mono',monospace;font-size:12px;border:1px solid rgba(255,255,255,.12);border-radius:30px;overflow:hidden;">
          <button onclick="setLang('it')" style="border:none;cursor:pointer;padding:6px 12px;background:${it?'rgba(61,220,151,.18)':'transparent'};color:${it?'#3DDC97':'#94a1b5'};">IT</button>
          <button onclick="setLang('en')" style="border:none;cursor:pointer;padding:6px 12px;background:${!it?'rgba(61,220,151,.18)':'transparent'};color:${!it?'#3DDC97':'#94a1b5'};">EN</button>
        </div>
        <a href="login.html" style="text-decoration:none;font-size:14px;color:#94a1b5;">${L.login}</a>
        <a href="prezzi.html" style="text-decoration:none;padding:10px 22px;background:linear-gradient(135deg,#4F8CFF,#3DDC97);color:#06101f;font-weight:600;font-size:14px;border-radius:30px;">${L.cta}</a>
      </div>
    </div>`;
}

function renderFooter() {
  const it = getLang() === 'it';
  const el = document.getElementById('main-footer');
  if (!el) return;
  el.innerHTML = `
    <div style="border-top:1px solid rgba(255,255,255,.08);background:rgba(8,11,17,.6);font-family:'IBM Plex Sans',sans-serif;color:#94a1b5;">
      <div style="max-width:1200px;margin:0 auto;padding:54px 40px 30px;">
        <div style="display:grid;grid-template-columns:1.6fr 1fr 1fr 1fr;gap:36px;padding-bottom:40px;border-bottom:1px solid rgba(255,255,255,.07);">
          <div>
            <div style="display:flex;align-items:center;gap:11px;margin-bottom:16px;">
              <div style="width:30px;height:30px;border-radius:9px;background:linear-gradient(135deg,#4F8CFF,#3DDC97);display:flex;align-items:center;justify-content:center;font-family:'Sora',sans-serif;font-weight:800;color:#06101f;font-size:17px;">N</div>
              <span style="font-family:'Sora',sans-serif;font-weight:700;font-size:18px;color:#EAF0F8;">Nexus<span style="font-family:'JetBrains Mono',monospace;color:#3DDC97;font-weight:500;font-size:14px;margin-left:2px;">_EA</span></span>
            </div>
            <p style="font-size:14px;line-height:1.6;max-width:300px;margin:0;">${it?'Trading automatico disciplinato per MetaTrader 4 e 5. Strategia testata, rischio sotto controllo.':'Disciplined automated trading for MetaTrader 4 and 5. Tested strategy, controlled risk.'}</p>
          </div>
          <div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:12px;letter-spacing:.1em;color:#5b6472;margin-bottom:16px;">${it?'PRODOTTO':'PRODUCT'}</div>
            <div style="display:flex;flex-direction:column;gap:11px;font-size:14px;">
              <a href="strategia.html" style="color:#94a1b5;text-decoration:none;">${it?'Strategia':'Strategy'}</a>
              <a href="performance.html" style="color:#94a1b5;text-decoration:none;">Performance</a>
              <a href="prezzi.html" style="color:#94a1b5;text-decoration:none;">${it?'Prezzi':'Pricing'}</a>
            </div>
          </div>
          <div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:12px;letter-spacing:.1em;color:#5b6472;margin-bottom:16px;">${it?'SUPPORTO':'SUPPORT'}</div>
            <div style="display:flex;flex-direction:column;gap:11px;font-size:14px;">
              <a href="faq.html" style="color:#94a1b5;text-decoration:none;">FAQ</a>
              <a href="faq.html" style="color:#94a1b5;text-decoration:none;">${it?'Contatti':'Contact'}</a>
            </div>
          </div>
          <div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:12px;letter-spacing:.1em;color:#5b6472;margin-bottom:16px;">${it?'LEGALE':'LEGAL'}</div>
            <div style="display:flex;flex-direction:column;gap:11px;font-size:14px;">
              <a href="#" style="color:#94a1b5;text-decoration:none;">${it?'Termini di servizio':'Terms of service'}</a>
              <a href="#" style="color:#94a1b5;text-decoration:none;">Privacy</a>
            </div>
          </div>
        </div>
        <div style="margin-top:24px;padding:18px 20px;background:rgba(255,255,255,.03);border:1px solid rgba(255,180,80,.18);border-radius:10px;">
          <div style="font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.1em;color:#d99a4e;margin-bottom:7px;">⚠ ${it?'AVVISO DI RISCHIO':'RISK WARNING'}</div>
          <p style="font-size:12.5px;line-height:1.6;margin:0;color:#7c8aa3;">${it?'Il trading sul Forex e sui CFD comporta un elevato livello di rischio e può non essere adatto a tutti gli investitori. Le performance passate non sono indicative di risultati futuri. Investi solo capitale che puoi permetterti di perdere.':'Trading Forex and CFDs carries a high level of risk and may not be suitable for all investors. Past performance is not indicative of future results. Only invest capital you can afford to lose.'}</p>
        </div>
        <div style="margin-top:24px;display:flex;align-items:center;justify-content:space-between;font-size:13px;color:#5b6472;">
          <span>© 2026 Nexus EA. ${it?'Tutti i diritti riservati.':'All rights reserved.'}</span>
          <span style="font-family:'JetBrains Mono',monospace;font-size:12px;">MT4 · MT5</span>
        </div>
      </div>
    </div>`;
}
