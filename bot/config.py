import os
from dotenv import load_dotenv

load_dotenv()

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY", "")

ALERT_EMAIL_SENDER = os.getenv("ALERT_EMAIL_SENDER", "")
ALERT_EMAIL_PASSWORD = os.getenv("ALERT_EMAIL_PASSWORD", "")
ALERT_EMAIL_RECIPIENT = os.getenv("ALERT_EMAIL_RECIPIENT", "")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Scanner settings
SCAN_INTERVAL_SECONDS = int(os.getenv("SCAN_INTERVAL_SECONDS", "300"))
DIP_THRESHOLD_24H = float(os.getenv("DIP_THRESHOLD_24H", "-20.0"))
DIP_THRESHOLD_1H = float(os.getenv("DIP_THRESHOLD_1H", "-10.0"))
VOLUME_SURGE_MULTIPLIER = float(os.getenv("VOLUME_SURGE_MULTIPLIER", "3.0"))
RSI_OVERSOLD = float(os.getenv("RSI_OVERSOLD", "30"))
MIN_VOLUME_USDT = float(os.getenv("MIN_VOLUME_USDT", "5000000"))
MAX_DROP_24H = float(os.getenv("MAX_DROP_24H", "-50.0"))

# Trading settings
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
MIN_BUY_SCORE = int(os.getenv("MIN_BUY_SCORE", "60"))
MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", "3"))
BALANCE_ALLOCATION_PCT = float(os.getenv("BALANCE_ALLOCATION_PCT", "0.50"))  # 50% of balance
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "-8.0"))
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "15.0"))
DAILY_LOSS_CAP_PCT = float(os.getenv("DAILY_LOSS_CAP_PCT", "0.50"))  # 50% of starting balance
MONITOR_INTERVAL_SECONDS = int(os.getenv("MONITOR_INTERVAL_SECONDS", "120"))
MAX_HOLD_HOURS = float(os.getenv("MAX_HOLD_HOURS", "24.0"))
