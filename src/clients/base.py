"""
base.py — uniform model-client interface (§18.2).

One interface for all providers exposing a single call:

    forecast(pack_fields, reasoning_level, arm, match_id, sample_index, market) -> ForecastRecord

The base class owns the provider-agnostic orchestration required by §18.2 / §21:
  - build the byte-identical prompt from frozen pieces (config.build_match_prompt)
  - set reasoning effort ONLY by API parameter (config reasoning_kwargs)
  - call the provider, RETRY on parse failure (§18.3)
  - parse the five keys, flag strict-clean for the pilot gate (§19)
  - log model id, API version, parameters, timestamp, raw response, token usage,
    and cost into a ForecastRecord (§21)

Provider subclasses implement only `_raw_complete`. No network here.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional

from config import config as C
from config.config import ModelSpec
from src import parsing as P
from src.clients.pricing import compute_cost
from src.records import ForecastRecord, TokenUsage


@dataclass
class RawCompletion:
    """What a provider returns for one call."""
    text: str
    api_version: str
    parameters: Dict
    usage: TokenUsage


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ModelClient(ABC):
    def __init__(self, spec: ModelSpec, api_key: str):
        self.spec = spec
        self.api_key = api_key

    # ---- provider hook ---------------------------------------------------- #
    @abstractmethod
    def _raw_complete(self, prompt: str, reasoning_level: str,
                      temperature: Optional[float]) -> RawCompletion:
        """Make ONE provider call. Implemented per provider; the only network point."""

    # ---- shared orchestration -------------------------------------------- #
    def supports_level(self, reasoning_level: str) -> bool:
        return reasoning_level in self.spec.reasoning_kwargs

    def forecast(self, pack_fields: Dict, reasoning_level: str, arm: str,
                 match_id: str, sample_index: int = 0,
                 market: Optional[Dict] = None,
                 max_attempts: int = C.PARSE_MAX_ATTEMPTS) -> ForecastRecord:
        if not self.supports_level(reasoning_level):
            raise ValueError(
                f"{self.spec.name} does not run reasoning level {reasoning_level!r} "
                f"(supported: {sorted(self.spec.reasoning_kwargs)})")

        prompt = C.build_match_prompt(pack_fields, arm=arm, market=market)
        temperature = C.TEMPERATURE if self.spec.accepts_temperature else None

        raw: Optional[RawCompletion] = None
        parsed: Optional[Dict[str, int]] = None
        clean = False
        attempts = 0
        for attempts in range(1, max_attempts + 1):
            raw = self._raw_complete(prompt, reasoning_level, temperature)
            try:
                parsed = P.parse_five_keys(raw.text)
                clean = P.is_clean_five_key(raw.text)
                break
            except P.ParseError:
                parsed = None
                clean = False
                continue

        usage = raw.usage if raw else TokenUsage()
        usage.usd_cost = compute_cost(self.spec.name, usage)
        return ForecastRecord(
            model_name=self.spec.name,
            model_id=self.spec.model_id,
            provider=self.spec.provider,
            api_version=raw.api_version if raw else "",
            parameters=raw.parameters if raw else {},
            reasoning_level=reasoning_level,
            arm=arm,
            match_id=match_id,
            sample_index=sample_index,
            timestamp=_utc_now_iso(),
            raw_response=raw.text if raw else "",
            parsed=parsed,
            parse_clean=clean,
            n_attempts=attempts,
            usage=usage,
        )
