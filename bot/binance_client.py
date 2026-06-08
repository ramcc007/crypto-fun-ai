import time
import requests
import pandas as pd
from bot.config import BINANCE_API_KEY

BASE_URL = "https://api.binance.com"

# Cached at startup — refreshed every 6 hours
_active_spot_pairs: set[str] = set()
_pairs_fetched_at: float = 0
_PAIRS_TTL = 6 * 3600


def _get(endpoint: str, params: dict = None) -> dict | list:
    url = f"{BASE_URL}{endpoint}"
    headers = {"X-MBX-APIKEY": BINANCE_API_KEY} if BINANCE_API_KEY else {}
    resp = requests.get(url, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_active_spot_pairs() -> set[str]:
    """
    Returns the set of USDT pairs currently in TRADING status on Binance spot.
    Cached for 6 hours to avoid hammering the endpoint.
    """
    global _active_spot_pairs, _pairs_fetched_at
    if _active_spot_pairs and (time.time() - _pairs_fetched_at) < _PAIRS_TTL:
        return _active_spot_pairs

    data = _get("/api/v3/exchangeInfo")
    pairs = set()
    for s in data["symbols"]:
        if (
            s["quoteAsset"] == "USDT"
            and s["status"] == "TRADING"
            and s["isSpotTradingAllowed"]
            and not s["symbol"].endswith("DOWNUSDT")
            and not s["symbol"].endswith("UPUSDT")
            and not s["symbol"].endswith("BULLUSDT")
            and not s["symbol"].endswith("BEARUSDT")
        ):
            pairs.add(s["symbol"])

    _active_spot_pairs = pairs
    _pairs_fetched_at = time.time()
    print(f"  [Exchange] {len(pairs)} active USDT spot pairs loaded from Binance")
    return pairs


def get_all_usdt_tickers() -> list[dict]:
    """
    Fetch 24h stats for USDT pairs, pre-filtered to only currently
    active spot-tradeable symbols verified against exchangeInfo.
    """
    active = get_active_spot_pairs()
    data = _get("/api/v3/ticker/24hr")
    return [t for t in data if t["symbol"] in active]


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
