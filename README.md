# BTCUSD 9 EMA Cross Alerts → Telegram

Sends a Telegram message with a chart photo every time the **purple 9 EMA**
crosses the **blue EMA High** or the **red EMA Low** on **BTCUSD 30-minute**
candles, upward or downward.

**No TradingView alerts, no webhooks, no 2-factor authentication needed.**
Your shared TradingView account isn't touched.

## How it works

```
cron-job.org  (free scheduler)
   │  calls your server 1 minute after every 30m candle closes
   ▼
Vercel server (api/index.py)
   │  gets BTC/USD 30m candles from Kraken (Bitstamp as backup)
   │  calculates 9 EMA (close), 20 EMA (high), 20 EMA (low)
   │  checks for a cross on the candle that just closed
   ▼
Telegram  ──►  your iPhone + Samsung (same Telegram account)
```

- The lines are calculated the same way as TradingView's `ta.ema`.
- Signals are only sent after the candle has **closed**. A cross that appears
  and disappears mid-candle is never sent.
- Everything runs online. Your PC and phone can be off.

## The 4 signals

| Signal | Meaning | Telegram tag |
|---|---|---|
| 9 EMA crosses BLUE upward | purple moves above the EMA High line | `#BLUE_UP` |
| 9 EMA crosses BLUE downward | purple moves below the EMA High line | `#BLUE_DOWN` |
| 9 EMA crosses RED upward | purple moves above the EMA Low line | `#RED_UP` |
| 9 EMA crosses RED downward | purple moves below the EMA Low line | `#RED_DOWN` |

Tap a tag in Telegram to see every past signal of that type. That's your signal history.

Each message contains: the line crossed, the direction, the candle time (IST),
the candle's Open/High/Low/Close, the 9 EMA / EMA High / EMA Low values,
where the 9 EMA sits now, and the data source.
The photo shows the last 40 candles with all 3 lines and an arrow on the cross.

## Folder contents

```
btc-ema-telegram-alerts/
├── api/index.py                         the server
├── requirements.txt                     Python packages for Vercel
├── vercel.json                          Vercel routing + timeout settings
├── tradingview/ema_cross_telegram.pine  OPTIONAL: draws the same 3 lines on TradingView
└── README.md                            this guide
```

---

## Setup (about 25 minutes, one time)

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

> To send alerts to family members too: each one opens the bot and taps Start,
> then you repeat steps 5–6 to get their chat id. Put all ids in `TG_CHAT_IDS`,
> separated by commas.

### 2. Put the folder on GitHub

1. GitHub → **New repository** (e.g. `btc-ema-telegram-alerts`).
2. **Add file → Upload files** → drag in everything inside this folder,
   keeping the `api` and `tradingview` folders → **Commit**.
3. Check the repo shows `api/index.py`, `requirements.txt` and `vercel.json` at the top level.

> Already have the repo from before? Just replace `api/index.py` with the new one
> and commit. Vercel redeploys automatically.

### 3. Deploy on Vercel

1. vercel.com → sign in with GitHub → **Add New → Project** → **Import** the repo.
2. Framework Preset: **Other**. Leave the build settings empty.
3. **Environment Variables**:

   | Name | Value |
   |---|---|
   | `TG_TOKEN` | your bot token |
   | `TG_CHAT_IDS` | your chat id (comma-separate if more than one) |
   | `WEBHOOK_KEY` | a long secret word you invent (letters/numbers, no spaces) |
   | `SLOW_LEN` | only if your EMA High/Low length is **not** 20 |
   | `FAST_LEN` | only if your purple EMA length is **not** 9 |

4. **Deploy**. Copy your domain: `https://<your-project>.vercel.app`
5. **Settings → Deployment Protection** → make sure **Vercel Authentication is OFF**
   for production, otherwise the scheduler gets blocked.

### 4. Connection check

1. Open `https://<your-project>.vercel.app/`
   It must say the server is running and all three settings are **yes**.
2. Open `https://<your-project>.vercel.app/check?key=<your-WEBHOOK_KEY>`
   You get "✅ connected" in Telegram.
3. Open `https://<your-project>.vercel.app/cron?key=<your-WEBHOOK_KEY>`
   It shows the last closed candle with its 9 EMA, blue and red values.
   Compare these with your TradingView chart for the same candle (hover the candle).
   They should be very close. If blue/red are clearly off, set `SLOW_LEN`
   to the length in your "Custom EMA High/Low" indicator's Inputs tab and redeploy.

### 5. Create the schedule on cron-job.org

1. Go to **cron-job.org** → sign up free → **Create cronjob**.
2. **URL:** `https://<your-project>.vercel.app/cron?key=<your-WEBHOOK_KEY>`
3. **Execution schedule:** choose **Custom** and set:
   - Minutes: **1** and **31**
   - Hours: every hour
   - Days / Months / Weekdays: every
   (This runs at xx:01 and xx:31: one check right after each 30m candle closes.)
4. Under **Advanced** set **Timeout** to **30 seconds**.
5. Under **Notifications**, turn on **"Notify me when execution fails"**,
   so you get an email if a check ever fails.
6. **Create**.

That's it. From now on every cross on a closed 30m candle arrives in Telegram with its chart.

> Don't schedule it more often than minutes 1 and 31. Each check alerts on the
> candle that closed in the last 10 minutes, so extra runs could send the same alert twice.

### 6. (Optional) See the same lines on TradingView

If you want the 3 lines on your chart in one indicator: Pine Editor →
paste `tradingview/ema_cross_telegram.pine` → Save → Add to chart.
You **don't** need to create any TradingView alert.

---

## Accuracy note

The prices come from Kraken BTC/USD. TradingView's CRYPTO:BTCUSD is TradingView's
own index built from several exchanges, so the values differ by a few dollars.
Almost every cross lands on the same candle as on your chart. On a very tight
cross (lines nearly touching), the alert can come one candle earlier or later,
or rarely not at all. Every message says which data source it used.

## Maintenance

- **Changing a Vercel variable:** after editing it, go to **Deployments → ⋯ → Redeploy**.
- **History of every check:** cron-job.org → your job → **History** shows each run's
  result (candle, line values, and "ALERT SENT" or "no cross").
- **Server logs:** Vercel → your project → **Logs**.

## Troubleshooting

| Problem | Fix |
|---|---|
| Status page shows a setting as **NO** | Add the variable in Vercel, then Redeploy |
| `/check` says Telegram FAILED | Wrong token or chat id, or you never pressed Start in the bot |
| `/cron` says "Wrong or missing key" | The key in the cron-job.org URL ≠ `WEBHOOK_KEY` |
| `/cron` shows "error: No price data" | Kraken and Bitstamp were both unreachable at that moment; the next run retries |
| cron-job.org shows 401 / 403 from Vercel | Turn off Deployment Protection (step 3.5) |
| Values differ a lot from TradingView | Set `SLOW_LEN` / `FAST_LEN` to your indicator's lengths, Redeploy |

## Notes

- The bot reports crosses. It doesn't place trades, and a cross alone isn't a
  guaranteed buy or sell signal.
- Keep your bot token and `WEBHOOK_KEY` private.
