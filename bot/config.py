import os
from dotenv import load_dotenv

load_dotenv()

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY", "")

ALERT_EMAIL_SENDER = os.getenv("ALERT_EMAIL_SENDER", "")
ALERT_EMAIL_PASSWORD = os.getenv("ALERT_EMAIL_PASSWORD", "")
ALERT_EMAIL_RECIPIENT = os.getenv("ALERT_EMAIL_RECIPIENT", "")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

SCAN_INTERVAL_SECONDS = int(os.getenv("SCAN_INTERVAL_SECONDS", "300"))
DIP_THRESHOLD_24H = float(os.getenv("DIP_THRESHOLD_24H", "-20.0"))
DIP_THRESHOLD_1H = float(os.getenv("DIP_THRESHOLD_1H", "-10.0"))
VOLUME_SURGE_MULTIPLIER = float(os.getenv("VOLUME_SURGE_MULTIPLIER", "3.0"))
RSI_OVERSOLD = float(os.getenv("RSI_OVERSOLD", "30"))
MIN_VOLUME_USDT = float(os.getenv("MIN_VOLUME_USDT", "500000"))
