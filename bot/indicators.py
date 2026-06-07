import pandas as pd
import pandas_ta as ta


def compute_rsi(df: pd.DataFrame, period: int = 14) -> float:
    """Returns latest RSI value."""
    if len(df) < period + 1:
        return 50.0
    rsi = ta.rsi(df["close"], length=period)
    val = rsi.iloc[-1]
    return float(val) if not pd.isna(val) else 50.0


def compute_macd(df: pd.DataFrame) -> dict:
    """Returns MACD line, signal line, and histogram for latest candle."""
    if len(df) < 26:
        return {"macd": 0.0, "signal": 0.0, "histogram": 0.0, "crossover": False}
    macd_df = ta.macd(df["close"])
    if macd_df is None or macd_df.empty:
        return {"macd": 0.0, "signal": 0.0, "histogram": 0.0, "crossover": False}
    macd_col = [c for c in macd_df.columns if c.startswith("MACD_")][0]
    signal_col = [c for c in macd_df.columns if c.startswith("MACDs_")][0]
    hist_col = [c for c in macd_df.columns if c.startswith("MACDh_")][0]

    macd_val = float(macd_df[macd_col].iloc[-1] or 0)
    signal_val = float(macd_df[signal_col].iloc[-1] or 0)
    hist_val = float(macd_df[hist_col].iloc[-1] or 0)
    prev_hist = float(macd_df[hist_col].iloc[-2] or 0)

    # Bullish crossover: histogram just turned positive
    crossover = prev_hist < 0 and hist_val > 0

    return {"macd": macd_val, "signal": signal_val, "histogram": hist_val, "crossover": crossover}


def compute_bollinger(df: pd.DataFrame) -> dict:
    """Returns upper, middle, lower bands and position of price within bands."""
    if len(df) < 20:
        return {"upper": 0, "mid": 0, "lower": 0, "pct_b": 0.5, "below_lower": False}
    bb = ta.bbands(df["close"], length=20)
    if bb is None or bb.empty:
        return {"upper": 0, "mid": 0, "lower": 0, "pct_b": 0.5, "below_lower": False}
    upper = float(bb.iloc[-1, 0])
    mid = float(bb.iloc[-1, 1])
    lower = float(bb.iloc[-1, 2])
    price = float(df["close"].iloc[-1])
    band_width = upper - lower
    pct_b = (price - lower) / band_width if band_width > 0 else 0.5
    return {
        "upper": upper,
        "mid": mid,
        "lower": lower,
        "pct_b": round(pct_b, 3),
        "below_lower": price < lower,
    }


def compute_ema_crossover(df: pd.DataFrame) -> dict:
    """EMA9 / EMA21 crossover signal."""
    if len(df) < 22:
        return {"ema9": 0, "ema21": 0, "bullish": False}
    ema9 = ta.ema(df["close"], length=9)
    ema21 = ta.ema(df["close"], length=21)
    e9 = float(ema9.iloc[-1])
    e21 = float(ema21.iloc[-1])
    prev_e9 = float(ema9.iloc[-2])
    prev_e21 = float(ema21.iloc[-2])
    # Just crossed above
    bullish_cross = (prev_e9 < prev_e21) and (e9 > e21)
    return {"ema9": round(e9, 6), "ema21": round(e21, 6), "bullish": bullish_cross}


def volume_surge_ratio(df: pd.DataFrame, lookback: int = 20) -> float:
    """Current volume vs average of last N candles (excluding current)."""
    if len(df) < lookback + 1:
        return 1.0
    avg_vol = df["volume"].iloc[-(lookback + 1):-1].mean()
    curr_vol = df["volume"].iloc[-1]
    return round(float(curr_vol / avg_vol), 2) if avg_vol > 0 else 1.0
