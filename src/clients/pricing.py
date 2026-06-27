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
PRICES: Dict[str, Optional[Dict[str, float]]] = {
    "Claude Opus 4.8": None,   # PENDING_SIGNOFF: native Anthropic price per 1M
    "GPT-5.5": None,           # PENDING_SIGNOFF: native OpenAI price per 1M
    "Grok 4.3": None,          # PENDING_SIGNOFF: native xAI price per 1M
    "Gemini 3.1 Pro": None,    # PENDING_SIGNOFF: native Google price per 1M
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
