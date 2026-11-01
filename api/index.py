"""
BTCUSD 30m  9 EMA cross alerts -> Telegram (chart photo + full message), on Vercel.

Lines (same as the TradingView chart):
  PURPLE = 9 EMA of close
  BLUE   = 20 EMA of HIGH
  RED    = 20 EMA of LOW

Environment variables (Vercel -> Project -> Settings -> Environment Variables):
  TG_TOKEN     - bot token from @BotFather
  TG_CHAT_IDS  - Telegram chat id(s), comma separated
  WEBHOOK_KEY  - your secret word (protects the URLs below)
  FAST_LEN     - optional, purple EMA length (default 9)
  SLOW_LEN     - optional, EMA High / EMA Low length (default 20)

URLs:
  GET  /cron?key=WEBHOOK_KEY   <- called by cron-job.org after every 30m candle close
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
TF_SEC = 1800          # 30-minute candles
CHART_BARS = 40        # candles shown in the photo
MAX_AGE_SEC = 600      # only alert on a candle that closed in the last 10 minutes

IST = timezone(timedelta(hours=5, minutes=30))
PURPLE, BLUE, RED = "#7B1FA2", "#1E40FF", "#E53935"
LINE_COLOR = {"blue": BLUE, "red": RED}

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.info
app = Flask(__name__)
_seen = set()


# ---------------------------- TELEGRAM ----------------------------
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
    return all(results) and bool(results)


# ----------------------------- CHART -----------------------------
def make_chart(d):
    b = d["bars"]
    n = len(b["c"])
    tf_s = int(d["tf"])
    t_last = int(d["t"]) // 1000
    times = [datetime.fromtimestamp(t_last - (n - 1 - k) * tf_s, tz=IST) for k in range(n)]
    o, h, l, c = list(b["o"]), list(b["h"]), list(b["l"]), list(b["c"])
    fast, blue, red = list(b["fast"]), list(b["blue"]), list(b["red"])
    # exact values for the cross candle
    o[-1], h[-1], l[-1], c[-1] = float(d["o"]), float(d["h"]), float(d["l"]), float(d["c"])
    fast[-1], blue[-1], red[-1] = float(d["fast"]), float(d["blue"]), float(d["red"])

    line, up = d["line"], d["dir"] == "UPWARD"
    color = LINE_COLOR[line]
    y = float(d[line])

    fig, ax = plt.subplots(figsize=(14, 8))
    for i in range(n):
        ax.vlines(i, l[i], h[i], color="black", linewidth=1, zorder=2)
        lo, hi = min(o[i], c[i]), max(o[i], c[i])
        ax.add_patch(Rectangle(
            (i - 0.3, lo), 0.6, max(hi - lo, (max(h) - min(l)) * 0.002),
            facecolor="white" if c[i] >= o[i] else RED, edgecolor="black", linewidth=1, zorder=3,
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
    ax.set_title(
        f"{d.get('ticker', 'BTCUSD')} {tf_s // 60}m  |  9 EMA crossed {line.upper()} line {d['dir']}\n"
        f"Candle {start:%d %b %Y %H:%M}-{end:%H:%M} IST  ({d.get('source', 'TradingView')} data)",
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
    ax.annotate(
        f"CROSS {d['dir']}\n{start:%H:%M} IST\n{y:,.2f}",
        xy=(n - 1, y), xytext=(max(0, n - 12), ty),
        arrowprops=dict(arrowstyle="->", color=color, lw=1.8),
        fontsize=10, color=color, fontweight="bold",
        bbox=dict(boxstyle="round", fc="white", ec=color), zorder=7,
    )

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


# ---------------------------- MESSAGE ----------------------------
def position(d):
    f, b, r = float(d["fast"]), float(d["blue"]), float(d["red"])
    if f > b:
        return "ABOVE both lines (above blue)"
    if f < r:
        return "BELOW both lines (below red)"
    return "BETWEEN blue and red"


def caption(d):
    start = datetime.fromtimestamp(int(d["t"]) / 1000, tz=IST)
    end = start + timedelta(seconds=int(d["tf"]))
    line_name = "BLUE line (20 EMA of HIGH)" if d["line"] == "blue" else "RED line (20 EMA of LOW)"
    up = d["dir"] == "UPWARD"
    return (
        f"🚨 <b>{d.get('ticker', 'BTCUSD')} {int(d['tf']) // 60}m — 9 EMA CROSS</b>\n\n"
        f"<b>9 EMA (purple) has cut the {line_name}</b>\n"
        f"Direction: <b>{d['dir']}</b> {'⬆️' if up else '⬇️'} (9 EMA moved {'above' if up else 'below'} it)\n"
        f"Candle: {start:%d %b %Y}, {start:%H:%M}–{end:%H:%M} IST (closed)\n\n"
        f"Open: {float(d['o']):,.2f}\nHigh: {float(d['h']):,.2f}\n"
        f"Low: {float(d['l']):,.2f}\nClose: {float(d['c']):,.2f}\n\n"
        f"9 EMA (purple): {float(d['fast']):,.2f}\n"
        f"EMA High (blue): {float(d['blue']):,.2f}\n"
        f"EMA Low (red): {float(d['red']):,.2f}\n\n"
        f"Now: 9 EMA is {position(d)}\n"
        f"Data: {d.get('source', 'TradingView')}\n\n"
        f"#BTCUSD #{d['line'].upper()}_{'UP' if up else 'DOWN'}"
    )


def handle_alert(d):
    key = (d.get("t"), d.get("line"), d.get("dir"))
    if key in _seen:
        log(f"Duplicate ignored: {key}")
        return
    _seen.add(key)
    log(f"CROSS {d['line']} {d['dir']} at {d['t']}")
    text = caption(d)
    try:
        photo = make_chart(d)
        if tg("sendPhoto", {"caption": text, "parse_mode": "HTML"}, photo):
            return
    except Exception as e:
        log(f"Chart/photo failed: {e}")
    tg("sendMessage", {"text": text, "parse_mode": "HTML"})  # never lose the alert


# ------------------------- PRICE DATA (no TradingView needed) -------------------------
def fetch_kraken():
    r = requests.get("https://api.kraken.com/0/public/OHLC",
                     params={"pair": "XBTUSD", "interval": TF_SEC // 60}, timeout=15)
    data = r.json()
    if data.get("error"):
        raise RuntimeError(data["error"])
    key = [k for k in data["result"] if k != "last"][0]
    return "Kraken BTC/USD", [
        (int(row[0]), float(row[1]), float(row[2]), float(row[3]), float(row[4]))
        for row in data["result"][key]
    ]


def fetch_bitstamp():
    r = requests.get("https://www.bitstamp.net/api/v2/ohlc/btcusd/",
                     params={"step": TF_SEC, "limit": 720}, timeout=15)
    r.raise_for_status()
    return "Bitstamp BTC/USD", [
        (int(x["timestamp"]), float(x["open"]), float(x["high"]), float(x["low"]), float(x["close"]))
        for x in r.json()["data"]["ohlc"]
    ]


def fetch_closed_candles():
    now = time.time()
    for source in (fetch_kraken, fetch_bitstamp):
        try:
            name, rows = source()
            rows = sorted(r for r in rows if r[0] + TF_SEC <= now)  # closed candles only
            if len(rows) > SLOW_LEN * 10:
                return name, rows
            log(f"{name}: not enough candles ({len(rows)})")
        except Exception as e:
            log(f"Data error from {source.__name__}: {e}")
    raise RuntimeError("No price data from Kraken or Bitstamp")


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


def run_scheduled_check():
    source, rows = fetch_closed_candles()
    t = [r[0] for r in rows]
    o = [r[1] for r in rows]
    h = [r[2] for r in rows]
    l = [r[3] for r in rows]
    c = [r[4] for r in rows]
    fast, blue, red = ema(c, FAST_LEN), ema(h, SLOW_LEN), ema(l, SLOW_LEN)
    i = len(rows) - 1

    start = datetime.fromtimestamp(t[i], tz=IST)
    status = (f"{source} | candle {start:%d %b %H:%M} IST | close {c[i]:,.2f} | "
              f"9EMA {fast[i]:,.2f} | blue {blue[i]:,.2f} | red {red[i]:,.2f}")
    log(status)

    age = time.time() - (t[i] + TF_SEC)
    if age > MAX_AGE_SEC:
        return status + " | no alert (candle closed more than 10 min ago)"

    sent = []
    for line, arr in (("blue", blue), ("red", red)):
        if fast[i - 1] <= arr[i - 1] and fast[i] > arr[i]:
            direction = "UPWARD"
        elif fast[i - 1] >= arr[i - 1] and fast[i] < arr[i]:
            direction = "DOWNWARD"
        else:
            continue
        a = max(0, len(rows) - CHART_BARS)
        rnd = lambda xs: [round(x, 2) for x in xs[a:]]
        handle_alert({
            "source": source, "ticker": "BTCUSD", "tf": TF_SEC, "t": t[i] * 1000,
            "line": line, "dir": direction,
            "o": o[i], "h": h[i], "l": l[i], "c": c[i],
            "fast": fast[i], "blue": blue[i], "red": red[i],
            "bars": {"o": rnd(o), "h": rnd(h), "l": rnd(l), "c": rnd(c),
                     "fast": rnd(fast), "blue": rnd(blue), "red": rnd(red)},
        })
        sent.append(f"{line.upper()} {direction}")

    return status + (" | ALERT SENT: " + ", ".join(sent) if sent else " | no cross")


# ----------------------------- ROUTES -----------------------------
@app.route("/", defaults={"path": ""}, methods=["GET", "POST"])
@app.route("/<path:path>", methods=["GET", "POST"])
def router(path):
    path = path.strip("/")

    if request.method == "POST":
        try:
            d = json.loads(request.get_data(as_text=True))
        except Exception:
            return "bad json", 400
        if not WEBHOOK_KEY or d.get("key") != WEBHOOK_KEY:
            log("Rejected: wrong webhook key")
            return "forbidden", 403
        handle_alert(d)
        return "ok", 200

    if path.endswith("cron"):
        if not WEBHOOK_KEY or request.args.get("key") != WEBHOOK_KEY:
            return "Wrong or missing key", 403
        try:
            return run_scheduled_check(), 200
        except Exception as e:
            log(f"Scheduled check failed: {e}")
            return f"error: {e}", 500

    if path.endswith("check"):
        if not WEBHOOK_KEY or request.args.get("key") != WEBHOOK_KEY:
            return "Wrong or missing key", 403
        ok = tg("sendMessage", {"text": "✅ BTC 9 EMA alert server is connected to this Telegram chat."})
        return ("Telegram OK — message sent." if ok else
                "Telegram FAILED — check TG_TOKEN and TG_CHAT_IDS, and that you pressed Start in your bot."), 200

    return (
        "BTC 9 EMA alert server is running.<br>"
        f"TG_TOKEN set: {'yes' if TG_TOKEN else 'NO'}<br>"
        f"Chat ids set: {len(TG_CHAT_IDS)}<br>"
        f"WEBHOOK_KEY set: {'yes' if WEBHOOK_KEY else 'NO'}"
    ), 200
