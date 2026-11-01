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
   • gets BTC/USD 30m + 1m candles from Coinbase, Kraken, Bitstamp, Bitfinex
   • averages them, the same way TradingView builds CRYPTO:BTCUSD
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

## Accuracy note (CRYPTO:BTCUSD)

TradingView builds CRYPTO:BTCUSD as an average of BTC prices from several exchanges.
The bot rebuilds it the same way, from the main USD exchanges: Coinbase, Kraken,
Bitstamp and Bitfinex. If one exchange is down or its price is far off, it's left
out, like TradingView does. Every message shows which exchanges were used.

TradingView doesn't publish its exact exchange list, so the values can still differ
by a few dollars from your chart. Clear crosses land on the same candle; a very
tight cross can rarely be one candle off.

The bot reports crosses. It doesn't place trades, and a cross alone isn't a
guaranteed buy or sell signal.
