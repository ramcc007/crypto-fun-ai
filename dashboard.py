"""
Web dashboard for the Crypto Bot.
Run standalone: python dashboard.py
Or it starts automatically alongside the bot.
Open browser at: http://localhost:5000
"""
import threading
from flask import Flask, jsonify, render_template, request
from datetime import datetime, timezone

from bot.portfolio import (
    init_db, get_open_positions, get_trade_history,
    get_today_pnl, get_starting_balance
)
from bot.binance_client import get_current_price, get_usdt_balance
from bot import config

app = Flask(__name__)

# Shared state — updated by the scanner thread
_bot_state = {
    "running": False,
    "mode": "idle",         # idle | scanning | trading
    "dry_run": config.DRY_RUN,
    "last_scan": None,
    "last_scan_count": 0,
    "recent_signals": [],   # last 20 signals found
    "error": None,
}
_state_lock = threading.Lock()


def update_state(**kwargs):
    with _state_lock:
        _bot_state.update(kwargs)


def push_signal(sig_dict: dict):
    with _state_lock:
        _bot_state["recent_signals"].insert(0, sig_dict)
        _bot_state["recent_signals"] = _bot_state["recent_signals"][:20]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    with _state_lock:
        state = dict(_bot_state)

    # Live position data with current prices
    positions = get_open_positions()
    enriched = []
    for p in positions:
        try:
            price = get_current_price(p["symbol"])
            pnl_pct = ((price - p["entry_price"]) / p["entry_price"]) * 100
            pnl_usdt = (price - p["entry_price"]) * p["quantity"]
        except Exception:
            price, pnl_pct, pnl_usdt = p["entry_price"], 0.0, 0.0
        enriched.append({
            **p,
            "current_price": price,
            "pnl_pct": round(pnl_pct, 2),
            "pnl_usdt": round(pnl_usdt, 2),
        })

    # Balance
    try:
        balance = get_usdt_balance()
    except Exception:
        balance = None

    today_pnl = get_today_pnl()
    starting_bal = get_starting_balance()

    return jsonify({
        "bot": state,
        "positions": enriched,
        "balance_usdt": balance,
        "today_pnl": round(today_pnl, 2),
        "starting_balance": starting_bal,
        "settings": {
            "dry_run": config.DRY_RUN,
            "min_score": config.MIN_BUY_SCORE,
            "max_positions": config.MAX_OPEN_POSITIONS,
            "stop_loss_pct": config.STOP_LOSS_PCT,
            "take_profit_pct": config.TAKE_PROFIT_PCT,
            "scan_interval": config.SCAN_INTERVAL_SECONDS,
        },
    })


@app.route("/api/history")
def api_history():
    trades = get_trade_history(50)
    return jsonify(trades)


@app.route("/api/signals")
def api_signals():
    with _state_lock:
        return jsonify(_bot_state["recent_signals"])


def run_dashboard(host="127.0.0.1", port=5000, debug=False):
    init_db()
    app.run(host=host, port=port, debug=debug, use_reloader=False)
