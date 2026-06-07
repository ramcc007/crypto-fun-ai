import pandas as pd
import ta


def compute_rsi(df: pd.DataFrame, period: int = 14) -> float:
    if len(df) < period + 1:
        return 50.0
    rsi = ta.momentum.RSIIndicator(df["close"], window=period).rsi()
    val = rsi.iloc[-1]
    return float(val) if not pd.isna(val) else 50.0


def compute_macd(df: pd.DataFrame) -> dict:
    if len(df) < 26:
        return {"macd": 0.0, "signal": 0.0, "histogram": 0.0, "crossover": False}
    macd_ind = ta.trend.MACD(df["close"])
    hist = macd_ind.macd_diff()
    macd_line = macd_ind.macd()
    signal_line = macd_ind.macd_signal()
    hist_val = float(hist.iloc[-1] or 0)
    prev_hist = float(hist.iloc[-2] or 0)
    crossover = prev_hist < 0 and hist_val > 0
    return {
        "macd": float(macd_line.iloc[-1] or 0),
        "signal": float(signal_line.iloc[-1] or 0),
        "histogram": hist_val,
        "crossover": crossover,
    }


def compute_bollinger(df: pd.DataFrame) -> dict:
    if len(df) < 20:
        return {"upper": 0, "mid": 0, "lower": 0, "pct_b": 0.5, "below_lower": False}
    bb = ta.volatility.BollingerBands(df["close"], window=20)
    upper = float(bb.bollinger_hband().iloc[-1])
    mid = float(bb.bollinger_mavg().iloc[-1])
    lower = float(bb.bollinger_lband().iloc[-1])
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
    if len(df) < 22:
        return {"ema9": 0, "ema21": 0, "bullish": False}
    ema9 = ta.trend.EMAIndicator(df["close"], window=9).ema_indicator()
    ema21 = ta.trend.EMAIndicator(df["close"], window=21).ema_indicator()
    e9, e21 = float(ema9.iloc[-1]), float(ema21.iloc[-1])
    prev_e9, prev_e21 = float(ema9.iloc[-2]), float(ema21.iloc[-2])
    bullish_cross = (prev_e9 < prev_e21) and (e9 > e21)
    return {"ema9": round(e9, 6), "ema21": round(e21, 6), "bullish": bullish_cross}


def volume_surge_ratio(df: pd.DataFrame, lookback: int = 20) -> float:
    if len(df) < lookback + 1:
        return 1.0
    avg_vol = df["volume"].iloc[-(lookback + 1):-1].mean()
    curr_vol = df["volume"].iloc[-1]
    return round(float(curr_vol / avg_vol), 2) if avg_vol > 0 else 1.0
