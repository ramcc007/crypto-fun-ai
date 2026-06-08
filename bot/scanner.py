"""
Main scanning loop. Fetches all USDT tickers, scores each one,
dispatches alerts, and triggers auto-buys when enabled.
"""
import time
from datetime import datetime
from colorama import Fore, Style

from bot.binance_client import get_all_usdt_tickers
from bot.signals import score_ticker, Signal
from bot.ai_reasoning import get_reasoning
from bot.alerts import dispatch
from bot import config
from bot.trader import execute_buy

_alerted_this_cycle: set[str] = set()
_last_alerted: dict[str, float] = {}
COOLDOWN_SECONDS = 3600


def _within_cooldown(symbol: str) -> bool:
    return (time.time() - _last_alerted.get(symbol, 0)) < COOLDOWN_SECONDS


def run_scan(min_score: int = 30, auto_trade: bool = False) -> list[Signal]:
    global _alerted_this_cycle
    _alerted_this_cycle = set()

    mode = f"{'[DRY RUN] ' if config.DRY_RUN else '[LIVE] '}Auto-trade ON" if auto_trade else "Alert only"
    print(f"\n{Fore.CYAN}[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Scan started  |  {mode}{Style.RESET_ALL}")

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

        if (i + 1) % 50 == 0:
            print(f"  ... {i+1}/{len(tickers)} scanned, {len(found)} signals so far")

        time.sleep(0.1)

    found.sort(key=lambda s: s.score, reverse=True)
    print(f"\n  Scan complete: {len(found)} opportunities ({errors} errors)")
    print(f"  Next scan in {config.SCAN_INTERVAL_SECONDS // 60} minutes\n")

    for sig in found:
        reasoning = get_reasoning(sig)
        dispatch(sig, reasoning, min_score=min_score)
        if auto_trade:
            execute_buy(sig)

    return found


def start_scheduler(min_score: int = 30, auto_trade: bool = False) -> None:
    from bot import config as cfg
    tag = f"{'[DRY RUN] ' if cfg.DRY_RUN else '[LIVE] '}" if auto_trade else ""
    print(f"{Fore.GREEN}{tag}Crypto Bot starting...{Style.RESET_ALL}")
    print(f"  Auto-trade    : {'YES (' + ('DRY RUN' if cfg.DRY_RUN else 'LIVE ORDERS') + ')' if auto_trade else 'NO (alert only)'}")
    print(f"  Scan interval : every {cfg.SCAN_INTERVAL_SECONDS}s")
    print(f"  Min buy score : {cfg.MIN_BUY_SCORE}/100")
    print(f"  Max positions : {cfg.MAX_OPEN_POSITIONS}")
    print(f"  Stop loss     : {cfg.STOP_LOSS_PCT}%")
    print(f"  Take profit   : +{cfg.TAKE_PROFIT_PCT}%")
    print(f"  Daily loss cap: {cfg.DAILY_LOSS_CAP_PCT*100:.0f}% of starting balance")
    print()

    while True:
        try:
            run_scan(min_score=min_score, auto_trade=auto_trade)
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Bot stopped.{Style.RESET_ALL}")
            break
        except Exception as e:
            print(f"{Fore.RED}Scan error: {e}{Style.RESET_ALL}")

        time.sleep(config.SCAN_INTERVAL_SECONDS)
