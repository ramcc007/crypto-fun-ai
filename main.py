#!/usr/bin/env python3
"""
Crypto Opportunity Bot — SPOT trading signals only.
Usage:
  python main.py              # start continuous scanning
  python main.py --once       # single scan pass, then exit
  python main.py --score 50   # only alert signals scoring 50+
"""
import argparse
from bot.scanner import run_scan, start_scheduler


def main():
    parser = argparse.ArgumentParser(description="Crypto SPOT Opportunity Bot")
    parser.add_argument("--once", action="store_true", help="Run one scan and exit")
    parser.add_argument("--score", type=int, default=30, help="Minimum signal score to alert (0-100)")
    args = parser.parse_args()

    if args.once:
        signals = run_scan(min_score=args.score)
        print(f"\nFound {len(signals)} signal(s) with score >= {args.score}")
    else:
        start_scheduler(min_score=args.score)


if __name__ == "__main__":
    main()
