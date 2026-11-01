# Step-by-Step Setup (your Vercel project already exists)

This sets up the **2-stage alerts**:
⚠️ EARLY SIGNAL (within about 1 minute of the cross) → ✅ CONFIRMED or ❌ CANCELLED (at candle close).

Follow every part in order. Don't skip any step.
At the end of each part there's a **"You should see"** line. If you don't see it,
stop and send a screenshot of that screen.

There are 6 parts:

1. Get the new code onto your computer
2. Update the code on GitHub
3. Check Vercel redeployed it
4. Check the settings in Vercel
5. Check the server works
6. Create the every-minute schedule on cron-job.org

---

## PART 1: Get the new code onto your computer

1. Download **btc-ema-telegram-alerts.zip** from the Claude chat.
2. Open your **Downloads** folder.
3. Right-click **btc-ema-telegram-alerts.zip** → **Extract All** → **Extract**.
4. Open the extracted folder → open the **api** folder.
5. Right-click **index.py** → **Open with** → **Notepad**.
6. In Notepad press **Ctrl + A** (select all), then **Ctrl + C** (copy).
7. Keep Notepad open.

**You should see:** the code in Notepad, starting with
`BTCUSD 30m  9 EMA cross alerts -> Telegram, in TWO STAGES`.

---

## PART 2: Update the code on GitHub

1. Open **github.com** and log in.
2. Open your repository (the one you connected to Vercel, e.g. `btc-ema-telegram-alerts`).
3. Click the **api** folder.
4. Click **index.py**.
5. Click the **pencil icon** ✏️ (top right of the code, "Edit this file").
6. Click inside the code box, press **Ctrl + A**, then press **Delete**.
   The box is now empty.
7. Press **Ctrl + V** to paste the new code from Notepad.
8. Click the green **Commit changes...** button (top right).
9. In the window that opens, click **Commit changes** again.

**You should see:** the file `api/index.py` with the new code, and at the top
a message like "Update index.py" with "now" next to it.

---

## PART 3: Check Vercel redeployed it

Vercel updates by itself when GitHub changes. You only check it.

1. Open **vercel.com** and log in.
2. Click your project.
3. Click the **Deployments** tab at the top.
4. Look at the **first row** in the list. It shows "Update index.py".
5. Wait until its status turns **Ready** (green dot). This takes about 1–2 minutes.
   Refresh the page if needed.

**You should see:** the top deployment = "Update index.py" with a green **Ready**.

If it shows a red **Error**, click it, take a screenshot of the error, and send it.

---

## PART 4: Check the settings in Vercel

### 4A. Find and note your domain

1. In your project, click the **Overview** tab (or the project name at the top).
2. Under **Domains**, find the address ending in **.vercel.app**,
   e.g. `btc-ema-telegram-alerts.vercel.app`.
   If several are listed, use the **shortest** one.
3. Write it down. In this guide it's called **YOUR-DOMAIN**.

### 4B. Check the environment variables and note your key

1. Click the **Settings** tab.
2. In the left menu click **Environment Variables**.
3. Check these 3 are in the list:
   - `TG_TOKEN`
   - `TG_CHAT_IDS`
   - `WEBHOOK_KEY`
4. Next to `WEBHOOK_KEY`, click the **eye icon** 👁 to show its value.
5. Write that value down. In this guide it's called **YOUR-KEY**.
   Copy it exactly: capitals, small letters and numbers must match.

If one of the 3 is missing:
- Click **Add New** (or **Add Environment Variable**).
- Enter the Key name and the Value, tick all environments, and click **Save**.
- Then go to **Deployments** → first row → click **⋯** (three dots) → **Redeploy** → **Redeploy**,
  and wait for green **Ready**.

### 4C. Make sure Deployment Protection is off

1. Still in **Settings**, click **Deployment Protection** in the left menu.
2. Find **Vercel Authentication**.
3. If it's **Enabled** or "Standard Protection", change it to **Disabled**.
4. Click **Save**.

**You should see:** Vercel Authentication = **Disabled**.

---

## PART 5: Check the server works

Use your own **YOUR-DOMAIN** and **YOUR-KEY** in the addresses below.
Type each one into the browser's address bar and press Enter.

### 5A. Status page

```
https://YOUR-DOMAIN/
```

**You should see:**
```
BTC 9 EMA alert server is running (2-stage: early + confirmed).
TG_TOKEN set: yes
Chat ids set: 1
WEBHOOK_KEY set: yes
```

### 5B. Telegram connection

```
https://YOUR-DOMAIN/check?key=YOUR-KEY
```

**You should see:** `Telegram OK — message sent.` in the browser, **and**
the message "✅ BTC 9 EMA alert server is connected to this Telegram chat."
in Telegram on your phone.

### 5C. Live BTC check

```
https://YOUR-DOMAIN/cron?key=YOUR-KEY
```

**You should see** one line like this, with today's real numbers:
```
Average of Coinbase, Kraken, Bitstamp, Bitfinex | LIVE candle 01 Nov 13:00 IST, minute 17 | price 77,780.10 | 9EMA 77,701.55 | blue 77,690.20 | red 77,520.90 | no new cross
```

- "LIVE candle ..., minute 17" means the 13:00 candle is open and 17 minutes are finished.
- The 9EMA / blue / red numbers are the **live** values right now.
- Now compare with TradingView: on your BTCUSD 30m chart, look at the **current
  candle** and read the 9 EMA, blue and red values. They should be close.
  If blue and red are far off, the length is different: add `SLOW_LEN` in Vercel
  (Part 4B) with the length from your "Custom EMA High/Low" indicator's Inputs tab,
  then Redeploy.

---

## PART 6: Create the every-minute schedule on cron-job.org

This free website opens your `/cron` address **every minute**, automatically.
Each time, the server looks at BTC:
- while the 30m candle is open → sends ⚠️ EARLY SIGNAL if the 9 EMA just crossed a line
- in the first minute after the candle closes → sends ✅ CONFIRMED or ❌ CANCELLED
- otherwise → sends nothing

> **Already made a cron job before (minutes 1 and 31)?** Open it, click **Edit**,
> and change only the schedule as in step 6B.3 below, then **Save**.
> Don't create a second job.

### 6A. Make an account

1. Open **https://cron-job.org**
2. Click **Sign up** (top right).
3. Enter your email and a password, accept the terms, and click **Create account**.
4. Open your email, click the confirmation link, and log in.

### 6B. Create the job

1. Click **Dashboard** (or **Cronjobs**) in the menu.
2. Click **CREATE CRONJOB**.
3. On the **COMMON** tab:
   - **Title:** `BTC 9 EMA alert`
   - **URL:** `https://YOUR-DOMAIN/cron?key=YOUR-KEY`
     (exactly the same address that worked in Part 5C)
   - Make sure **Enable job** is turned **on**.
   - **Execution schedule:** choose **Every 1 minute(s)**
     (if you only see "Custom": select every day, every month, every weekday,
     every hour, and **every minute**).
4. Click the **ADVANCED** tab:
   - Turn **on** **Save responses in job history**.
   - If there's a **Timeout** field, set it to **30** seconds.
5. Click the **NOTIFICATIONS** tab:
   - Turn **on** **Execution of the cronjob fails**.
6. Click **CREATE** (or **SAVE**).

**You should see:** your job "BTC 9 EMA alert" in the list, enabled,
with the next run time within the next minute.

> Keep only **one** job pointing to this address. Two jobs could send the same alert twice.

### 6C. Confirm it's running

1. Wait 2–3 minutes.
2. On cron-job.org, click your job → **History**.
3. You see one entry per minute. Click the newest one.

**You should see:** status **Successful** (200), and a response like:
```
Average of Coinbase, Kraken, Bitstamp, Bitfinex | LIVE candle ... minute 12 | price ... | 9EMA ... | blue ... | red ... | no new cross
```
At the first minute after each candle closes (xx:00 or xx:30), the response says
`CLOSE CHECK candle ...`.

When something happens, the response shows it, and Telegram gets the message at the same time:
- `EARLY BLUE UPWARD` → ⚠️ early signal sent
- `CONFIRMED BLUE UPWARD` → ✅ confirmation sent
- `CANCELLED BLUE UPWARD` → ❌ cancel message sent

**Setup is finished.** It now runs every minute by itself. Your PC can be off.

---

## If something is wrong

| What you see | What to do |
|---|---|
| Part 3: deployment shows **Error** | Screenshot the error and send it |
| 5A shows **NO** for a setting | Add that variable (Part 4B), then Redeploy |
| 5B: "Telegram FAILED" | `TG_TOKEN` or `TG_CHAT_IDS` is wrong, or you never pressed **Start** in your bot |
| 5B / 5C: "Wrong or missing key" | The key in the address ≠ `WEBHOOK_KEY` in Vercel. Copy it again exactly |
| Vercel login page opens instead | Deployment Protection is still on, see Part 4C |
| 5C: "error: No price data" | Exchanges didn't answer that moment; open it again after a minute |
| cron-job.org History: **401** or **403** | Part 4C (protection) or wrong key in the URL |
| cron-job.org History: **500** | Click the entry, screenshot the response, and send it |
| History: "error: 30m candle data not updated yet" now and then | The exchange was a few seconds late; only matters if it repeats every time, then send a screenshot |
| You got the same message twice | You have two cron jobs for the same address; delete one |

## Later

- **See every check:** cron-job.org → job → **History**.
- **See every Telegram send:** Vercel → project → **Logs**.
- **Changed a Vercel variable?** Deployments → first row → **⋯** → **Redeploy**.
- **Pause alerts:** cron-job.org → job → turn **Enable job** off.
