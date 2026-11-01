# Step-by-Step Setup: exact CRYPTO:BTCUSD alerts → Telegram

## How it works

```
TradingView (your CRYPTO:BTCUSD 30m chart)
   │  the indicator watches the 3 lines on TradingView's own data
   │  and fires an alert → sent by EMAIL (no webhook, so no 2FA needed)
   ▼
Gmail (the TradingView account's email)
   │  a small Google script checks the inbox every minute
   ▼
Your Vercel server  ──►  Telegram (message + chart photo)
```

Because TradingView itself detects the cross, **every number in the Telegram
message is exactly the number on your CRYPTO:BTCUSD chart.**

You get:
- 🟡 **LINES TOUCHING**: the moment the live purple 9 EMA **touches** the blue or red
  line (comes within the "Touch distance", default 25 USD) while the candle is still open
- ✅ **CONFIRMED**: at the candle close, the 9 EMA has crossed the line
- ❌ **CANCELLED**: it touched, but at the candle close it had not crossed

A touch alert is sent once per line per candle, and only for a new touch: if the lines
were already touching at the previous candle close, you aren't sent the same touch again.

Price levels (optional, up to 3):
- 🎯 **PRICE LEVEL CROSSED**: the price crossed your level (time to the second + chart)
- ↩️ **PRICE CAME BACK**: the price came back through the level, with the time and
  how long it stayed past the level

**Timeframe:** the alerts use the timeframe of the chart you create the alert on
(5m, 15m, 30m, 1h, 4h...). The messages show it.

**Timing (honest):** TradingView fires the instant it happens, but the email route adds
delay: usually **under 1 minute**, sometimes up to about 2 minutes. That's the limit
without 2FA (a webhook would be a few seconds).

Follow every part in order. After each part there's a **"You should see"** line.
If you don't see it, stop and send a screenshot of that screen.

---

## PART 1: Update the code on GitHub

1. Download **btc-ema-telegram-alerts.zip** from the Claude chat and extract it
   (right-click → **Extract All** → **Extract**).
2. Open the extracted folder → **api** → right-click **index.py** → **Open with → Notepad**.
3. Press **Ctrl + A**, then **Ctrl + C**.
4. On **github.com**, open your repository → **api** → **index.py** → click the **pencil icon** ✏️.
5. Click in the code, press **Ctrl + A**, press **Delete**, then press **Ctrl + V**.
6. Click **Commit changes...** → **Commit changes**.

**You should see:** `api/index.py` updated "now".

---

## PART 2: Check Vercel and note your domain and key

1. On **vercel.com**, open your project → **Deployments** tab.
2. Wait until the first row ("Update index.py") shows a green **Ready** (1–2 minutes).
3. **Overview** tab → under **Domains**, note the `.vercel.app` address. That's **YOUR-DOMAIN**.
4. **Settings** → **Environment Variables** → click the 👁 next to `WEBHOOK_KEY`.
   Note the value exactly. That's **YOUR-KEY**.

**You should see:** a green **Ready**, and you've written down YOUR-DOMAIN and YOUR-KEY.

---

## PART 3: Turn off the old cron-job.org job

The old job used exchange prices, which aren't exact. Turn it off so you don't get two different alerts.

1. Log in to **cron-job.org** → **Dashboard**.
2. Click your job **BTC 9 EMA alert**.
3. Turn **Enable job** **off** → **Save**.

**You should see:** the job shown as disabled.

---

## PART 4: Add the indicator in TradingView

1. Open your **CRYPTO:BTCUSD** chart, timeframe **30m**.
2. At the bottom, click **Pine Editor**.
3. If you added "9 EMA Cross Alerts -> Telegram" before, open it from the Pine Editor's
   script menu; otherwise click **Open → New indicator**.
4. Click in the code, press **Ctrl + A**, press **Delete**.
5. In the extracted folder open **tradingview** → **ema_cross_telegram.pine** with Notepad,
   **Ctrl + A**, **Ctrl + C**, then go back to the Pine Editor and press **Ctrl + V**.
6. Click **Save**. Name it `9 EMA Cross -> Telegram (CRYPTO exact)`.
7. Click **Add to chart** (or **Update on chart**).
8. On the chart, hover the indicator's name → click the ⚙️ **Settings** icon → **Inputs** tab.
   The settings are in 3 groups:

   **9 EMA alerts**
   - **Purple 9 EMA length**: 9
   - **EMA High / EMA Low length**: the same number as in your
     "Custom EMA High/Low & SMA" indicator's Inputs tab
   - **Touch distance in USD**: how close the lines must be to count as "touching".
     Default **25**. Bigger = earlier alert but more cancels; smaller = only when they really meet.
   - **Send 9 EMA touch / confirmed / cancelled alerts**: ticked (untick if you only want price levels)

   **Price level alerts (0 = off)**
   - **Level 1 / Level 2 / Level 3 price**: type the prices you want to watch,
     e.g. `78000`. Leave `0` for levels you don't use.
   - **Buffer in USD**: default **10**. The price must pass the level by this much,
     so tiny wiggles around the level don't send many alerts.

   **General**
   - **Key**: type **YOUR-KEY** exactly
   - **Candles sent for the chart photo**: 40
   - **Show the 3 lines on the chart**: your choice

   Click **Ok**.
9. **Check the lines:** the purple, blue and red lines of this indicator must lie exactly
   on top of your existing purple, blue and red lines. If blue/red don't match, the length
   in step 8 is different. Fix it.
   Orange lines show your price levels.

**You should see:** the indicator name on the chart, with its lines exactly on your existing lines.

---

## PART 5: Create the TradingView alert (email only)

1. If an old alert for "9 EMA Cross Alerts -> Telegram" exists, delete it first:
   right side **Alerts** panel (clock icon) → hover it → **⋯** → **Delete**.
2. Click **Alert** in the top toolbar.
3. **Settings** tab:
   - **Condition:** `9 EMA Cross -> Telegram (CRYPTO exact)`
   - Below it choose: **Any alert() function call**
   - **Expiration:** **Open-ended** (or the latest date offered)
   - **Alert name:** `BTC 9 EMA Telegram`
4. **Notifications** tab:
   - Tick **Send email**.
   - **Untick** Notify in app, Show pop-up and Play sound,
     so family members on this account aren't disturbed.
   - Leave **Webhook URL** unticked.
5. Click **Create**.

**You should see:** "BTC 9 EMA Telegram" in the Alerts panel, active.

> The emails go to the email address of this TradingView account. Part 6 must be
> done in that same Gmail account.

---

## PART 6: Google script that forwards the emails to Telegram

Do this logged into the **Gmail account that receives the TradingView emails**.
Someone with access to that Gmail needs to do it once; after that it runs by itself.

### 6A. Create the script

1. In the browser, go to **https://script.google.com** (logged into that Gmail).
2. Click **New project**.
3. Delete everything in the code box.
4. In the extracted folder open **gmail_script** → **forward_tradingview_alerts.gs**
   with Notepad → **Ctrl + A**, **Ctrl + C** → paste into the code box (**Ctrl + V**).
5. In line 8, change
   `const SERVER = "https://YOUR-DOMAIN/tv";`
   to your real domain, e.g. `"https://btc-ema-telegram-alerts.vercel.app/tv"`.
   Keep `/tv` at the end.
6. Click the project name "Untitled project" at the top → name it `TradingView to Telegram` → **Rename**.
7. Press **Ctrl + S** (save).

### 6B. Allow it to read Gmail (one time)

1. At the top, make sure the function dropdown shows **forwardTradingViewAlerts**, then click **▶ Run**.
2. A window "Authorization required" opens → **Review permissions** → choose the Gmail account.
3. You may see "Google hasn't verified this app". That's normal for your own script:
   click **Advanced** → **Go to TradingView to Telegram (unsafe)**.
4. Click **Allow**.

**You should see:** at the bottom, "Execution started" then "Execution completed".

### 6C. Make it run every minute

1. On the left, click the **⏰ Triggers** icon.
2. Click **+ Add Trigger** (bottom right).
3. Set:
   - Choose which function to run: **forwardTradingViewAlerts**
   - Select event source: **Time-driven**
   - Select type of time based trigger: **Minutes timer**
   - Select minute interval: **Every minute**
   - Failure notification settings: **Notify me daily**
4. Click **Save**.

**You should see:** one trigger in the list: forwardTradingViewAlerts, Time-based, Every minute.

**Setup is finished.** Nothing needs your PC. TradingView, Gmail, Vercel and Telegram all run online.

---

## PART 7: How to see it working

- **TradingView** → Alerts panel → **Log** tab: every time the alert fired.
- **Gmail**: TradingView alert emails arrive and are automatically marked read and archived
  by the script (find them under **All Mail**).
- **Google script** → left menu **Executions**: one run per minute. Click a run that
  forwarded something to see `200 ok`.
- **Vercel** → your project → **Logs**: each EARLY / CONFIRMED / CANCELLED received and sent.
- **Telegram**: the messages (🟡 touching, ✅ confirmed, ❌ cancelled). The numbers match your CRYPTO:BTCUSD chart exactly,
  and every message ends with "Data: TradingView CRYPTO:BTCUSD".

---

## If something is wrong

| What you see | What to do |
|---|---|
| TradingView Log shows alerts, but no email arrives | Check the TradingView account's email is correct (Profile → Settings → email), and check Spam |
| Emails arrive but stay **unread** | Part 6C trigger missing, or 6B permission not given. Run ▶ once more |
| Script Executions show `403` | The Key in the indicator (Part 4.8) ≠ `WEBHOOK_KEY` in Vercel. Fix the Key, then **delete and recreate the alert** (Part 5) |
| Script Executions show `400 bad json` | Send me a screenshot of the email text |
| Script Executions show an error about the address | `SERVER` in line 8 is wrong; it must be `https://YOUR-DOMAIN/tv` |
| Vercel log fine but no Telegram | Open `https://YOUR-DOMAIN/check?key=YOUR-KEY` to test Telegram |
| Lines don't match your chart | Length in Part 4.8 differs from your indicator; fix, then recreate the alert |
| Same alert twice | The cron-job.org job is still on (Part 3), or two TradingView alerts exist |

## Changing settings later (timeframe, levels, touch distance)

TradingView rule: **an alert keeps the settings it was created with.** So every change is:
change the setting → delete the old alert → create it again. About 1 minute.

**Change the timeframe** (e.g. 30m → 15m):
1. Click the timeframe at the top of the chart and pick the new one.
2. Alerts panel → delete "BTC 9 EMA Telegram".
3. Create it again exactly as in Part 5. It now runs on the new timeframe.

**Change price levels / touch distance / lengths:**
1. Indicator ⚙️ Settings → Inputs → change the numbers → **Ok**.
2. Alerts panel → delete "BTC 9 EMA Telegram".
3. Create it again exactly as in Part 5.

**Several timeframes at once?** Create one alert per timeframe: set the chart to 15m →
create alert → set the chart to 1h → create another alert. Each message shows its timeframe.

## Important

- **Changed anything in the indicator** (Key, lengths, code)? **Delete and recreate the alert** (Part 5).
  A TradingView alert keeps the settings it was created with.
- Don't delete or rename the alert or the indicator later, or alerts stop.
- Check the alert's expiry in the Alerts panel if it isn't Open-ended, and renew it in time.
