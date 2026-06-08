import time
import hmac
import hashlib
import requests
import pandas as pd
from bot.config import BINANCE_API_KEY, BINANCE_SECRET_KEY

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


def _signed_get(endpoint: str, params: dict = None) -> dict:
    """Signed GET for private endpoints (account, orders)."""
    params = params or {}
    params["timestamp"] = int(time.time() * 1000)
    query = "&".join(f"{k}={v}" for k, v in params.items())
    sig = hmac.new(BINANCE_SECRET_KEY.encode(), query.encode(), hashlib.sha256).hexdigest()
    url = f"{BASE_URL}{endpoint}?{query}&signature={sig}"
    headers = {"X-MBX-APIKEY": BINANCE_API_KEY}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _signed_post(endpoint: str, params: dict = None) -> dict:
    """Signed POST for placing orders."""
    params = params or {}
    params["timestamp"] = int(time.time() * 1000)
    query = "&".join(f"{k}={v}" for k, v in params.items())
    sig = hmac.new(BINANCE_SECRET_KEY.encode(), query.encode(), hashlib.sha256).hexdigest()
    url = f"{BASE_URL}{endpoint}?{query}&signature={sig}"
    headers = {"X-MBX-APIKEY": BINANCE_API_KEY}
    resp = requests.post(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_usdt_balance() -> float:
    """Returns free USDT balance in spot account."""
    data = _signed_get("/api/v3/account")
    for asset in data.get("balances", []):
        if asset["asset"] == "USDT":
            return float(asset["free"])
    return 0.0


def get_asset_balance(asset: str) -> float:
    """Returns free balance of a specific asset (e.g. 'BTC')."""
    data = _signed_get("/api/v3/account")
    for a in data.get("balances", []):
        if a["asset"] == asset:
            return float(a["free"])
    return 0.0


def get_symbol_info(symbol: str) -> dict:
    """Returns lot size and min notional filters for a symbol."""
    data = _get("/api/v3/exchangeInfo", params={"symbol": symbol})
    info = {"stepSize": "0.01", "minQty": "0.01", "minNotional": 5.0}
    for f in data["symbols"][0]["filters"]:
        if f["filterType"] == "LOT_SIZE":
            info["stepSize"] = f["stepSize"]
            info["minQty"] = f["minQty"]
        if f["filterType"] in ("MIN_NOTIONAL", "NOTIONAL"):
            info["minNotional"] = float(f.get("minNotional", f.get("minNotionalValue", 5)))
    return info


def place_market_buy(symbol: str, usdt_amount: float) -> dict:
    """Place a market buy order using a USDT quote amount."""
    return _signed_post("/api/v3/order", {
        "symbol": symbol,
        "side": "BUY",
        "type": "MARKET",
        "quoteOrderQty": round(usdt_amount, 2),
    })


def place_market_sell(symbol: str, quantity: float, step_size: str) -> dict:
    """Place a market sell order for a given quantity, rounded to step size."""
    qty = _round_step(quantity, step_size)
    return _signed_post("/api/v3/order", {
        "symbol": symbol,
        "side": "SELL",
        "type": "MARKET",
        "quantity": qty,
    })


def get_current_price(symbol: str) -> float:
    """Returns latest price for a symbol."""
    data = _get("/api/v3/ticker/price", params={"symbol": symbol})
    return float(data["price"])


def _round_step(qty: float, step_size: str) -> str:
    """Round quantity down to the exchange's required step size."""
    step = float(step_size)
    if step == 0:
        return str(qty)
    precision = len(step_size.rstrip("0").split(".")[-1]) if "." in step_size else 0
    rounded = int(qty / step) * step
    return f"{rounded:.{precision}f}"


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
