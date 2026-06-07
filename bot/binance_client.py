import time
import requests
import pandas as pd
from bot.config import BINANCE_API_KEY, BINANCE_SECRET_KEY

BASE_URL = "https://api.binance.com"


def _get(endpoint: str, params: dict = None) -> dict | list:
    url = f"{BASE_URL}{endpoint}"
    headers = {"X-MBX-APIKEY": BINANCE_API_KEY} if BINANCE_API_KEY else {}
    resp = requests.get(url, params=params, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_all_usdt_tickers() -> list[dict]:
    """Fetch 24h stats for every *USDT spot pair."""
    data = _get("/api/v3/ticker/24hr")
    return [t for t in data if t["symbol"].endswith("USDT") and not t["symbol"].endswith("DOWNUSDT") and not t["symbol"].endswith("UPUSDT")]


def get_klines(symbol: str, interval: str, limit: int = 100) -> pd.DataFrame:
    """Return OHLCV DataFrame for a symbol. interval e.g. '1h', '15m', '4h'."""
    raw = _get("/api/v3/klines", params={"symbol": symbol, "interval": interval, "limit": limit})
    df = pd.DataFrame(raw, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore"
    ])
    for col in ["open", "high", "low", "close", "volume", "quote_volume"]:
        df[col] = pd.to_numeric(df[col])
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    return df


def get_1h_change(symbol: str) -> float:
    """Returns % price change over the last 1 hour using 1h klines."""
    try:
        df = get_klines(symbol, "1h", limit=2)
        if len(df) < 2:
            return 0.0
        prev_close = df.iloc[-2]["close"]
        curr_close = df.iloc[-1]["close"]
        return ((curr_close - prev_close) / prev_close) * 100
    except Exception:
        return 0.0


def get_exchange_info() -> set[str]:
    """Return set of all active USDT spot trading pairs."""
    data = _get("/api/v3/exchangeInfo")
    return {
        s["symbol"]
        for s in data["symbols"]
        if s["quoteAsset"] == "USDT"
        and s["status"] == "TRADING"
        and not s["symbol"].endswith("DOWNUSDT")
        and not s["symbol"].endswith("UPUSDT")
    }
