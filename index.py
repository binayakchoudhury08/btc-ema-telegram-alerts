"""
TradingView webhook -> Telegram (chart photo + full message), running on Vercel.

Environment variables (Vercel -> Project -> Settings -> Environment Variables):
  TG_TOKEN     - bot token from @BotFather
  TG_CHAT_IDS  - your Telegram chat id (several allowed, comma separated)
  WEBHOOK_KEY  - the same secret word you typed in the Pine indicator

URLs:
  POST /tv                     <- TradingView webhook
  GET  /                       <- status page
  GET  /check?key=WEBHOOK_KEY  <- sends a "connected" message to Telegram
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
        f"Candle {start:%d %b %Y %H:%M}-{end:%H:%M} IST  (TradingView data)",
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
        f"Now: 9 EMA is {position(d)}\n\n"
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
