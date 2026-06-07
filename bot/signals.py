"""
Signal scoring engine. Each ticker is scored 0-100.
Higher = stronger buy opportunity. Alerts fire above threshold.
"""
from dataclasses import dataclass, field
from bot import config
from bot.binance_client import get_klines, get_1h_change
from bot.indicators import (
    compute_rsi, compute_macd, compute_bollinger,
    compute_ema_crossover, volume_surge_ratio
)


@dataclass
class Signal:
    symbol: str
    price: float
    change_24h: float
    change_1h: float
    volume_usdt_24h: float
    rsi_1h: float
    macd: dict
    bollinger: dict
    ema: dict
    vol_surge_1h: float
    score: int = 0
    reasons: list[str] = field(default_factory=list)
    signal_types: list[str] = field(default_factory=list)


def score_ticker(ticker: dict) -> Signal | None:
    """
    Returns a Signal if the coin is worth alerting on, else None.
    Scores across 4 categories: dip quality, volume, momentum, technicals.
    """
    symbol = ticker["symbol"]
    price = float(ticker["lastPrice"])
    change_24h = float(ticker["priceChangePercent"])
    volume_usdt = float(ticker["quoteVolume"])

    if volume_usdt < config.MIN_VOLUME_USDT:
        return None

    # Fetch 1h candles for indicators
    try:
        df_1h = get_klines(symbol, "1h", limit=60)
    except Exception:
        return None

    change_1h = get_1h_change(symbol)
    rsi = compute_rsi(df_1h)
    macd = compute_macd(df_1h)
    bb = compute_bollinger(df_1h)
    ema = compute_ema_crossover(df_1h)
    vol_surge = volume_surge_ratio(df_1h)

    score = 0
    reasons = []
    signal_types = []

    # --- DIP DETECTOR ---
    if change_24h <= config.DIP_THRESHOLD_24H:
        score += 25
        signal_types.append("MAJOR_DIP")
        reasons.append(f"Down {change_24h:.1f}% in 24h (major dip)")
    elif change_24h <= (config.DIP_THRESHOLD_24H / 2):
        score += 12
        signal_types.append("DIP")
        reasons.append(f"Down {change_24h:.1f}% in 24h")

    if change_1h <= config.DIP_THRESHOLD_1H:
        score += 15
        if "MAJOR_DIP" not in signal_types:
            signal_types.append("SHARP_DROP_1H")
        reasons.append(f"Down {change_1h:.1f}% in last 1h (sharp drop)")

    # --- OVERSOLD ---
    if rsi < config.RSI_OVERSOLD:
        score += 20
        reasons.append(f"RSI={rsi:.1f} (oversold < {config.RSI_OVERSOLD})")
        if "OVERSOLD" not in signal_types:
            signal_types.append("OVERSOLD")
    elif rsi < 40:
        score += 8
        reasons.append(f"RSI={rsi:.1f} (approaching oversold)")

    # --- BOLLINGER BANDS ---
    if bb["below_lower"]:
        score += 15
        signal_types.append("BELOW_BB_LOWER")
        reasons.append(f"Price below lower Bollinger Band (pct_b={bb['pct_b']:.2f})")
    elif bb["pct_b"] < 0.2:
        score += 7
        reasons.append(f"Price near lower Bollinger Band (pct_b={bb['pct_b']:.2f})")

    # --- VOLUME SURGE ---
    if vol_surge >= config.VOLUME_SURGE_MULTIPLIER:
        score += 20
        signal_types.append("VOLUME_SURGE")
        reasons.append(f"Volume {vol_surge:.1f}x above 20-period average")
    elif vol_surge >= 2.0:
        score += 10
        reasons.append(f"Volume elevated at {vol_surge:.1f}x average")

    # --- MACD CROSSOVER ---
    if macd["crossover"]:
        score += 15
        signal_types.append("MACD_CROSSOVER")
        reasons.append("MACD bullish crossover (momentum turning positive)")
    elif macd["histogram"] > 0 and macd["histogram"] > 0:
        score += 5
        reasons.append("MACD histogram positive (upward momentum)")

    # --- EMA CROSSOVER ---
    if ema["bullish"]:
        score += 10
        signal_types.append("EMA_CROSS")
        reasons.append("EMA9 crossed above EMA21 (trend reversal signal)")

    if score == 0:
        return None

    return Signal(
        symbol=symbol,
        price=price,
        change_24h=change_24h,
        change_1h=change_1h,
        volume_usdt_24h=volume_usdt,
        rsi_1h=rsi,
        macd=macd,
        bollinger=bb,
        ema=ema,
        vol_surge_1h=vol_surge,
        score=score,
        reasons=reasons,
        signal_types=signal_types,
    )
