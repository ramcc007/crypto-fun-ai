#!/usr/bin/env python3
"""
Crypto Opportunity Bot — SPOT trading signals + auto-trading + web dashboard.

Usage:
  python main.py                  # alert-only mode + dashboard
  python main.py --trade          # auto-trade dry run + dashboard
  python main.py --trade --live   # LIVE trading (real money)
  python main.py --once           # single scan, no dashboard
  python main.py --no-dashboard   # skip the web dashboard
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
    parser.add_argument("--no-dashboard", action="store_true", help="Disable web dashboard")
    parser.add_argument("--score", type=int, default=None, help="Minimum signal score")
    parser.add_argument("--positions", action="store_true", help="Show open positions and exit")
    parser.add_argument("--history", action="store_true", help="Show trade history and exit")
    args = parser.parse_args()

    # --positions
    if args.positions:
        from bot.portfolio import get_open_positions
        from bot.binance_client import get_current_price
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
                    print(f"{p['symbol']:<14} {p['entry_price']:>10.6f} {'?':>10}")
        return

    # --history
    if args.history:
        from bot.portfolio import get_trade_history
        trades = get_trade_history(30)
        if not trades:
            print("No trade history yet.")
        else:
            print(f"\n{'Symbol':<14} {'Entry':>10} {'Exit':>10} {'PnL':>10} {'PnL%':>8} {'Reason':<20} {'Closed'}")
            print("-" * 100)
            for t in trades:
                tag = "[DRY]" if t["dry_run"] else "[LIVE]"
                print(f"{t['symbol']:<14} {t['entry_price']:>10.6f} {t['exit_price']:>10.6f} "
                      f"{t['pnl_usdt']:>+10.2f} {t['pnl_pct']:>+8.2f}% {t['reason']:<20} {t['closed_at'][:19]} {tag}")
        return

    # Enable live mode
    if args.live and args.trade:
        os.environ["DRY_RUN"] = "false"
        from bot import config
        config.DRY_RUN = False
        print("WARNING: LIVE MODE — real orders will be placed on Binance")

    from bot import config
    min_score = args.score if args.score is not None else config.MIN_BUY_SCORE

    if args.once:
        from bot.scanner import run_scan
        run_scan(min_score=min_score, auto_trade=args.trade)
        return

    # Start dashboard in background thread
    if not args.no_dashboard:
        import dashboard as dash
        dash.update_state(running=True, dry_run=config.DRY_RUN,
                          mode="trading" if args.trade else "scanning")
        from bot.scanner import set_dashboard
        set_dashboard(dash)

        t_dash = threading.Thread(
            target=dash.run_dashboard,
            kwargs={"host": "127.0.0.1", "port": 5000},
            daemon=True
        )
        t_dash.start()
        print("\n  Dashboard: http://localhost:5000  (open in your browser)\n")

    # Start position monitor in background if trading
    if args.trade:
        from bot.monitor import run_monitor
        t_mon = threading.Thread(target=run_monitor, daemon=True)
        t_mon.start()

    from bot.scanner import start_scheduler
    start_scheduler(min_score=min_score, auto_trade=args.trade)


if __name__ == "__main__":
    main()
