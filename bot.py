"""
Bot de semnale CRYPTO + FOREX (nu execută ordine, doar îți spune intrarea / ieșirea).
Funcționează doar cu Python standard (fără pip) - ideal pentru iPhone.

Strategie: breakout Donchian cu filtru de trend
  - LONG : închiderea depășește maximul ultimelor 20 de lumânări ȘI prețul e peste EMA100
  - SHORT: invers (doar forex; crypto spot nu se poate vinde în lipsă)
  - Stop-loss: 2 x ATR | Take-profit: 3 x ATR
  - Forex: semnale doar în sesiunea Londra/New York (07:00-17:00 UTC)

Rulare:
  python3 trading_bot_crypto_forex.py crypto BTCUSDT ETHUSDT
  python3 trading_bot_crypto_forex.py forex EURUSD GBPUSD USDJPY
"""
import sys
import json
import urllib.request
from datetime import datetime, timezone

CRYPTO = {"interval": "4h", "fee": 0.001, "short": False, "session": None}
FOREX = {"interval": "1h", "fee": 0.0002, "short": True, "session": (7, 17)}
DONCHIAN, EMA_N, SL_ATR, TP_ATR, WARMUP = 20, 100, 2.0, 3.0, 150


def http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def fetch_crypto(sym, interval):
    url = f"https://data-api.binance.vision/api/v3/klines?symbol={sym}&interval={interval}&limit=1000"
    return [(int(k[0]) // 1000, float(k[1]), float(k[2]), float(k[3]), float(k[4]))
            for k in http_json(url)]


def fetch_forex(pair, interval):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{pair}=X?interval={interval}&range=1y"
    r = http_json(url)["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    bars = []
    for t, o, h, l, c in zip(r["timestamp"], q["open"], q["high"], q["low"], q["close"]):
        if None not in (o, h, l, c):
            bars.append((t, o, h, l, c))
    return bars


def ema(vals, n):
    k, out = 2 / (n + 1), [vals[0]]
    for v in vals[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def atr(bars, n=14):
    trs = [bars[0][2] - bars[0][3]]
    for i in range(1, len(bars)):
        h, l, pc = bars[i][2], bars[i][3], bars[i - 1][4]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    out = [trs[0]]
    for tr in trs[1:]:
        out.append((out[-1] * (n - 1) + tr) / n)
    return out


def signal(bars, e, i, cfg):
    if i < WARMUP:
        return None
    if cfg["session"]:
        hr = datetime.fromtimestamp(bars[i][0], timezone.utc).hour
        if not cfg["session"][0] <= hr < cfg["session"][1]:
            return None
    c = bars[i][4]
    hi = max(b[2] for b in bars[i - DONCHIAN:i])
    lo = min(b[3] for b in bars[i - DONCHIAN:i])
    if c > hi and c > e[i]:
        return "LONG"
    if cfg["short"] and c < lo and c < e[i]:
        return "SHORT"
    return None


def levels(side, entry, a):
    if side == "LONG":
        return entry - SL_ATR * a, entry + TP_ATR * a
    return entry + SL_ATR * a, entry - TP_ATR * a


def backtest(bars, e, a, cfg):
    res, i = [], WARMUP
    while i < len(bars) - 1:
        side = signal(bars, e, i, cfg)
        if not side:
            i += 1
            continue
        entry = bars[i][4]
        sl, tp = levels(side, entry, a[i])
        exit_p, j = bars[-1][4], i + 1
        while j < len(bars):
            h, l = bars[j][2], bars[j][3]
            if side == "LONG":
                if l <= sl:
                    exit_p = sl
                    break
                if h >= tp:
                    exit_p = tp
                    break
            else:
                if h >= sl:
                    exit_p = sl
                    break
                if l <= tp:
                    exit_p = tp
                    break
            j += 1
        ret = (exit_p - entry) / entry if side == "LONG" else (entry - exit_p) / entry
        res.append(ret - 2 * cfg["fee"])
        i = j + 1
    return res


def analyze(market, name):
    cfg = CRYPTO if market == "crypto" else FOREX
    try:
        bars = (fetch_crypto(name, cfg["interval"]) if market == "crypto"
                else fetch_forex(name, cfg["interval"]))
    except Exception as ex:
        print(f"\n{name}: nu am putut descărca datele ({ex})")
        return
    if len(bars) < WARMUP + 50:
        print(f"\n{name}: date insuficiente")
        return
    e, a = ema([b[4] for b in bars], EMA_N), atr(bars)
    last = len(bars) - 1
    price = bars[last][4]
    when = datetime.fromtimestamp(bars[last][0], timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"\n=== {name} ({cfg['interval']}) | preț {price:.6g} | lumânare {when} ===")

    side = signal(bars, e, last, cfg)
    if side:
        sl, tp = levels(side, price, a[last])
        print(f"SEMNAL: {'CUMPĂRĂ' if side == 'LONG' else 'VINDE'}")
        print(f"  Intrare:     {price:.6g}")
        print(f"  Stop-loss:   {sl:.6g}")
        print(f"  Take-profit: {tp:.6g}")
    else:
        print("Niciun semnal acum. Așteaptă.")

    t = backtest(bars, e, a, cfg)
    if t:
        w = sum(1 for x in t if x > 0)
        print(f"Backtest: {len(t)} tranzacții | câștigătoare {w / len(t):.0%} "
              f"| medie {sum(t) / len(t):.2%} | total {sum(t):.1%} (după comisioane)")


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("crypto", "forex"):
        print("Folosire: python3 trading_bot_crypto_forex.py crypto BTCUSDT ETHUSDT")
        print("          python3 trading_bot_crypto_forex.py forex EURUSD GBPUSD")
        sys.exit(1)
    for n in sys.argv[2:]:
        analyze(sys.argv[1], n.upper())
    print("\nAtenție: nu este sfat financiar. Rezultatele trecute nu garantează profit.")
