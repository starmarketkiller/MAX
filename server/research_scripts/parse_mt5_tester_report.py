#!/usr/bin/env python3
"""26/08 - estrae da un report .htm del vero Tester MT5 (Strategy Tester,
non simulazione Python): riepilogo (net profit, trade totali, PF, DD,
win rate) + la tabella "Affari" (deals) grezza in CSV. Usato per il
backtest completo del portafoglio 2014-2026 (13 blocchi annuali OHLC +
1 blocco a tick reali), per analizzare ogni pezzo appena finisce invece
di aspettare tutto il giro."""
import sys, os, re, csv
import html as htmlmod


def load_text(path):
    with open(path, "rb") as f:
        raw = f.read()
    try:
        return raw.decode("utf-16")
    except UnicodeError:
        return raw.decode("utf-8", errors="replace")


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s)


def parse_summary(text_flat):
    labels = {
        "Profitto Totale Netto": "net_profit",
        "Profitto Lordo": "gross_profit",
        "Perdita Lorda": "gross_loss",
        "Fattore di Profitto": "profit_factor",
        "Payoff Atteso": "expected_payoff",
        "Fattore di Recupero": "recovery_factor",
        "Indice di Sharpe": "sharpe",
        "Bilancio Drawdown Massimo": "max_dd_balance",
        "Equità Drawdown Massima": "max_dd_equity",
        "Numero di Operazioni di Trading Totali": "total_trades",
        "Affari Totali": "total_deals",
        "Operazioni di Trading in Profitto": "win_trades",
        "Operazioni di Trading in Perdita": "lose_trades",
        "Operazioni di Trading Short": "short_trades",
        "Operazioni di Trading Long": "long_trades",
        "Massima vincite consecutive": "max_consec_wins_usd",
        "Massima perdite consecutive": "max_consec_losses_usd",
    }
    ridx = text_flat.find("Risultati")
    base = text_flat[ridx:] if ridx >= 0 else text_flat
    out = {}
    for lab, key in labels.items():
        idx = base.find(lab)
        if idx < 0:
            continue
        seg = base[idx + len(lab):idx + len(lab) + 60]
        m = re.search(r"[-+]?\d[\d\s.,]*", seg)
        if m:
            val = m.group(0).replace(" ", "").replace(",", "")
            out[key] = val
    return out


def parse_rows(html_content, section_marker):
    """Trova la tabella dopo section_marker (cercato DOPO 'Ordini', per non
    confondere l'intestazione della sezione con 'Affari Totali' nel
    riepilogo) e ritorna le righe come liste di celle."""
    ordini_idx = html_content.find("Ordini")
    base = html_content[ordini_idx:] if ordini_idx >= 0 else html_content
    idx = base.find(section_marker)
    if idx < 0:
        return []
    rest = base[idx:]
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", rest, re.S)
    out = []
    for r in rows[:20000]:
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)
        cells = [htmlmod.unescape(strip_tags(c)).strip() for c in cells]
        cells = [c for c in cells if c != ""]
        if cells:
            out.append(cells)
    return out


def main(path):
    html_content = load_text(path)
    text_flat = htmlmod.unescape(strip_tags(html_content))
    text_flat = re.sub(r"\s+", " ", text_flat)

    summary = parse_summary(text_flat)
    print("=== RIEPILOGO ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    deal_rows = parse_rows(html_content, "Affari")
    # scarta l'header e la riga "balance" iniziale, tieni solo deal veri
    deals = [r for r in deal_rows if len(r) >= 10 and r[0] not in ("Ora",) ]

    out_csv = os.path.splitext(path)[0] + "_deals.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for r in deals:
            w.writerow(r)
    print(f"\nDeal grezzi scritti: {len(deals)} -> {out_csv}")


if __name__ == "__main__":
    main(sys.argv[1])
