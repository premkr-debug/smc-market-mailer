"""Daily 'Market ki Halchal' creative generator. Free stack: yfinance + Playwright + GitHub Actions/Pages."""
import io, os, sys, pathlib, datetime as dt, zoneinfo
import pandas as pd, requests, yfinance as yf
from jinja2 import Template
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).parent
IST = zoneinfo.ZoneInfo("Asia/Kolkata")
NOW = dt.datetime.now(IST)
FORCE = os.getenv("FORCE") == "1"

# Short display names (add more as needed)
NAMES = {"HINDUNILVR": "HUL", "TATACONSUM": "TATA Cons. Prod", "HDFCLIFE": "HDFC Life",
         "INDIGO": "Interglobe Avi", "SHRIRAMFIN": "Shriram Finance", "ADANIENT": "Adani Enterpris",
         "MAXHEALTH": "Max Healthcare", "BAJFINANCE": "Bajaj Finance", "TATASTEEL": "Tata Steel",
         "JSWSTEEL": "JSW Steel", "BHARTIARTL": "Bharti Airtel", "HINDALCO": "Hindalco"}

def inr(x, d=2):
    s = f"{abs(x):.{d}f}"; i, _, f = s.partition(".")
    if len(i) > 3:
        head, tail, g = i[:-3], i[-3:], []
        while len(head) > 2: g.insert(0, head[-2:]); head = head[:-2]
        if head: g.insert(0, head)
        i = ",".join(g + [tail])
    return ("-" if x < 0 else "") + i + (f".{f}" if d else "")

def sgn(x, d=2): return ("+" if x >= 0 else "-") + inr(abs(x), d)

def nifty50():
    """Live constituent list from NSE; falls back to local nifty50.csv (same format)."""
    try:
        r = requests.get("https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv",
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        r.raise_for_status(); df = pd.read_csv(io.StringIO(r.text))
    except Exception as e:
        print("NSE list fetch failed, using local nifty50.csv:", e)
        df = pd.read_csv(ROOT / "nifty50.csv")
    return df["Symbol"].str.strip().tolist(), dict(zip(df["Symbol"].str.strip(), df["Company Name"]))

def short(sym, company):
    if sym in NAMES: return NAMES[sym]
    n = company.replace(" Limited", "").replace(" Ltd.", "").replace(" Ltd", "")
    return n if len(n) <= 16 else n[:16].rstrip()

def last2(tickers):
    c = yf.download(tickers, period="10d", interval="1d", auto_adjust=False, progress=False)["Close"]
    c = c.dropna(how="all")
    return c.index[-1].date(), c.iloc[-1], c.iloc[-2]

def main():
    syms, comp = nifty50()
    d, last, prev = last2([s + ".NS" for s in syms])
    if d != NOW.date() and not FORCE:
        print(f"Latest bar is {d}, today is {NOW.date()} -> holiday/no data, skipping."); sys.exit(0)

    rows = []
    for s in syms:
        l, p = last.get(s + ".NS"), prev.get(s + ".NS")
        if pd.isna(l) or pd.isna(p): continue
        rows.append(dict(name=short(s, comp[s]), l=l, c=l - p, p=(l - p) / p * 100))
    fmt = lambda r: dict(name=r["name"], price=inr(r["l"]), chg=sgn(r["c"]), pct=f"{abs(r['p']):.2f}%")
    fmt_l = lambda r: {**fmt(r), "pct": f"{r['p']:.2f}%".replace("-", "−"), "chg": sgn(r["c"]).replace("-", "−")}
    gainers = [fmt(r) for r in sorted([r for r in rows if r["c"] > 0], key=lambda r: -r["p"])[:10]]
    losers = [fmt_l(r) for r in sorted([r for r in rows if r["c"] < 0], key=lambda r: r["p"])[:10]]

    _, il, ip = last2(["^BSESN", "^NSEI"])
    indices = []
    for name, t in (("SENSEX", "^BSESN"), ("NIFTY", "^NSEI")):
        c = il[t] - ip[t]; p = c / ip[t] * 100
        indices.append(dict(name=name, price=inr(il[t]), chg=sgn(c), pct=f"{p:+.2f}%", cls="up" if c >= 0 else "down",
                            arrow="▲" if c >= 0 else "▼"))

    # Footer: USD/INR always; gold/silver only if enabled (see README - verify vs MCX!)
    _, fl, fp = last2(["INR=X", "GC=F", "SI=F"])
    usd = fl["INR=X"]; parts = []
    if os.getenv("ENABLE_COMMODITIES") == "1":
        gp, sp = float(os.getenv("GOLD_PREMIUM", "0")), float(os.getenv("SILVER_PREMIUM", "0"))
        g = fl["GC=F"] * usd / 31.1035 * 10 * (1 + gp); s = fl["SI=F"] * usd / 31.1035 * 1000 * (1 + sp)
        gc = (fl["GC=F"] / fp["GC=F"] - 1) * 100; sc = (fl["SI=F"] / fp["SI=F"] - 1) * 100
        parts += [f"GOLD - {inr(g)} ({gc:.2f}%)", f"SILVER - {inr(s)} ({sc:.2f}%)"]
    parts.append(f"USD/INR - {usd:.3f} ({(usd / fp['INR=X'] - 1) * 100:.2f}%)")

    asset = lambda n: (ROOT / "assets" / n).as_uri() if (ROOT / "assets" / n).exists() else None
    bg = asset("bg.png")
    html = Template((ROOT / "template.html").read_text()).render(
        logo=asset("logo.png"), bull=asset("bull.png"), bear=asset("bear.png"),
        bg_css=f"url('{bg}') center/cover" if bg else "linear-gradient(180deg,#0b1030,#101a4a 60%,#0a0f2c)",
        date_str=NOW.strftime("%d %B %Y").upper(), time_str=NOW.strftime("%I:%M %p"),
        indices=indices, gainers=gainers, losers=losers, footer=" &nbsp;|&nbsp; ".join(parts))
    tmp = ROOT / "_render.html"; tmp.write_text(html, encoding="utf-8")

    out = ROOT / "docs"; out.mkdir(exist_ok=True)
    dated = out / f"market-update-{d.isoformat()}.png"
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 800, "height": 1308}, device_scale_factor=1.5)
        pg.goto(tmp.as_uri()); pg.wait_for_timeout(1500); pg.screenshot(path=str(dated)); b.close()
    (out / "latest.png").write_bytes(dated.read_bytes()); tmp.unlink()
    print("Created", dated)

if __name__ == "__main__":
    main()
