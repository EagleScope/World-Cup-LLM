"""
fake.py — offline fake client for testing base orchestration (no network).

Returns canned responses from a queue so we can exercise the retry/parse/record
logic deterministically without hitting any provider.
"""
from __future__ import annotations

from typing import List, Optional

from config.config import ModelSpec
from src.clients.base import ModelClient, RawCompletion
from src.records import TokenUsage


class FakeClient(ModelClient):
    def __init__(self, spec: ModelSpec, responses: List[str]):
        super().__init__(spec, api_key="fake")
        self._responses = list(responses)
        self.calls: List[dict] = []   # record of (prompt, level, temperature)

    def _raw_complete(self, prompt, reasoning_level, temperature) -> RawCompletion:
        self.calls.append({"prompt": prompt, "reasoning_level": reasoning_level,
                           "temperature": temperature})
        text = self._responses.pop(0) if self._responses else ""
        return RawCompletion(
            text=text,
            api_version="fake/1.0",
            parameters={"reasoning_level": reasoning_level, "temperature": temperature,
                        **self.spec.reasoning_kwargs.get(reasoning_level, {})},
            usage=TokenUsage(input_tokens=100, output_tokens=12, total_tokens=112),
        )


class ConstantFakeClient(ModelClient):
    """Returns a deterministic response per sample_index (for run/pilot tests).

    `response_for(sample_index, level, arm)` -> str. Lets tests inject varied but
    reproducible samples without any network."""
    def __init__(self, spec: ModelSpec, response_for):
        super().__init__(spec, api_key="fake")
        self._fn = response_for
        self._i = 0

    def _raw_complete(self, prompt, reasoning_level, temperature) -> RawCompletion:
        text = self._fn(self._i, reasoning_level, temperature)
        self._i += 1
        return RawCompletion(
            text=text,
            api_version="fake/1.0",
            parameters={"reasoning_level": reasoning_level, "temperature": temperature,
                        **self.spec.reasoning_kwargs.get(reasoning_level, {})},
            usage=TokenUsage(input_tokens=100, output_tokens=12, total_tokens=112),
        )
