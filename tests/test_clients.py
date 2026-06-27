"""Tests for the uniform client orchestration (§18.2) via an offline fake."""
import pytest

from config import config as C
from src.clients.fake import FakeClient
from src.clients.factory import client_class_for
from src.clients import pricing

CLAUDE = next(m for m in C.MODELS if m.provider == "anthropic")
GEMINI = next(m for m in C.MODELS if m.provider == "google")

PACK = {
    "round": "Round of 32", "date": "2026-06-28", "venue": "Stadium", "venue_city": "City",
    "team_A": "A", "team_B": "B", "eloA": 2000, "eloB": 1900, "elo_diff": 100,
    "rankA": 5, "rankB": 12, "mvA": 800, "mvB": 600, "formA": "6-2-2", "formB": "5-3-2",
    "gfgaA": "14/7", "gfgaB": "11/8", "hostA": "no", "hostB": "no", "restA": 4, "restB": 3,
}
GOOD = "A_WIN=45\nDRAW=28\nB_WIN=27\nADV_A=58\nADV_B=42"
BAD = "I think A is favoured but it's hard to say."


def test_forecast_parses_and_records():
    fc = FakeClient(CLAUDE, [GOOD])
    rec = fc.forecast(PACK, reasoning_level="high", arm="primary", match_id="M1", sample_index=3)
    assert rec.parsed == {"A_WIN": 45, "DRAW": 28, "B_WIN": 27, "ADV_A": 58, "ADV_B": 42}
    assert rec.parse_clean is True
    assert rec.n_attempts == 1
    assert rec.model_id == "claude-opus-4-8"
    assert rec.reasoning_level == "high" and rec.arm == "primary" and rec.sample_index == 3
    assert rec.usage.input_tokens == 100
    assert rec.timestamp  # ISO timestamp recorded


def test_retry_on_parse_failure_then_success():
    fc = FakeClient(CLAUDE, [BAD, BAD, GOOD])
    rec = fc.forecast(PACK, "high", "primary", "M1")
    assert rec.parsed is not None
    assert rec.n_attempts == 3              # two failures then success
    assert len(fc.calls) == 3


def test_all_attempts_fail_returns_unparsed_record():
    fc = FakeClient(CLAUDE, [BAD, BAD, BAD])
    rec = fc.forecast(PACK, "high", "primary", "M1", max_attempts=3)
    assert rec.parsed is None
    assert rec.parse_clean is False
    assert rec.n_attempts == 3
    assert rec.raw_response == BAD          # raw kept even when unparsed


def test_reasoning_level_passed_and_unsupported_rejected():
    # Gemini is high-only: requesting 'low' must raise (§6).
    fc = FakeClient(GEMINI, [GOOD])
    with pytest.raises(ValueError):
        fc.forecast(PACK, "low", "primary", "M1")
    # high works
    fc2 = FakeClient(GEMINI, [GOOD])
    rec = fc2.forecast(PACK, "high", "primary", "M1")
    assert rec.reasoning_level == "high"


def test_conditioning_arm_builds_market_prompt():
    fc = FakeClient(CLAUDE, [GOOD])
    fc.forecast(PACK, "high", "conditioning", "M1",
                market={"mktA": 45, "mktD": 28, "mktB": 27})
    sent = fc.calls[0]["prompt"]
    assert "Market-implied probabilities" in sent     # §20.4 line present


def test_gpt_temperature_suppressed():
    gpt = next(m for m in C.MODELS if m.provider == "openai")
    fc = FakeClient(gpt, [GOOD])
    fc.forecast(PACK, "high", "primary", "M1")
    assert fc.calls[0]["temperature"] is None          # §10: GPT rejects temp


def test_factory_maps_every_provider():
    from src.clients.providers import (AnthropicClient, OpenAIClient,
                                       XAIClient, GeminiClient)
    assert client_class_for("anthropic") is AnthropicClient
    assert client_class_for("openai") is OpenAIClient
    assert client_class_for("xai") is XAIClient
    assert client_class_for("google") is GeminiClient


def test_cost_computed_from_estimate_prices():
    fc = FakeClient(CLAUDE, [GOOD])
    rec = fc.forecast(PACK, "high", "primary", "M1")
    # Prices are populated as ESTIMATES (Bedrock catalog / placeholders) pending
    # PI confirmation; cost is therefore computed and flagged as estimate.
    assert rec.usage.usd_cost is not None and rec.usage.usd_cost > 0
    assert pricing.PRICES_ARE_ESTIMATES is True
