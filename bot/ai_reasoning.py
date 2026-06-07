"""
Uses Claude to produce a plain-English trading rationale for a signal.
Falls back to a rule-based summary if no API key is configured.
"""
from bot.config import ANTHROPIC_API_KEY
from bot.signals import Signal


def _rule_based_summary(sig: Signal) -> str:
    lines = [f"{sig.symbol} is showing {len(sig.signal_types)} buy signal(s):"]
    for r in sig.reasons:
        lines.append(f"  • {r}")
    lines.append("")
    if sig.score >= 60:
        lines.append("Strength: STRONG — multiple confluence signals. Worth serious attention.")
    elif sig.score >= 35:
        lines.append("Strength: MODERATE — a few signals aligning. Monitor closely.")
    else:
        lines.append("Strength: WEAK — early signal, not yet confirmed by multiple indicators.")
    lines.append("")
    lines.append("⚠ This is not financial advice. Always do your own research before buying.")
    return "\n".join(lines)


def get_reasoning(sig: Signal) -> str:
    if not ANTHROPIC_API_KEY:
        return _rule_based_summary(sig)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        prompt = f"""You are a crypto trading analyst. A scanner found a potential SPOT buy opportunity.
Analyze these signals and give a concise, plain-English explanation (5-8 sentences) of:
1. Why this might be a good buying opportunity
2. What risks to watch out for
3. What confirmation to wait for before buying

Coin: {sig.symbol}
Current Price: ${sig.price}
24h Change: {sig.change_24h:.1f}%
1h Change: {sig.change_1h:.1f}%
24h Volume (USDT): ${sig.volume_usdt_24h:,.0f}
RSI (1h): {sig.rsi_1h:.1f}
MACD Histogram: {sig.macd['histogram']:.6f} (crossover: {sig.macd['crossover']})
Bollinger %B: {sig.bollinger['pct_b']} (below lower band: {sig.bollinger['below_lower']})
EMA9 vs EMA21: {sig.ema['ema9']} vs {sig.ema['ema21']} (bullish cross: {sig.ema['bullish']})
Volume surge: {sig.vol_surge_1h:.1f}x above average
Signal score: {sig.score}/100
Triggered signals: {', '.join(sig.signal_types)}

End your response with one line: "ACTION: [WATCH / CONSIDER BUYING / STRONG BUY]" """

        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )
        return msg.content[0].text
    except Exception as e:
        return _rule_based_summary(sig) + f"\n(AI reasoning unavailable: {e})"
