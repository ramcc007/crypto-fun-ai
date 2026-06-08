"""
SQLite-backed position and trade tracker.
Tracks open positions and full trade history.
"""
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "trades.db")


def _conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                entry_price REAL NOT NULL,
                quantity REAL NOT NULL,
                usdt_spent REAL NOT NULL,
                stop_loss REAL NOT NULL,
                take_profit REAL NOT NULL,
                opened_at TEXT NOT NULL,
                step_size TEXT DEFAULT '0.01',
                dry_run INTEGER DEFAULT 0
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL,
                exit_price REAL,
                quantity REAL NOT NULL,
                usdt_spent REAL,
                pnl_usdt REAL,
                pnl_pct REAL,
                reason TEXT,
                opened_at TEXT,
                closed_at TEXT,
                dry_run INTEGER DEFAULT 0
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                starting_balance REAL,
                realized_pnl REAL DEFAULT 0.0,
                trades_count INTEGER DEFAULT 0
            )
        """)


def open_position(symbol: str, entry_price: float, quantity: float,
                  usdt_spent: float, stop_loss: float, take_profit: float,
                  step_size: str = "0.01", dry_run: bool = True):
    with _conn() as c:
        c.execute("""
            INSERT INTO positions (symbol, entry_price, quantity, usdt_spent,
                stop_loss, take_profit, opened_at, step_size, dry_run)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (symbol, entry_price, quantity, usdt_spent, stop_loss,
              take_profit, datetime.utcnow().isoformat(), step_size, int(dry_run)))


def get_open_positions() -> list[dict]:
    with _conn() as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("SELECT * FROM positions").fetchall()
        return [dict(r) for r in rows]


def get_position(symbol: str) -> dict | None:
    with _conn() as c:
        c.row_factory = sqlite3.Row
        row = c.execute("SELECT * FROM positions WHERE symbol=?", (symbol,)).fetchone()
        return dict(row) if row else None


def close_position(symbol: str, exit_price: float, reason: str, dry_run: bool = True):
    pos = get_position(symbol)
    if not pos:
        return
    pnl_usdt = (exit_price - pos["entry_price"]) * pos["quantity"]
    pnl_pct = ((exit_price - pos["entry_price"]) / pos["entry_price"]) * 100
    with _conn() as c:
        c.execute("""
            INSERT INTO trades (symbol, side, entry_price, exit_price, quantity,
                usdt_spent, pnl_usdt, pnl_pct, reason, opened_at, closed_at, dry_run)
            VALUES (?, 'SELL', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (symbol, pos["entry_price"], exit_price, pos["quantity"],
              pos["usdt_spent"], pnl_usdt, pnl_pct, reason,
              pos["opened_at"], datetime.utcnow().isoformat(), int(dry_run)))
        c.execute("DELETE FROM positions WHERE symbol=?", (symbol,))
        # Update daily stats
        today = datetime.utcnow().date().isoformat()
        c.execute("""
            INSERT INTO daily_stats (date, starting_balance, realized_pnl, trades_count)
            VALUES (?, 0, ?, 1)
            ON CONFLICT(date) DO UPDATE SET
                realized_pnl = realized_pnl + ?,
                trades_count = trades_count + 1
        """, (today, pnl_usdt, pnl_usdt))
    return pnl_usdt, pnl_pct


def count_open_positions() -> int:
    with _conn() as c:
        return c.execute("SELECT COUNT(*) FROM positions").fetchone()[0]


def is_holding(symbol: str) -> bool:
    return get_position(symbol) is not None


def get_today_pnl() -> float:
    today = datetime.utcnow().date().isoformat()
    with _conn() as c:
        row = c.execute(
            "SELECT realized_pnl FROM daily_stats WHERE date=?", (today,)
        ).fetchone()
        return float(row[0]) if row else 0.0


def set_starting_balance(balance: float):
    today = datetime.utcnow().date().isoformat()
    with _conn() as c:
        c.execute("""
            INSERT INTO daily_stats (date, starting_balance, realized_pnl, trades_count)
            VALUES (?, ?, 0, 0)
            ON CONFLICT(date) DO UPDATE SET starting_balance = ?
            WHERE starting_balance = 0
        """, (today, balance, balance))


def get_starting_balance() -> float:
    today = datetime.utcnow().date().isoformat()
    with _conn() as c:
        row = c.execute(
            "SELECT starting_balance FROM daily_stats WHERE date=?", (today,)
        ).fetchone()
        return float(row[0]) if row else 0.0


def get_trade_history(limit: int = 20) -> list[dict]:
    with _conn() as c:
        c.row_factory = sqlite3.Row
        rows = c.execute(
            "SELECT * FROM trades ORDER BY closed_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
