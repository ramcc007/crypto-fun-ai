"""
Monitors open positions every N seconds.
Triggers stop loss, take profit, or time-based exits.
"""
import time
from datetime import datetime, timezone
from colorama import Fore, Style

from bot import config
from bot.portfolio import get_open_positions
from bot.binance_client import get_current_price
from bot.trader import execute_sell


def check_positions():
    positions = get_open_positions()
    if not positions:
        return

    now = datetime.now(timezone.utc)
    print(f"\n  [Monitor] Checking {len(positions)} open position(s)...")

    for pos in positions:
        symbol = pos["symbol"]
        try:
            price = get_current_price(symbol)
        except Exception as e:
            print(f"  [Monitor] Could not get price for {symbol}: {e}")
            continue

        pnl_pct = ((price - pos["entry_price"]) / pos["entry_price"]) * 100
        color = Fore.GREEN if pnl_pct >= 0 else Fore.RED
        print(f"    {symbol}: ${price:.6f}  {color}{pnl_pct:+.2f}%{Style.RESET_ALL}  "
              f"(SL: ${pos['stop_loss']:.6f} | TP: ${pos['take_profit']:.6f})")

        # Stop loss
        if price <= pos["stop_loss"]:
            execute_sell(pos, price, f"STOP_LOSS ({pnl_pct:.2f}%)")
            continue

        # Take profit
        if price >= pos["take_profit"]:
            execute_sell(pos, price, f"TAKE_PROFIT ({pnl_pct:.2f}%)")
            continue

        # Time-based exit — held too long with no significant move
        opened = datetime.fromisoformat(pos["opened_at"]).replace(tzinfo=timezone.utc)
        hours_held = (now - opened).total_seconds() / 3600
        if hours_held >= config.MAX_HOLD_HOURS:
            execute_sell(pos, price, f"TIME_EXIT ({hours_held:.1f}h held, {pnl_pct:.2f}%)")


def run_monitor():
    """Blocking loop that checks positions on MONITOR_INTERVAL_SECONDS schedule."""
    print(f"  [Monitor] Started — checking every {config.MONITOR_INTERVAL_SECONDS}s")
    while True:
        try:
            check_positions()
        except Exception as e:
            print(f"  [Monitor] Error: {e}")
        time.sleep(config.MONITOR_INTERVAL_SECONDS)
