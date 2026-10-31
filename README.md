# BTCUSD 9 EMA Cross Alerts → Telegram

Sends a Telegram message with a chart photo every time the **purple 9 EMA**
crosses the **blue EMA High** or the **red EMA Low** on the **BTCUSD 30-minute**
chart, upward or downward.

## How it works

```
TradingView (your chart, your data)
   │  detects the cross when the 30m candle CLOSES
   ▼
Webhook  ──►  Vercel server (api/index.py)
                 │  draws the chart from TradingView's own candles
                 ▼
              Telegram  ──►  your iPhone + Samsung
```

- The cross is detected by TradingView itself, on CRYPTO:BTCUSD. Every signal
  matches what you see on your chart.
- Signals are only sent after the candle has **closed**. A cross that appears
  and disappears mid-candle is never sent.
- Everything runs on TradingView's and Vercel's servers. Your PC and phone can be off.

## The 4 signals

| Signal | Meaning | Telegram tag |
|---|---|---|
| 9 EMA crosses BLUE upward | purple moves above the EMA High line | `#BLUE_UP` |
| 9 EMA crosses BLUE downward | purple moves below the EMA High line | `#BLUE_DOWN` |
| 9 EMA crosses RED upward | purple moves above the EMA Low line | `#RED_UP` |
| 9 EMA crosses RED downward | purple moves below the EMA Low line | `#RED_DOWN` |

Tap a tag in Telegram to see every past signal of that type. That's your signal history.

Each message contains: the line crossed, the direction, the candle time (IST),
the candle's Open/High/Low/Close, the exact 9 EMA / EMA High / EMA Low values,
and where the 9 EMA sits now (above both, between, or below both).
The photo shows the last 40 candles with all 3 lines and an arrow on the cross.

## Folder contents

```
btc-ema-telegram-alerts/
├── api/index.py                       server: receives alert, draws chart, sends Telegram
├── requirements.txt                   Python packages for Vercel
├── vercel.json                        Vercel routing + timeout settings
├── tradingview/ema_cross_telegram.pine  TradingView indicator that fires the alerts
└── README.md                          this guide
```

---

## Setup (about 30 minutes, one time)

### 1. Create the Telegram bot

1. In Telegram, search **@BotFather** → send `/newbot`.
2. Give it a name, then a username that ends in `bot`.
3. BotFather replies with a **token**. Copy it and keep it private.
4. Open your new bot → tap **Start** → send any message.
5. In a browser open:
   `https://api.telegram.org/bot<your-bot-token>/getUpdates`
6. Find `"chat":{"id":` and copy the number after it. That's your **chat id**.
7. Log into the same Telegram account on your iPhone and your Samsung.
   Both receive every alert.

> To send alerts to another person too: they open the bot, tap Start, and you
> repeat steps 5–6 to get their chat id. Put both ids in `TG_CHAT_IDS`,
> separated by a comma.

### 2. Put the folder on GitHub

1. GitHub → **New repository** (e.g. `btc-ema-telegram-alerts`).
2. **Add file → Upload files** → drag in everything inside this folder,
   keeping the `api` and `tradingview` folders → **Commit**.
3. Check the repo shows `api/index.py`, `requirements.txt` and `vercel.json` at the top level.

### 3. Deploy on Vercel

1. vercel.com → sign in with GitHub → **Add New → Project** → **Import** the repo.
2. Framework Preset: **Other**. Leave the build settings empty.
3. **Environment Variables**, add all three:

   | Name | Value |
   |---|---|
   | `TG_TOKEN` | your bot token |
   | `TG_CHAT_IDS` | your chat id (comma-separate if more than one) |
   | `WEBHOOK_KEY` | a long secret word you invent (letters/numbers, no spaces) |

4. **Deploy**. When it's done, copy your domain: `https://<your-project>.vercel.app`
5. **Settings → Deployment Protection** → make sure **Vercel Authentication is OFF**
   for production, otherwise TradingView gets blocked.

### 4. Connection check

1. Open `https://<your-project>.vercel.app/`
   It must say the server is running and all three settings are **yes**.
2. Open `https://<your-project>.vercel.app/check?key=<your-WEBHOOK_KEY>`
   You get "✅ connected" in Telegram. If not, re-check `TG_TOKEN` / `TG_CHAT_IDS`
   and redeploy (see Maintenance).

### 5. TradingView indicator

1. Open your BTCUSD chart (CRYPTO:BTCUSD), timeframe **30m**.
2. **Pine Editor** → delete everything → paste `tradingview/ema_cross_telegram.pine`
   → **Save** → **Add to chart**.
3. Open the indicator's **Settings → Inputs**:
   - **Webhook key**: exactly the same as `WEBHOOK_KEY` on Vercel.
   - **EMA High / EMA Low length**: the same length your
     "Custom EMA High/Low & SMA – [GSK-VIZAG-AP-INDIA]" indicator uses (its Inputs tab).
   - **Purple 9 EMA length**: 9.
4. **Accuracy check:** keep your old two indicators visible for a moment. The new
   purple, blue and red lines must lie exactly on top of the old ones. If blue/red
   don't match, the length in step 3 is different from your old indicator; fix it.
   Then hide the old indicators if you like.

### 6. Create the TradingView alert

1. TradingView **Settings → Privacy and security** → turn on **2-factor authentication**
   (TradingView requires it for webhooks).
2. On the 30m BTCUSD chart, click **Alert** (clock icon):
   - **Condition:** `9 EMA Cross Alerts -> Telegram` → **Any alert() function call**
   - **Expiration:** the longest your plan allows (or Open-ended)
   - **Notifications tab:** tick **Webhook URL** → `https://<your-project>.vercel.app/tv`
   - You can also tick **Notify in app** as a backup.
3. **Create**.

From now on every cross on a closed 30m candle arrives in Telegram with its chart.

---

## Maintenance

- **Changing a Vercel variable:** after editing it, go to **Deployments → ⋯ → Redeploy**.
  Changes only apply after a redeploy.
- **Changing the indicator inputs** (key, lengths): edit the alert afterwards
  (or delete and recreate it), because an alert keeps the settings it was created with.
- **Alert expiry:** check the alert's expiry date in TradingView's Alerts panel and
  renew it before it ends.
- **Logs:** Vercel → your project → **Logs** shows every alert received and every
  Telegram send. TradingView → Alerts → **Log** shows every alert fired.

## Troubleshooting

| Problem | Fix |
|---|---|
| Status page shows a setting as **NO** | Add the variable in Vercel, then Redeploy |
| `/check` says Telegram FAILED | Wrong token or chat id, or you never pressed Start in the bot |
| Vercel log: "Rejected: wrong webhook key" | Key in the indicator ≠ `WEBHOOK_KEY`; fix, then recreate the alert |
| TradingView alert log shows an error about message length | Indicator Inputs → lower "Candles sent for the chart photo" to 30, recreate the alert |
| TradingView log shows a webhook timeout but Telegram got the alert | Normal after a long idle period; nothing lost |
| Nothing in Vercel logs when TradingView fired | Check the webhook URL ends with `/tv`, and that Deployment Protection is off |
| Lines don't match your old indicator | Length in the Pine inputs is different; match it and recreate the alert |

## Notes

- The bot reports crosses. It doesn't place trades, and a cross alone isn't a
  guaranteed buy or sell signal.
- Keep your bot token and webhook key private. Anyone with the key could send
  fake alerts to your bot.
