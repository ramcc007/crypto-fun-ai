"""
Main scanning loop. Fetches all USDT tickers, scores each one,
and dispatches alerts for anything above the threshold.
"""
import time
import threading
from datetime import datetime
from colorama import Fore, Style

from bot.binance_client import get_all_usdt_tickers
from bot.signals import score_ticker, Signal
from bot.ai_reasoning import get_reasoning
from bot.alerts import dispatch
from bot.config import SCAN_INTERVAL_SECONDS

# Dedup: don't re-alert the same coin within 1 scan cycle
_alerted_this_cycle: set[str] = set()
# Cooldown: don't alert same coin more than once per hour
_last_alerted: dict[str, float] = {}
COOLDOWN_SECONDS = 3600


def _within_cooldown(symbol: str) -> bool:
    last = _last_alerted.get(symbol, 0)
    return (time.time() - last) < COOLDOWN_SECONDS


def run_scan(min_score: int = 30) -> list[Signal]:
    """Single scan pass. Returns all signals found."""
    global _alerted_this_cycle
    _alerted_this_cycle = set()

    print(f"\n{Fore.CYAN}[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting scan of all USDT pairs...{Style.RESET_ALL}")

    try:
        tickers = get_all_usdt_tickers()
    except Exception as e:
        print(f"{Fore.RED}Failed to fetch tickers: {e}{Style.RESET_ALL}")
        return []

    print(f"  Scanning {len(tickers)} USDT pairs...")

    found: list[Signal] = []
    errors = 0

    for i, ticker in enumerate(tickers):
        symbol = ticker["symbol"]
        if symbol in _alerted_this_cycle or _within_cooldown(symbol):
            continue
        try:
            sig = score_ticker(ticker)
            if sig and sig.score >= min_score:
                found.append(sig)
                _alerted_this_cycle.add(symbol)
                _last_alerted[symbol] = time.time()
        except Exception:
            errors += 1
            continue

        # Progress every 50 coins
        if (i + 1) % 50 == 0:
            print(f"  ... {i+1}/{len(tickers)} scanned, {len(found)} signals so far")

        # Polite rate limiting — Binance allows 1200 req/min on the API
        time.sleep(0.1)

    found.sort(key=lambda s: s.score, reverse=True)

    print(f"\n  Scan complete: {len(found)} opportunities found ({errors} errors)")
    print(f"  Next scan in {SCAN_INTERVAL_SECONDS // 60} minutes\n")

    # Dispatch alerts (AI reasoning added per signal)
    for sig in found:
        reasoning = get_reasoning(sig)
        dispatch(sig, reasoning, min_score=min_score)

    return found


def start_scheduler(min_score: int = 30) -> None:
    """Run the scanner continuously on SCAN_INTERVAL_SECONDS schedule."""
    print(f"{Fore.GREEN}Crypto Opportunity Bot starting...{Style.RESET_ALL}")
    print(f"  Scan interval : every {SCAN_INTERVAL_SECONDS}s")
    print(f"  Min score     : {min_score}/100")
    print(f"  Dip threshold : {__import__('bot.config', fromlist=['DIP_THRESHOLD_24H']).DIP_THRESHOLD_24H}% (24h)")
    print(f"  Volume surge  : {__import__('bot.config', fromlist=['VOLUME_SURGE_MULTIPLIER']).VOLUME_SURGE_MULTIPLIER}x")
    print(f"  RSI oversold  : < {__import__('bot.config', fromlist=['RSI_OVERSOLD']).RSI_OVERSOLD}")
    print()

    while True:
        try:
            run_scan(min_score=min_score)
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Bot stopped by user.{Style.RESET_ALL}")
            break
        except Exception as e:
            print(f"{Fore.RED}Scan error: {e}{Style.RESET_ALL}")

        time.sleep(SCAN_INTERVAL_SECONDS)
