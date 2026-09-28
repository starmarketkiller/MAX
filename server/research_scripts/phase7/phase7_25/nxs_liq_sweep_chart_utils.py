#!/usr/bin/env python3
"""Phase 7.25 - rendering SVG puro-Python per il Visual Audit (NESSUNA
libreria di charting esterna - matplotlib e' risultato bloccato in
questo ambiente: 'ImportError: DLL load failed while importing _image
- Un criterio di controllo dell'applicazione ha bloccato il file' -
policy di sicurezza dell'ambiente, non risolvibile con una
reinstallazione. Pivot dichiarato: SVG generato a mano, zero
dipendenze native, stesso contenuto informativo (candele OHLC,
livelli entry/SL/TP, marker entry/exit).

Research-only: nessuna immagine e' usata per derivare regole
operative, solo per l'ispezione qualitativa Stage A/B/C."""
import html

WIDTH, HEIGHT = 900, 380
MARGIN_L, MARGIN_R, MARGIN_T, MARGIN_B = 60, 90, 30, 40


def _scale(df, extra_prices):
    lows = list(df["low"]) if not df.empty else []
    highs = list(df["high"]) if not df.empty else []
    prices = lows + highs + [p for p in extra_prices if p is not None]
    if not prices:
        prices = [0, 1]
    lo, hi = min(prices), max(prices)
    pad = (hi - lo) * 0.08 or 1.0
    return lo - pad, hi + pad


def render_panel_svg(df, title, extra_hlines=None, extra_vlines=None, truncate_at_idx=None):
    """extra_hlines: list of (price, label, color). extra_vlines: list
    of (idx, label, color). truncate_at_idx: se dato, disegna solo le
    barre fino a quell'indice incluso (Stage A - nessuna barra futura)."""
    extra_hlines = extra_hlines or []
    extra_vlines = extra_vlines or []
    n = len(df) if truncate_at_idx is None else min(truncate_at_idx + 1, len(df))
    plot_w = WIDTH - MARGIN_L - MARGIN_R
    plot_h = HEIGHT - MARGIN_T - MARGIN_B

    if n == 0:
        body = (f'<text x="{WIDTH/2}" y="{HEIGHT/2}" text-anchor="middle" '
               f'font-size="13" fill="#888">NESSUN DATO IN QUESTA FINESTRA</text>')
        return _wrap_svg(title, body)

    sub = df.iloc[:n]
    lo, hi = _scale(sub, [h[0] for h in extra_hlines])

    def px(i):
        return MARGIN_L + (i + 0.5) * (plot_w / n)

    def py(price):
        return MARGIN_T + (hi - price) / (hi - lo) * plot_h

    bar_w = max(1.5, (plot_w / n) * 0.6)
    parts = []
    for i, (_, row) in enumerate(sub.iterrows()):
        o, h_, l, c = row["open"], row["high"], row["low"], row["close"]
        color = "#2a9d5c" if c >= o else "#c0392b"
        x = px(i)
        parts.append(f'<line x1="{x:.1f}" y1="{py(h_):.1f}" x2="{x:.1f}" y2="{py(l):.1f}" '
                    f'stroke="{color}" stroke-width="1"/>')
        y_top, y_bot = py(max(o, c)), py(min(o, c))
        parts.append(f'<rect x="{x - bar_w/2:.1f}" y="{y_top:.1f}" width="{bar_w:.1f}" '
                    f'height="{max(y_bot - y_top, 0.8):.1f}" fill="{color}" stroke="{color}"/>')

    for price, label, color in extra_hlines:
        if price is None or not (lo <= price <= hi or True):
            continue
        y = py(price)
        parts.append(f'<line x1="{MARGIN_L}" y1="{y:.1f}" x2="{WIDTH - MARGIN_R}" y2="{y:.1f}" '
                    f'stroke="{color}" stroke-width="1" stroke-dasharray="4,3"/>')
        parts.append(f'<text x="{WIDTH - MARGIN_R + 4}" y="{y+3:.1f}" font-size="10" '
                    f'fill="{color}">{html.escape(label)}</text>')

    for idx, label, color in extra_vlines:
        if idx is None or idx < 0 or idx >= n:
            continue
        x = px(idx)
        parts.append(f'<line x1="{x:.1f}" y1="{MARGIN_T}" x2="{x:.1f}" y2="{HEIGHT - MARGIN_B}" '
                    f'stroke="{color}" stroke-width="1.2" stroke-dasharray="2,2"/>')
        parts.append(f'<text x="{x+3:.1f}" y="{MARGIN_T+10}" font-size="9" fill="{color}" '
                    f'transform="rotate(90 {x+3:.1f} {MARGIN_T+10})">{html.escape(label)}</text>')

    n_ticks = min(6, n)
    step = max(1, n // n_ticks) if n_ticks else n
    for i in range(0, n, step):
        x = px(i)
        ts = sub.iloc[i]["time"]
        lbl = ts.strftime("%Y-%m-%d")
        parts.append(f'<line x1="{x:.1f}" y1="{HEIGHT - MARGIN_B}" x2="{x:.1f}" '
                    f'y2="{HEIGHT - MARGIN_B + 4}" stroke="#999"/>')
        parts.append(f'<text x="{x:.1f}" y="{HEIGHT - MARGIN_B + 16}" font-size="8" '
                    f'text-anchor="middle" fill="#555">{lbl}</text>')

    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        price = lo + frac * (hi - lo)
        y = py(price)
        parts.append(f'<line x1="{MARGIN_L}" y1="{y:.1f}" x2="{WIDTH-MARGIN_R}" y2="{y:.1f}" '
                    f'stroke="#eee" stroke-width="0.6"/>')
        parts.append(f'<text x="{MARGIN_L-6}" y="{y+3:.1f}" font-size="8" text-anchor="end" '
                    f'fill="#555">{price:.1f}</text>')

    parts.append(f'<rect x="{MARGIN_L}" y="{MARGIN_T}" width="{plot_w}" height="{plot_h}" '
                f'fill="none" stroke="#ccc"/>')
    body = "\n".join(parts)
    return _wrap_svg(title, body)


def _wrap_svg(title, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT+22}" '
           f'viewBox="0 0 {WIDTH} {HEIGHT+22}" font-family="sans-serif">\n'
           f'<rect width="100%" height="100%" fill="white"/>\n'
           f'<text x="{WIDTH/2}" y="16" text-anchor="middle" font-size="12" font-weight="bold">'
           f'{html.escape(title)}</text>\n'
           f'<g transform="translate(0,20)">\n{body}\n</g>\n</svg>\n')


def save_svg(svg_text, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg_text)


def index_for_time(df, ts):
    if df.empty:
        return None
    diffs = (df["time"] - ts).abs()
    return int(diffs.idxmin())
