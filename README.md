# BTCUSD 9 EMA Cross Alerts → Telegram (2-stage)

Telegram alerts when the **purple 9 EMA** crosses the **blue EMA High** or the
**red EMA Low** on **BTCUSD 30-minute** candles, upward or downward.

**No TradingView alerts, no webhooks, no 2-factor authentication.**
Your shared TradingView account isn't touched.

👉 **Setup instructions: open `SETUP-STEP-BY-STEP.md`**

## The two stages

| Stage | When | What you get |
|---|---|---|
| ⚠️ **EARLY SIGNAL** | Within ~1 minute of the live 9 EMA crossing a line, while the 30m candle is still open | Message + chart photo, marked "not confirmed yet" |
| ✅ **CONFIRMED** | 1 minute after the candle closes, if the cross is still there | Full message + chart photo |
| ❌ **CANCELLED** | 1 minute after the candle closes, if the 9 EMA moved back before the close | Short message: the early signal didn't hold |

- Every early signal is always followed by either **CONFIRMED** or **CANCELLED**.
- A cross that only happens in the very last minute of a candle comes straight as
  **CONFIRMED** (the message says "Early signal: none").
- One early signal per line per candle. If the price wobbles back and forth, you
  aren't spammed.

## Telegram tags (your signal history)

Tap any tag in Telegram to see every past signal of that kind:

- Stage: `#EARLY` `#CONFIRMED` `#CANCELLED`
- Line and direction: `#BLUE_UP` `#BLUE_DOWN` `#RED_UP` `#RED_DOWN`

## How it works

```
cron-job.org  (free scheduler)  ── calls your server EVERY MINUTE
        ▼
Vercel server (api/index.py)
   • gets BTC/USD 30m + 1m candles from Kraken (Bitstamp as backup)
   • calculates 9 EMA (close), 20 EMA (high), 20 EMA (low), like TradingView
   • candle open   → checks the LIVE lines → EARLY SIGNAL
   • candle closed → checks the final lines → CONFIRMED or CANCELLED
        ▼
Telegram ──► your iPhone + Samsung (same Telegram account)
```

## Folder contents

```
btc-ema-telegram-alerts/
├── api/index.py                         the server
├── requirements.txt                     Python packages for Vercel
├── vercel.json                          Vercel routing + timeout settings
├── tradingview/ema_cross_telegram.pine  OPTIONAL: draws the same 3 lines on TradingView
├── SETUP-STEP-BY-STEP.md                full click-by-click setup
└── README.md                            this file
```

## Accuracy note

Prices come from Kraken BTC/USD. TradingView's CRYPTO:BTCUSD is TradingView's own
index from several exchanges, so values differ by a few dollars. Almost every
cross lands on the same candle as on your chart. On a very tight cross the
alert can be one candle off, or rarely missing. Every message says its data source.

The bot reports crosses. It doesn't place trades, and a cross alone isn't a
guaranteed buy or sell signal.
