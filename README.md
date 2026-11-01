# BTCUSD 9 EMA Cross Alerts → Telegram (2-stage)

Telegram alerts when the **purple 9 EMA** crosses the **blue EMA High** or the
**red EMA Low** on **BTCUSD 30-minute** candles, upward or downward.

**Exact CRYPTO:BTCUSD numbers:** TradingView detects the cross on its own data and
sends the alert by **email** (no webhook, so no 2-factor authentication needed).
A free Google script forwards the email to the server, which posts to Telegram.

👉 **Setup instructions: open `SETUP-STEP-BY-STEP.md`**

## The two stages

| Stage | When | What you get |
|---|---|---|
| 🟡 **LINES TOUCHING** | Usually under 1 minute after the live 9 EMA touches the blue or red line (within the Touch distance), while the 30m candle is still open | Message + chart photo |
| ✅ **CONFIRMED** | Usually under 1 minute after the candle closes, if the 9 EMA has crossed the line | Full message + chart photo |
| ❌ **CANCELLED** | Usually under 1 minute after the candle closes, if it touched but didn't cross | Short message |

- Every touch alert is followed by either **CONFIRMED** or **CANCELLED**.
- One touch alert per line per candle, and only for a new touch.
- "Touch distance" (default 25 USD) is set in the indicator's Inputs.

## Price level alerts (up to 3 levels)

| Alert | What you get |
|---|---|
| 🎯 **PRICE LEVEL CROSSED** | Price crossed your level: direction, time (to the second), chart with the level line |
| ↩️ **PRICE CAME BACK** | Price came back through the level: cross time, back time, how long it stayed past it |

## Timeframe

Alerts use the timeframe of the chart the alert is created on (5m, 15m, 30m, 1h, 4h...).
To change it: switch the chart timeframe, then delete and recreate the alert.

## Telegram tags (your signal history)

Tap any tag in Telegram to see every past signal of that kind:

- Stage: `#TOUCH` `#CONFIRMED` `#CANCELLED` `#LEVEL_CROSS` `#LEVEL_BACK`
- A level: e.g. `#LEVEL_78000`
- Line and direction: `#BLUE_UP` `#BLUE_DOWN` `#RED_UP` `#RED_DOWN`

## How it works

```
TradingView CRYPTO:BTCUSD 30m chart + indicator  ── alert by EMAIL
        ▼
Gmail + Google Apps Script (checks every minute)  ── forwards to
        ▼
Vercel server (api/index.py)  ── draws the chart from TradingView's numbers
        ▼
Telegram ──► your iPhone + Samsung
```

## Folder contents

```
btc-ema-telegram-alerts/
├── api/index.py                         the server
├── requirements.txt                     Python packages for Vercel
├── vercel.json                          Vercel routing + timeout settings
├── tradingview/ema_cross_telegram.pine  TradingView indicator that fires the alerts
├── gmail_script/forward_tradingview_alerts.gs  Google script: Gmail → server
├── SETUP-STEP-BY-STEP.md                full click-by-click setup
└── README.md                            this file
```

## Accuracy

All values come from TradingView's own CRYPTO:BTCUSD calculation, so the messages
match your chart exactly. (The `/cron` exchange-price check still exists in the
server as a backup, but it isn't used; its cron-job.org job is switched off.)

The bot reports crosses. It doesn't place trades, and a cross alone isn't a
guaranteed buy or sell signal.
