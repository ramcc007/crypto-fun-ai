# crypto-fun-ai — Binance SPOT Opportunity Bot

Monitors all USDT pairs on Binance for buy opportunities using technical analysis.
Alerts via terminal output, email, and log file. No auto-trading — you decide.

## What It Detects

| Signal | Trigger |
|---|---|
| Major Dip | 24h price down >= 20% |
| Sharp Drop | 1h price down >= 10% |
| Oversold | RSI < 30 |
| Below Bollinger Lower Band | Price outside lower BB |
| Volume Surge | Volume >= 3x 20-period average |
| MACD Bullish Crossover | MACD histogram turns positive |
| EMA Crossover | EMA9 crosses above EMA21 |

Signals are scored 0-100. Multiple signals on the same coin = higher score = stronger alert.

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure
```bash
cp .env.example .env
# Edit .env and fill in your keys
```

Required:
- `BINANCE_API_KEY` + `BINANCE_SECRET_KEY` — Read-only keys from binance.com -> API Management

Optional but recommended:
- Gmail app password for email alerts
- `ANTHROPIC_API_KEY` for AI-powered plain-English reasoning per alert

### 3. Run

```bash
# Continuous scanning (every 5 minutes by default)
python main.py

# Single scan and exit
python main.py --once

# Only show high-confidence signals (score 50+)
python main.py --score 50
```

## Output

Each alert shows:
- Coin, price, 24h/1h % change
- Which signals triggered
- Volume surge ratio
- RSI, Bollinger %B
- AI reasoning (if Anthropic API key provided)
- Score out of 100

Alerts are also logged to `logs/alerts.log` and emailed if configured.

## Tuning (in .env)

| Setting | Default | Meaning |
|---|---|---|
| `SCAN_INTERVAL_SECONDS` | 300 | Scan every 5 min |
| `DIP_THRESHOLD_24H` | -20.0 | Major dip threshold |
| `DIP_THRESHOLD_1H` | -10.0 | Sharp hourly drop |
| `VOLUME_SURGE_MULTIPLIER` | 3.0 | Volume spike multiplier |
| `RSI_OVERSOLD` | 30 | Oversold RSI level |
| `MIN_VOLUME_USDT` | 500000 | Ignore low-liquidity coins |

## Disclaimer

This tool is for informational purposes only. It does not constitute financial advice.
Crypto trading involves significant risk. Always do your own research.
