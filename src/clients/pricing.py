"""
pricing.py — per-provider token cost (§18 cost/token logging).

Token counts are logged on EVERY call from the real API usage response (the true
measurement the pilot needs). USD cost = tokens x price. NATIVE-API prices are
PENDING_SIGNOFF — confirm current per-1M prices for each provider before relying
on cost figures; until then compute_cost returns None and only tokens are logged.

Prices are USD per 1,000,000 tokens.
"""
from __future__ import annotations

from typing import Dict, Optional

from src.records import TokenUsage

# model_name -> {"input": $/Mtok, "output": $/Mtok}. None == PENDING (not yet set).
# Reasoning/thinking tokens are billed at the provider's output rate unless noted.
#
# ESTIMATES (not yet PI-confirmed): Claude/GPT use the Bedrock model-catalog prices
# seen at build; Grok/Gemini are rough placeholders. Confirm native list prices
# before reporting final cost. PRICES_ARE_ESTIMATES flags this in any output.
PRICES_ARE_ESTIMATES = True
PRICES: Dict[str, Optional[Dict[str, float]]] = {
    "Claude Opus 4.8": {"input": 5.0, "output": 25.0},   # ESTIMATE (Bedrock catalog)
    "GPT-5.5": {"input": 5.5, "output": 33.0},            # ESTIMATE (Bedrock catalog)
    "Grok 4.3": {"input": 3.0, "output": 15.0},           # ESTIMATE (placeholder)
    "Gemini 3.1 Pro": {"input": 2.0, "output": 12.0},     # ESTIMATE (placeholder)
}


def compute_cost(model_name: str, usage: TokenUsage) -> Optional[float]:
    """USD cost for a call, or None if the price is still PENDING."""
    price = PRICES.get(model_name)
    if not price:
        return None
    in_cost = usage.input_tokens / 1_000_000 * price["input"]
    # reasoning tokens billed at output rate (provider-dependent; confirm at signoff).
    out_tokens = usage.output_tokens + usage.reasoning_tokens
    out_cost = out_tokens / 1_000_000 * price["output"]
    return round(in_cost + out_cost, 6)
