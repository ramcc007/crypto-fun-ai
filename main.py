#!/usr/bin/env python3
"""
Crypto Opportunity Bot — SPOT trading signals + auto-trading.

Usage:
  python main.py                  # alert-only mode, no trades
  python main.py --trade          # auto-trade (dry run by default)
  python main.py --trade --live   # LIVE trading (real money)
  python main.py --once           # single scan, alert only
  python main.py --once --trade   # single scan with auto-trade
  python main.py --score 60       # override minimum score
  python main.py --positions      # show open positions and exit
  python main.py --history        # show recent trade history and exit
"""
import argparse
import threading
import os

from bot.portfolio import init_db


def main():
    init_db()

    parser = argparse.ArgumentParser(description="Crypto SPOT Opportunity Bot")
    parser.add_argument("--once", action="store_true", help="Run one scan and exit")
    parser.add_argument("--trade", action="store_true", help="Enable auto-trading")
    parser.add_argument("--live", action="store_true", help="Use real money (disables dry run)")
    parser.add_argument("--score", type=int, default=None, help="Minimum signal score (default from .env)")
    parser.add_argument("--positions", action="store_true", help="Show open positions and exit")
    parser.add_argument("--history", action="store_true", help="Show trade history and exit")
    args = parser.parse_args()

    # --positions
    if args.positions:
        from bot.portfolio import get_open_positions
        from bot.binance_client import get_current_price
        from bot.config import DRY_RUN
        positions = get_open_positions()
        if not positions:
            print("No open positions.")
        else:
            print(f"\n{'Symbol':<14} {'Entry':>10} {'Current':>10} {'PnL%':>8} {'SL':>10} {'TP':>10} {'Mode'}")
            print("-" * 75)
            for p in positions:
                try:
                    price = get_current_price(p["symbol"])
                    pnl = ((price - p["entry_price"]) / p["entry_price"]) * 100
                    tag = "DRY" if p["dry_run"] else "LIVE"
                    print(f"{p['symbol']:<14} {p['entry_price']:>10.6f} {price:>10.6f} {pnl:>+8.2f}% {p['stop_loss']:>10.6f} {p['take_profit']:>10.6f} {tag}")
                except Exception:
                    print(f"{p['symbol']:<14} {p['entry_price']:>10.6f} {'?':>10} {'?':>8} {p['stop_loss']:>10.6f} {p['take_profit']:>10.6f}")
        return

    # --history
    if args.history:
        from bot.portfolio import get_trade_history
        trades = get_trade_history(30)
        if not trades:
            print("No trade history yet.")
        else:
            print(f"\n{'Symbol':<14} {'Entry':>10} {'Exit':>10} {'PnL USDT':>10} {'PnL%':>8} {'Reason':<20} {'Closed At'}")
            print("-" * 100)
            for t in trades:
                tag = "[DRY]" if t["dry_run"] else "[LIVE]"
                print(f"{t['symbol']:<14} {t['entry_price']:>10.6f} {t['exit_price']:>10.6f} "
                      f"{t['pnl_usdt']:>+10.2f} {t['pnl_pct']:>+8.2f}% {t['reason']:<20} {t['closed_at'][:19]} {tag}")
        return

    # Override dry run if --live passed
    if args.live and args.trade:
        os.environ["DRY_RUN"] = "false"
        from bot import config
        config.DRY_RUN = False
        print("⚠  LIVE MODE ENABLED — real orders will be placed on Binance")

    from bot import config
    min_score = args.score if args.score is not None else config.MIN_BUY_SCORE

    if args.once:
        from bot.scanner import run_scan
        run_scan(min_score=min_score, auto_trade=args.trade)
    else:
        from bot.scanner import start_scheduler
        from bot.monitor import run_monitor

        if args.trade:
            # Run monitor in a background thread alongside the scanner
            t = threading.Thread(target=run_monitor, daemon=True)
            t.start()

        start_scheduler(min_score=min_score, auto_trade=args.trade)


if __name__ == "__main__":
    main()
