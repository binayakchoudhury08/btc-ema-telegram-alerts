/**
 * Forwards TradingView alert emails to your Vercel server, which posts them to Telegram.
 * Runs every minute (time-driven trigger). Free, inside your own Google account.
 *
 * 1. Change SERVER below to your own Vercel address (keep /tv at the end).
 * 2. Run forwardTradingViewAlerts once (allow access), then add the 1-minute trigger.
 */
const SERVER = "https://YOUR-DOMAIN/tv";

function forwardTradingViewAlerts() {
  const threads = GmailApp.search('from:tradingview.com is:unread newer_than:2d', 0, 30);
  for (const thread of threads) {
    let allDone = true;
    for (const msg of thread.getMessages()) {
      if (!msg.isUnread()) continue;
      const body = msg.getPlainBody() || "";
      const start = body.indexOf('{"key"');
      const end = body.lastIndexOf("}");
      if (start < 0 || end <= start) {
        msg.markRead();            // a TradingView email that isn't one of our alerts
        continue;
      }
      const json = body.substring(start, end + 1).replace(/\s+/g, "");
      try {
        const res = UrlFetchApp.fetch(SERVER, {
          method: "post",
          contentType: "application/json",
          payload: json,
          muteHttpExceptions: true,
        });
        const code = res.getResponseCode();
        console.log(code + " " + res.getContentText());
        if (code >= 500) { allDone = false; continue; }   // server problem: retry next minute
        msg.markRead();
      } catch (e) {
        console.log("Send failed, will retry: " + e);
        allDone = false;
      }
    }
    if (allDone) thread.moveToArchive();   // keeps the inbox clean
  }
}
