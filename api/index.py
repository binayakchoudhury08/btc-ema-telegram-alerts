"""
BTCUSD 30m  9 EMA cross alerts -> Telegram, in TWO STAGES, running on Vercel.

Lines (same as the TradingView chart):
  PURPLE = 9 EMA of close
  BLUE   = 20 EMA of HIGH
  RED    = 20 EMA of LOW

Stage 1  ⚠️ EARLY SIGNAL   - the live 9 EMA crosses blue/red while the 30m candle
                             is still open (checked every minute). Chart photo included.
Stage 2  ✅ CONFIRMED       - the cross is still there when the candle closes.
                             Full message + chart photo.
         ❌ CANCELLED       - there was an early signal, but the 9 EMA moved back
                             before the candle closed.

cron-job.org calls  GET /cron?key=WEBHOOK_KEY  EVERY MINUTE.

Environment variables (Vercel -> Settings -> Environment Variables):
  TG_TOKEN     - bot token from @BotFather
  TG_CHAT_IDS  - Telegram chat id(s), comma separated
  WEBHOOK_KEY  - your secret word (protects the URLs)
  FAST_LEN     - optional, purple EMA length (default 9)
  SLOW_LEN     - optional, EMA High / EMA Low length (default 20)

URLs:
  GET  /cron?key=WEBHOOK_KEY   <- called by cron-job.org every minute

Price data: average of Coinbase, Kraken, Bitstamp and Bitfinex BTC/USD, rebuilt the
same way TradingView builds CRYPTO:BTCUSD (arithmetic average of exchanges).
  GET  /check?key=WEBHOOK_KEY  <- sends a "connected" message to Telegram
  GET  /                       <- status page
  POST /tv                     <- optional TradingView webhook (needs TradingView 2FA)
"""

import os
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")  # Vercel: only /tmp is writable

import io
import json
import time
import logging
from datetime import datetime, timezone, timedelta

import requests
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
from flask import Flask, request

TG_TOKEN = os.environ.get("TG_TOKEN", "").strip()
TG_CHAT_IDS = [c.strip() for c in os.environ.get("TG_CHAT_IDS", "").split(",") if c.strip()]
WEBHOOK_KEY = os.environ.get("WEBHOOK_KEY", "").strip()
FAST_LEN = int(os.environ.get("FAST_LEN", "9"))
SLOW_LEN = int(os.environ.get("SLOW_LEN", "20"))

TF_SEC = 1800       # 30-minute candles
CHART_BARS = 40     # candles shown in the photo
IST = timezone(timedelta(hours=5, minutes=30))
PURPLE, BLUE, RED = "#7B1FA2", "#1E40FF", "#E53935"
LINE_COLOR = {"blue": BLUE, "red": RED}
LINE_NAME = {"blue": "BLUE line (20 EMA of HIGH)", "red": "RED line (20 EMA of LOW)"}

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.info
app = Flask(__name__)
_seen = set()


def ist(ts):
    return datetime.fromtimestamp(ts, tz=IST)


def sgn(x):
    return 1 if x > 0 else -1 if x < 0 else 0


def tag(line, direction):
    return f"#{line.upper()}_{'UP' if direction == 'UPWARD' else 'DOWN'}"


# ============================== TELEGRAM ==============================
def tg(method, data, photo_bytes=None):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/{method}"
    results = []
    for chat in TG_CHAT_IDS:
        ok = False
        for attempt in range(1, 4):
            try:
                files = {"photo": ("cross.png", photo_bytes, "image/png")} if photo_bytes else None
                r = requests.post(url, data={**data, "chat_id": chat}, files=files, timeout=20)
                if r.ok:
                    ok = True
                    log(f"Telegram {method} -> {chat} OK")
                    break
                log(f"Telegram error {r.status_code}: {r.text}")
                if r.status_code in (400, 401, 403, 404):
                    break  # wrong token / chat id: retrying will not help
            except Exception as e:
                log(f"Telegram send failed (try {attempt}/3): {e}")
            time.sleep(1.5 * attempt)
        results.append(ok)
    return bool(results) and all(results)


# ================================ CHART ================================
def make_chart(d):
    b = d["bars"]
    n = len(b["c"])
    tf_s = int(d["tf"])
    t_last = int(d["t"]) // 1000
    times = [ist(t_last - (n - 1 - k) * tf_s) for k in range(n)]
    o, h, l, c = list(b["o"]), list(b["h"]), list(b["l"]), list(b["c"])
    fast, blue, red = list(b["fast"]), list(b["blue"]), list(b["red"])
    o[-1], h[-1], l[-1], c[-1] = float(d["o"]), float(d["h"]), float(d["l"]), float(d["c"])
    fast[-1], blue[-1], red[-1] = float(d["fast"]), float(d["blue"]), float(d["red"])

    early = d.get("stage") == "EARLY"
    line, up = d["line"], d["dir"] == "UPWARD"
    color = LINE_COLOR[line]
    y = float(d[line])

    fig, ax = plt.subplots(figsize=(14, 8))
    rng_all = max(h) - min(l)
    for i in range(n):
        live_bar = early and i == n - 1
        ax.vlines(i, l[i], h[i], color="black", linewidth=1, zorder=2)
        lo, hi = min(o[i], c[i]), max(o[i], c[i])
        ax.add_patch(Rectangle(
            (i - 0.3, lo), 0.6, max(hi - lo, rng_all * 0.002),
            facecolor="white" if c[i] >= o[i] else RED, edgecolor="black",
            linewidth=1.4 if live_bar else 1, linestyle="--" if live_bar else "-",
            alpha=0.7 if live_bar else 1, zorder=3,
        ))
    x = list(range(n))
    ax.plot(x, fast, color=PURPLE, linewidth=2, zorder=4)
    ax.plot(x, blue, color=BLUE, linewidth=2, zorder=4)
    ax.plot(x, red, color=RED, linewidth=2, zorder=4)
    ax.axvline(n - 1, color=color, linestyle="--", linewidth=1, alpha=0.6, zorder=1)
    ax.scatter([n - 1], [y], s=350, color=color, marker="^" if up else "v", zorder=6)

    lo_y = min(min(l), min(red), min(fast))
    hi_y = max(max(h), max(blue), max(fast))
    pad = (hi_y - lo_y) * 0.08
    ax.set_ylim(lo_y - pad, hi_y + pad)
    ax.set_xlim(-1, n + 1)

    step = max(1, n // 8)
    ticks = list(range(n - 1, -1, -step))[::-1]
    ax.set_xticks(ticks)
    ax.set_xticklabels([times[i].strftime("%d %b\n%H:%M") for i in ticks], fontsize=9)
    ax.yaxis.tick_right()
    ax.yaxis.set_label_position("right")
    ax.set_ylabel("USD")
    ax.grid(True, linestyle=":", alpha=0.7)

    start = times[-1]
    end = start + timedelta(seconds=tf_s)
    stage_txt = "EARLY SIGNAL (candle still open)" if early else "CONFIRMED (candle closed)"
    ax.set_title(
        f"{d.get('ticker', 'BTCUSD')} {tf_s // 60}m  |  {stage_txt}  |  9 EMA crossed {line.upper()} {d['dir']}\n"
        f"Candle {start:%d %b %Y %H:%M}-{end:%H:%M} IST  |  {d.get('source', 'TradingView')} data",
        fontsize=13,
    )
    ax.legend(handles=[
        Line2D([], [], color=PURPLE, lw=2, label=f"9 EMA (purple)  {float(d['fast']):,.2f}"),
        Line2D([], [], color=BLUE, lw=2, label=f"EMA High (blue)  {float(d['blue']):,.2f}"),
        Line2D([], [], color=RED, lw=2, label=f"EMA Low (red)  {float(d['red']):,.2f}"),
    ], loc="upper left", fontsize=10, framealpha=0.9)

    ylo, yhi = ax.get_ylim()
    ty = y + (0.18 if up else -0.18) * (yhi - ylo)
    ty = min(max(ty, ylo + 0.12 * (yhi - ylo)), yhi - 0.12 * (yhi - ylo))
    label_time = d.get("seen") or f"{start:%H:%M}"
    ax.annotate(
        f"{'EARLY CROSS' if early else 'CROSS'} {d['dir']}\n{label_time} IST\n{y:,.2f}",
        xy=(n - 1, y), xytext=(max(0, n - 12), ty),
        arrowprops=dict(arrowstyle="->", color=color, lw=1.8),
        fontsize=10, color=color, fontweight="bold",
        bbox=dict(boxstyle="round", fc="white", ec=color), zorder=7,
    )

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


# =============================== MESSAGES ===============================
def position(d):
    f, b, r = float(d["fast"]), float(d["blue"]), float(d["red"])
    if f > b:
        return "ABOVE both lines (above blue)"
    if f < r:
        return "BELOW both lines (below red)"
    return "BETWEEN blue and red"


def caption_early(d):
    start = ist(int(d["t"]) // 1000)
    end = start + timedelta(seconds=int(d["tf"]))
    up = d["dir"] == "UPWARD"
    return (
        f"⚠️ <b>EARLY SIGNAL — not confirmed yet</b>\n"
        f"<b>{d.get('ticker', 'BTCUSD')} {int(d['tf']) // 60}m</b>\n\n"
        f"<b>9 EMA (purple) is crossing the {LINE_NAME[d['line']]}</b>\n"
        f"Direction: <b>{d['dir']}</b> {'⬆️' if up else '⬇️'}\n"
        f"Seen at: {d['seen']} IST\n"
        f"Candle: {start:%d %b %Y}, {start:%H:%M}–{end:%H:%M} IST (still open)\n\n"
        f"Price now: {float(d['c']):,.2f}\n"
        f"Candle so far: O {float(d['o']):,.2f} | H {float(d['h']):,.2f} | L {float(d['l']):,.2f}\n\n"
        f"9 EMA (live): {float(d['fast']):,.2f}\n"
        f"EMA High (live): {float(d['blue']):,.2f}\n"
        f"EMA Low (live): {float(d['red']):,.2f}\n\n"
        f"⏳ Confirmation at the {end:%H:%M} IST candle close.\n"
        f"Data: {d.get('source', 'TradingView')}\n\n"
        f"#BTCUSD #EARLY {tag(d['line'], d['dir'])}"
    )


def caption_confirmed(d):
    start = ist(int(d["t"]) // 1000)
    end = start + timedelta(seconds=int(d["tf"]))
    up = d["dir"] == "UPWARD"
    early_line = f"Early signal: {d['early_info']}\n" if d.get("early_info") else ""
    return (
        f"✅ <b>CONFIRMED — {d.get('ticker', 'BTCUSD')} {int(d['tf']) // 60}m 9 EMA CROSS</b>\n\n"
        f"<b>9 EMA (purple) has cut the {LINE_NAME[d['line']]}</b>\n"
        f"Direction: <b>{d['dir']}</b> {'⬆️' if up else '⬇️'} (9 EMA moved {'above' if up else 'below'} it)\n"
        f"Candle: {start:%d %b %Y}, {start:%H:%M}–{end:%H:%M} IST (closed)\n"
        f"{early_line}\n"
        f"Open: {float(d['o']):,.2f}\nHigh: {float(d['h']):,.2f}\n"
        f"Low: {float(d['l']):,.2f}\nClose: {float(d['c']):,.2f}\n\n"
        f"9 EMA (purple): {float(d['fast']):,.2f}\n"
        f"EMA High (blue): {float(d['blue']):,.2f}\n"
        f"EMA Low (red): {float(d['red']):,.2f}\n\n"
        f"Now: 9 EMA is {position(d)}\n"
        f"Data: {d.get('source', 'TradingView')}\n\n"
        f"#BTCUSD #CONFIRMED {tag(d['line'], d['dir'])}"
    )


def handle_alert(d):
    stage = d.get("stage", "CONFIRMED")
    key = (d.get("t"), d.get("line"), d.get("dir"), stage)
    if key in _seen:
        log(f"Duplicate ignored: {key}")
        return
    _seen.add(key)
    log(f"{stage}: {d['line']} {d['dir']} candle {d['t']}")
    text = caption_early(d) if stage == "EARLY" else caption_confirmed(d)
    try:
        if tg("sendPhoto", {"caption": text, "parse_mode": "HTML"}, make_chart(d)):
            return
    except Exception as e:
        log(f"Chart/photo failed: {e}")
    tg("sendMessage", {"text": text, "parse_mode": "HTML"})  # never lose the alert


def send_cancelled(source, line, direction, candle_start, seen_ts, close, fast, line_val):
    end = ist(candle_start + TF_SEC)
    text = (
        f"❌ <b>CANCELLED — early signal not confirmed</b>\n"
        f"<b>BTCUSD 30m</b>\n\n"
        f"The 9 EMA crossed the {LINE_NAME[line]} <b>{direction}</b> at {ist(seen_ts):%H:%M} IST,\n"
        f"but moved back before the {end:%H:%M} IST candle close.\n"
        f"No cross on this candle.\n\n"
        f"Close: {close:,.2f}\n"
        f"9 EMA (purple): {fast:,.2f}\n"
        f"{'EMA High (blue)' if line == 'blue' else 'EMA Low (red)'}: {line_val:,.2f}\n"
        f"Data: {source}\n\n"
        f"#BTCUSD #CANCELLED {tag(line, direction)}"
    )
    log(f"CANCELLED: {line} {direction}")
    tg("sendMessage", {"text": text, "parse_mode": "HTML"})


# ============================== PRICE DATA ==============================
HEADERS = {"User-Agent": "btc-ema-alert-bot/1.0"}


def kraken(minutes):
    r = requests.get("https://api.kraken.com/0/public/OHLC",
                     params={"pair": "XBTUSD", "interval": minutes}, headers=HEADERS, timeout=10)
    data = r.json()
    if data.get("error"):
        raise RuntimeError(data["error"])
    key = [k for k in data["result"] if k != "last"][0]
    return [(int(x[0]), float(x[1]), float(x[2]), float(x[3]), float(x[4])) for x in data["result"][key]]


def bitstamp(minutes):
    r = requests.get("https://www.bitstamp.net/api/v2/ohlc/btcusd/",
                     params={"step": minutes * 60, "limit": 1000}, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return [(int(x["timestamp"]), float(x["open"]), float(x["high"]), float(x["low"]), float(x["close"]))
            for x in r.json()["data"]["ohlc"]]


def bitfinex(minutes):
    r = requests.get(f"https://api-pub.bitfinex.com/v2/candles/trade:{minutes}m:tBTCUSD/hist",
                     params={"limit": 1000}, headers=HEADERS, timeout=10)
    r.raise_for_status()
    # [MTS, OPEN, CLOSE, HIGH, LOW, VOLUME]
    return [(int(x[0]) // 1000, float(x[1]), float(x[3]), float(x[4]), float(x[2])) for x in r.json()]


def coinbase(minutes):
    # Coinbase has no 30m candles: build them from two 15m candles
    gran = 60 if minutes == 1 else 900
    r = requests.get("https://api.exchange.coinbase.com/products/BTC-USD/candles",
                     params={"granularity": gran}, headers=HEADERS, timeout=10)
    r.raise_for_status()
    # [time, low, high, open, close, volume]
    rows = sorted((int(x[0]), float(x[3]), float(x[2]), float(x[1]), float(x[4])) for x in r.json())
    if minutes == 1:
        return rows
    buckets = {}
    for t, o, h, l, c in rows:
        buckets.setdefault(t // TF_SEC * TF_SEC, []).append((t, o, h, l, c))
    out = []
    for bt, parts in buckets.items():
        if len(parts) != 2:
            continue  # incomplete 30m bucket
        parts.sort()
        out.append((bt, parts[0][1], max(p[2] for p in parts), min(p[3] for p in parts), parts[1][4]))
    return out


EXCHANGES = {"Coinbase": coinbase, "Kraken": kraken, "Bitstamp": bitstamp, "Bitfinex": bitfinex}


def average_rows(per_exchange):
    """Average OHLC of all exchanges per candle time, like TradingView's CRYPTO:BTCUSD
    (arithmetic average; an exchange whose price is far from the others is left out)."""
    by_time = {}
    for rows in per_exchange.values():
        for r in rows:
            by_time.setdefault(r[0], []).append(r)
    out = []
    for t in sorted(by_time):
        rs = by_time[t]
        closes = sorted(r[4] for r in rs)
        med = closes[len(closes) // 2]
        rs = [r for r in rs if abs(r[4] - med) / med < 0.01] or rs
        n = len(rs)
        out.append((t, sum(r[1] for r in rs) / n, sum(r[2] for r in rs) / n,
                    sum(r[3] for r in rs) / n, sum(r[4] for r in rs) / n))
    return out


def fetch_all():
    """30m + 1m candles averaged over Coinbase, Kraken, Bitstamp and Bitfinex
    (the main BTC/USD exchanges behind TradingView's CRYPTO:BTCUSD average)."""
    from concurrent.futures import ThreadPoolExecutor
    jobs = {(name, m): None for name in EXCHANGES for m in (30, 1)}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {key: pool.submit(EXCHANGES[key[0]], key[1]) for key in jobs}
        for key, fut in futures.items():
            try:
                jobs[key] = fut.result()
            except Exception as e:
                log(f"Data error from {key[0]} ({key[1]}m): {e}")
    ok = [name for name in EXCHANGES if jobs[(name, 30)] and jobs[(name, 1)]]
    if not ok:
        raise RuntimeError("No price data from any exchange")
    label = f"Average of {', '.join(ok)}"
    return (label,
            average_rows({n: jobs[(n, 30)] for n in ok}),
            average_rows({n: jobs[(n, 1)] for n in ok}))


def ema(values, length):
    """Same as TradingView ta.ema: starts with an SMA, then exponential smoothing."""
    out = [None] * len(values)
    if len(values) < length:
        return out
    k = 2 / (length + 1)
    v = sum(values[:length]) / length
    out[length - 1] = v
    for i in range(length, len(values)):
        v = values[i] * k + v * (1 - k)
        out[i] = v
    return out


def live_values(base, part):
    """9 EMA / EMA High / EMA Low as they are right now on the still-open candle."""
    kf, ks = 2 / (FAST_LEN + 1), 2 / (SLOW_LEN + 1)
    o, h, l, c = part[0][1], max(r[2] for r in part), min(r[3] for r in part), part[-1][4]
    f0, b0, r0 = base
    return (o, h, l, c), (f0 + (c - f0) * kf, b0 + (h - b0) * ks, r0 + (l - r0) * ks)


def first_flips(period_start, minutes, r1, base, base_side):
    """For each line: the FIRST minute j (1..minutes) of the candle in which the
    live 9 EMA was on the other side of that line."""
    mins = [r for r in r1 if period_start <= r[0] < period_start + minutes * 60]
    flips = {}
    for j in range(1, minutes + 1):
        part = [r for r in mins if r[0] < period_start + j * 60]
        if not part:
            continue
        ohlc, (f, b, rd) = live_values(base, part)
        for line, v in (("blue", b), ("red", rd)):
            s = sgn(f - v)
            if line not in flips and s != 0 and base_side[line] != 0 and s != base_side[line]:
                flips[line] = {"j": j, "ohlc": ohlc, "vals": (f, b, rd)}
    return flips


def rnd(xs):
    return [round(float(x), 2) for x in xs]


# =========================== THE CHECK (every minute) ===========================
def run_scheduled_check(now=None):
    fixed = now is not None
    for attempt in range(4):
        now_ts = now if fixed else time.time()
        source, r30, r1 = fetch_all()
        p0 = int(now_ts // TF_SEC) * TF_SEC          # start of the candle that is open now
        k = int((now_ts - p0) // 60)                 # minutes of it that are finished
        closed = [r for r in r30 if r[0] < p0]
        candle_ready = bool(closed) and closed[-1][0] == p0 - TF_SEC
        minute_ready = any(r[0] >= p0 + k * 60 for r in r1) or now_ts - (p0 + k * 60) > 20
        if (candle_ready and minute_ready) or fixed:
            break
        log("Exchange data not updated yet, waiting 4 s")
        time.sleep(4)
    if not candle_ready:
        raise RuntimeError("30m candle data not updated yet")
    if len(closed) < SLOW_LEN * 10:
        raise RuntimeError(f"Not enough candles ({len(closed)})")

    t = [r[0] for r in closed]
    o = [r[1] for r in closed]
    h = [r[2] for r in closed]
    l = [r[3] for r in closed]
    c = [r[4] for r in closed]
    fast, blue, red = ema(c, FAST_LEN), ema(h, SLOW_LEN), ema(l, SLOW_LEN)
    lines = {"blue": blue, "red": red}
    i = len(closed) - 1
    out = []

    # ---------- candle just closed (first minute of a new candle): CONFIRM or CANCEL ----------
    if k == 0:
        cs = t[i]
        base = (fast[i - 1], blue[i - 1], red[i - 1])
        base_side = {ln: sgn(fast[i - 1] - arr[i - 1]) for ln, arr in lines.items()}
        flips = first_flips(cs, TF_SEC // 60 - 1, r1, base, base_side)
        status = (f"{source} | CLOSE CHECK candle {ist(cs):%d %b %H:%M} IST | close {c[i]:,.2f} | "
                  f"9EMA {fast[i]:,.2f} | blue {blue[i]:,.2f} | red {red[i]:,.2f}")
        for ln, arr in lines.items():
            s_prev, s_now = base_side[ln], sgn(fast[i] - arr[i])
            if s_prev != 0 and s_now != 0 and s_now != s_prev:
                direction = "UPWARD" if s_now > 0 else "DOWNWARD"
                fl = flips.get(ln)
                early_info = (f"sent at {ist(cs + fl['j'] * 60):%H:%M} IST" if fl
                              else "none (the cross happened in the last minute of the candle)")
                a = max(0, len(closed) - CHART_BARS)
                handle_alert({
                    "stage": "CONFIRMED", "source": source, "ticker": "BTCUSD", "tf": TF_SEC,
                    "t": cs * 1000, "line": ln, "dir": direction, "early_info": early_info,
                    "o": o[i], "h": h[i], "l": l[i], "c": c[i],
                    "fast": fast[i], "blue": blue[i], "red": red[i],
                    "bars": {"o": rnd(o[a:]), "h": rnd(h[a:]), "l": rnd(l[a:]), "c": rnd(c[a:]),
                             "fast": rnd(fast[a:]), "blue": rnd(blue[a:]), "red": rnd(red[a:])},
                })
                out.append(f"CONFIRMED {ln.upper()} {direction}")
            elif ln in flips:
                direction = "UPWARD" if -s_prev > 0 else "DOWNWARD"
                send_cancelled(source, ln, direction, cs, cs + flips[ln]["j"] * 60,
                               c[i], fast[i], arr[i])
                out.append(f"CANCELLED {ln.upper()} {direction}")
        log(status)
        return status + (" | " + ", ".join(out) if out else " | no cross")

    # ---------- candle still open: EARLY signal ----------
    base = (fast[i], blue[i], red[i])
    base_side = {ln: sgn(fast[i] - arr[i]) for ln, arr in lines.items()}
    flips = first_flips(p0, k, r1, base, base_side)
    part = [r for r in r1 if p0 <= r[0] < p0 + k * 60]
    if part:
        (po, ph, pl, pc), (lf, lb, lr) = live_values(base, part)
        status = (f"{source} | LIVE candle {ist(p0):%d %b %H:%M} IST, minute {k} | price {pc:,.2f} | "
                  f"9EMA {lf:,.2f} | blue {lb:,.2f} | red {lr:,.2f}")
    else:
        status = f"{source} | LIVE candle {ist(p0):%d %b %H:%M} IST, minute {k} | no trades yet"

    for ln, fl in flips.items():
        if fl["j"] != k:
            continue  # early signal for this line was already sent in an earlier minute
        (po, ph, pl, pc), (lf, lb, lr) = fl["ohlc"], fl["vals"]
        direction = "UPWARD" if -base_side[ln] > 0 else "DOWNWARD"
        a = max(0, len(closed) - (CHART_BARS - 1))
        handle_alert({
            "stage": "EARLY", "source": source, "ticker": "BTCUSD", "tf": TF_SEC,
            "t": p0 * 1000, "line": ln, "dir": direction, "seen": f"{ist(p0 + k * 60):%H:%M}",
            "o": po, "h": ph, "l": pl, "c": pc, "fast": lf, "blue": lb, "red": lr,
            "bars": {"o": rnd(o[a:] + [po]), "h": rnd(h[a:] + [ph]), "l": rnd(l[a:] + [pl]),
                     "c": rnd(c[a:] + [pc]), "fast": rnd(fast[a:] + [lf]),
                     "blue": rnd(blue[a:] + [lb]), "red": rnd(red[a:] + [lr])},
        })
        out.append(f"EARLY {ln.upper()} {direction}")
    log(status)
    return status + (" | " + ", ".join(out) if out else " | no new cross")


# ================================ ROUTES ================================
@app.route("/", defaults={"path": ""}, methods=["GET", "POST"])
@app.route("/<path:path>", methods=["GET", "POST"])
def router(path):
    path = path.strip("/")

    if request.method == "POST":  # optional TradingView webhook
        try:
            d = json.loads(request.get_data(as_text=True))
        except Exception:
            return "bad json", 400
        if not WEBHOOK_KEY or d.get("key") != WEBHOOK_KEY:
            log("Rejected: wrong webhook key")
            return "forbidden", 403
        d.setdefault("stage", "CONFIRMED")
        handle_alert(d)
        return "ok", 200

    if path.endswith("cron"):
        if not WEBHOOK_KEY or request.args.get("key") != WEBHOOK_KEY:
            return "Wrong or missing key", 403
        try:
            return run_scheduled_check(), 200
        except Exception as e:
            log(f"Check failed: {e}")
            return f"error: {e}", 500

    if path.endswith("check"):
        if not WEBHOOK_KEY or request.args.get("key") != WEBHOOK_KEY:
            return "Wrong or missing key", 403
        ok = tg("sendMessage", {"text": "✅ BTC 9 EMA alert server is connected to this Telegram chat."})
        return ("Telegram OK — message sent." if ok else
                "Telegram FAILED — check TG_TOKEN and TG_CHAT_IDS, and that you pressed Start in your bot."), 200

    return (
        "BTC 9 EMA alert server is running (2-stage: early + confirmed).<br>"
        f"TG_TOKEN set: {'yes' if TG_TOKEN else 'NO'}<br>"
        f"Chat ids set: {len(TG_CHAT_IDS)}<br>"
        f"WEBHOOK_KEY set: {'yes' if WEBHOOK_KEY else 'NO'}"
    ), 200
