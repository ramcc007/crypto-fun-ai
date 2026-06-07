"""
Alert delivery: console (always), email (if configured), log file.
"""
import smtplib
import os
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from colorama import Fore, Style, init as colorama_init

from bot.config import (
    ALERT_EMAIL_SENDER, ALERT_EMAIL_PASSWORD, ALERT_EMAIL_RECIPIENT
)
from bot.signals import Signal

colorama_init(autoreset=True)

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/alerts.log",
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
)


def _score_color(score: int) -> str:
    if score >= 60:
        return Fore.GREEN
    if score >= 35:
        return Fore.YELLOW
    return Fore.CYAN


def print_signal(sig: Signal, reasoning: str) -> None:
    color = _score_color(sig.score)
    now = datetime.now().strftime("%H:%M:%S")
    bar = "=" * 60

    print(f"\n{color}{bar}")
    print(f"  {now}  {sig.symbol}  |  Score: {sig.score}/100")
    print(f"  Price: ${sig.price}  |  24h: {sig.change_24h:.1f}%  |  1h: {sig.change_1h:.1f}%")
    print(f"  Signals: {', '.join(sig.signal_types)}")
    print(f"  Volume: ${sig.volume_usdt_24h:,.0f} USDT  |  Vol surge: {sig.vol_surge_1h:.1f}x")
    print(f"  RSI: {sig.rsi_1h:.1f}  |  BB %B: {sig.bollinger['pct_b']}")
    print(bar)
    print(reasoning)
    print(f"{bar}{Style.RESET_ALL}")


def send_email(sig: Signal, reasoning: str) -> None:
    if not all([ALERT_EMAIL_SENDER, ALERT_EMAIL_PASSWORD, ALERT_EMAIL_RECIPIENT]):
        return

    subject = f"[CryptoBot] {sig.symbol} | Score {sig.score}/100 | {', '.join(sig.signal_types)}"

    html = f"""
<html><body style="font-family:monospace;background:#111;color:#eee;padding:20px">
<h2 style="color:#4ade80">{sig.symbol} — Score: {sig.score}/100</h2>
<table style="border-collapse:collapse;width:100%">
  <tr><td style="padding:4px 12px"><b>Price</b></td><td>${sig.price}</td></tr>
  <tr><td style="padding:4px 12px"><b>24h Change</b></td><td style="color:{'#f87171' if sig.change_24h < 0 else '#4ade80'}">{sig.change_24h:.2f}%</td></tr>
  <tr><td style="padding:4px 12px"><b>1h Change</b></td><td style="color:{'#f87171' if sig.change_1h < 0 else '#4ade80'}">{sig.change_1h:.2f}%</td></tr>
  <tr><td style="padding:4px 12px"><b>Volume (24h)</b></td><td>${sig.volume_usdt_24h:,.0f} USDT</td></tr>
  <tr><td style="padding:4px 12px"><b>Volume Surge</b></td><td>{sig.vol_surge_1h:.1f}x average</td></tr>
  <tr><td style="padding:4px 12px"><b>RSI (1h)</b></td><td>{sig.rsi_1h:.1f}</td></tr>
  <tr><td style="padding:4px 12px"><b>BB %B</b></td><td>{sig.bollinger['pct_b']}</td></tr>
  <tr><td style="padding:4px 12px"><b>Signals</b></td><td>{', '.join(sig.signal_types)}</td></tr>
</table>
<hr style="border-color:#333;margin:16px 0">
<h3 style="color:#facc15">Analysis</h3>
<pre style="white-space:pre-wrap;color:#d1d5db">{reasoning}</pre>
<hr style="border-color:#333;margin:16px 0">
<p style="color:#6b7280;font-size:12px">
  ⚠ Not financial advice. Verify before trading. This bot monitors signals only — it does not trade for you.
</p>
</body></html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = ALERT_EMAIL_SENDER
    msg["To"] = ALERT_EMAIL_RECIPIENT
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(ALERT_EMAIL_SENDER, ALERT_EMAIL_PASSWORD)
            server.sendmail(ALERT_EMAIL_SENDER, ALERT_EMAIL_RECIPIENT, msg.as_string())
        print(f"  → Email sent to {ALERT_EMAIL_RECIPIENT}")
    except Exception as e:
        print(f"  → Email failed: {e}")


def log_signal(sig: Signal) -> None:
    logging.info(
        f"{sig.symbol} | score={sig.score} | 24h={sig.change_24h:.1f}% | "
        f"1h={sig.change_1h:.1f}% | rsi={sig.rsi_1h:.1f} | "
        f"vol_surge={sig.vol_surge_1h:.1f}x | signals={','.join(sig.signal_types)}"
    )


def dispatch(sig: Signal, reasoning: str, min_score: int = 30) -> None:
    if sig.score < min_score:
        return
    print_signal(sig, reasoning)
    log_signal(sig)
    send_email(sig, reasoning)
