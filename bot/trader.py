"""
Executes buy and sell decisions.
DRY_RUN=true  → simulates everything, no real orders placed.
DRY_RUN=false → live trading via Binance API.
"""
from datetime import datetime
from colorama import Fore, Style

from bot import config
from bot.signals import Signal
from bot import portfolio
from bot.binance_client import (
    get_usdt_balance, get_symbol_info, get_current_price,
    place_market_buy, place_market_sell
)


def _tag() -> str:
    return f"[{'DRY RUN' if config.DRY_RUN else 'LIVE'}]"


def _usdt_per_trade(balance: float) -> float:
    """
    Each trade gets an equal share of the allocated balance.
    Allocation = 50% of balance split across MAX_OPEN_POSITIONS slots.
    """
    per_slot = (balance * config.BALANCE_ALLOCATION_PCT) / config.MAX_OPEN_POSITIONS
    return round(per_slot, 2)


def should_buy(sig: Signal) -> tuple[bool, str]:
    """Returns (True, reason) or (False, reason) for a buy decision."""
    if sig.score < config.MIN_BUY_SCORE:
        return False, f"Score {sig.score} below threshold {config.MIN_BUY_SCORE}"

    if portfolio.count_open_positions() >= config.MAX_OPEN_POSITIONS:
        return False, f"Max positions ({config.MAX_OPEN_POSITIONS}) already open"

    if portfolio.is_holding(sig.symbol):
        return False, f"Already holding {sig.symbol}"

    # Daily loss cap check
    starting_bal = portfolio.get_starting_balance()
    if starting_bal > 0:
        today_pnl = portfolio.get_today_pnl()
        loss_cap = starting_bal * config.DAILY_LOSS_CAP_PCT
        if today_pnl <= -loss_cap:
            return False, f"Daily loss cap hit (${abs(today_pnl):.2f} lost today)"

    return True, "All checks passed"


def execute_buy(sig: Signal) -> bool:
    """Places a buy order (or simulates one in dry run). Returns True if successful."""
    ok, reason = should_buy(sig)
    if not ok:
        print(f"  {_tag()} SKIP {sig.symbol}: {reason}")
        return False

    try:
        if config.DRY_RUN:
            balance = get_usdt_balance() if config.BINANCE_API_KEY else 1000.0
        else:
            balance = get_usdt_balance()
    except Exception as e:
        print(f"  {_tag()} Could not fetch balance: {e}")
        balance = 0.0

    if balance < 10:
        print(f"  {_tag()} SKIP {sig.symbol}: insufficient USDT balance (${balance:.2f})")
        return False

    portfolio.set_starting_balance(balance)
    usdt_amount = _usdt_per_trade(balance)

    if usdt_amount < 5:
        print(f"  {_tag()} SKIP {sig.symbol}: trade size ${usdt_amount:.2f} too small (min $5)")
        return False

    entry_price = sig.price
    stop_loss_price = entry_price * (1 + config.STOP_LOSS_PCT / 100)
    take_profit_price = entry_price * (1 + config.TAKE_PROFIT_PCT / 100)
    step_size = "0.01"

    if config.DRY_RUN:
        quantity = usdt_amount / entry_price
        print(
            f"\n  {Fore.YELLOW}{_tag()} BUY {sig.symbol}{Style.RESET_ALL}\n"
            f"    Amount   : ${usdt_amount:.2f} USDT\n"
            f"    Price    : ${entry_price}\n"
            f"    Quantity : {quantity:.6f}\n"
            f"    Stop loss: ${stop_loss_price:.6f} ({config.STOP_LOSS_PCT}%)\n"
            f"    Target   : ${take_profit_price:.6f} (+{config.TAKE_PROFIT_PCT}%)\n"
            f"    Score    : {sig.score}/100  Signals: {', '.join(sig.signal_types)}"
        )
    else:
        try:
            sym_info = get_symbol_info(sig.symbol)
            step_size = sym_info["stepSize"]
            order = place_market_buy(sig.symbol, usdt_amount)
            fills = order.get("fills", [])
            if fills:
                total_qty = sum(float(f["qty"]) for f in fills)
                total_cost = sum(float(f["qty"]) * float(f["price"]) for f in fills)
                entry_price = total_cost / total_qty if total_qty else entry_price
                quantity = total_qty
            else:
                quantity = usdt_amount / entry_price
            stop_loss_price = entry_price * (1 + config.STOP_LOSS_PCT / 100)
            take_profit_price = entry_price * (1 + config.TAKE_PROFIT_PCT / 100)
            print(
                f"\n  {Fore.GREEN}{_tag()} BUY EXECUTED {sig.symbol}{Style.RESET_ALL}\n"
                f"    Spent    : ${usdt_amount:.2f} USDT\n"
                f"    Avg price: ${entry_price:.6f}\n"
                f"    Quantity : {quantity:.6f}\n"
                f"    Stop loss: ${stop_loss_price:.6f}\n"
                f"    Target   : ${take_profit_price:.6f}"
            )
        except Exception as e:
            print(f"  {Fore.RED}{_tag()} BUY FAILED {sig.symbol}: {e}{Style.RESET_ALL}")
            return False

    portfolio.open_position(
        symbol=sig.symbol,
        entry_price=entry_price,
        quantity=quantity,
        usdt_spent=usdt_amount,
        stop_loss=stop_loss_price,
        take_profit=take_profit_price,
        step_size=step_size,
        dry_run=config.DRY_RUN,
    )
    return True


def execute_sell(pos: dict, current_price: float, reason: str) -> float | None:
    """Sells an open position. Returns PnL in USDT."""
    symbol = pos["symbol"]
    pnl_pct = ((current_price - pos["entry_price"]) / pos["entry_price"]) * 100
    pnl_usdt = (current_price - pos["entry_price"]) * pos["quantity"]
    color = Fore.GREEN if pnl_usdt >= 0 else Fore.RED

    if config.DRY_RUN:
        print(
            f"\n  {Fore.YELLOW}[DRY RUN] SELL {symbol}{Style.RESET_ALL}  ({reason})\n"
            f"    Entry  : ${pos['entry_price']:.6f}\n"
            f"    Exit   : ${current_price:.6f}\n"
            f"    PnL    : {color}${pnl_usdt:+.2f} ({pnl_pct:+.2f}%){Style.RESET_ALL}"
        )
    else:
        try:
            place_market_sell(symbol, pos["quantity"], pos["step_size"])
            print(
                f"\n  {color}[LIVE] SELL {symbol}{Style.RESET_ALL}  ({reason})\n"
                f"    Entry  : ${pos['entry_price']:.6f}\n"
                f"    Exit   : ${current_price:.6f}\n"
                f"    PnL    : {color}${pnl_usdt:+.2f} ({pnl_pct:+.2f}%){Style.RESET_ALL}"
            )
        except Exception as e:
            print(f"  {Fore.RED}[LIVE] SELL FAILED {symbol}: {e}{Style.RESET_ALL}")
            return None

    portfolio.close_position(symbol, current_price, reason, dry_run=config.DRY_RUN)
    return pnl_usdt
