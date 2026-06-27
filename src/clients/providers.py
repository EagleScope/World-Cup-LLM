"""
providers.py — the four native-API model clients (§5, §18.2).

Each implements only `_raw_complete`. SDKs are imported LAZILY inside the call so
this module imports cleanly without the SDKs installed and without any network.

>>> The provider request shapes below are written from the current SDKs but have
    NOT been exercised live yet. They will be smoke-tested in the pilot (next
    session, after PI approval). Items flagged PENDING_SIGNOFF in config
    (reasoning params, Claude thinking/temperature interaction) are confirmed
    there before lock. <<<
"""
from __future__ import annotations

from typing import Optional

from config.config import ModelSpec, XAI_BASE_URL
from src.clients.base import ModelClient, RawCompletion
from src.records import TokenUsage


# Generous output cap so reasoning + the tiny 5-line answer always fit.
_BASE_OUTPUT_TOKENS = 2048


class AnthropicClient(ModelClient):
    """Claude Opus 4.8 via the Anthropic Messages API."""

    def _raw_complete(self, prompt, reasoning_level, temperature) -> RawCompletion:
        import anthropic  # lazy
        client = anthropic.Anthropic(api_key=self.api_key)
        rk = dict(self.spec.reasoning_kwargs[reasoning_level])  # {'thinking': {...}}
        thinking = rk.get("thinking", {"type": "disabled"})
        budget = thinking.get("budget_tokens", 0) if thinking.get("type") == "enabled" else 0
        max_tokens = _BASE_OUTPUT_TOKENS + budget
        params = {"model": self.spec.model_id, "max_tokens": max_tokens,
                  "messages": [{"role": "user", "content": prompt}], **rk}
        # Extended thinking requires temperature == 1; only set temp when thinking off.
        if temperature is not None and thinking.get("type") != "enabled":
            params["temperature"] = temperature
        resp = client.messages.create(**params)
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        u = resp.usage
        usage = TokenUsage(input_tokens=u.input_tokens, output_tokens=u.output_tokens,
                           total_tokens=u.input_tokens + u.output_tokens)
        return RawCompletion(text=text, api_version=f"anthropic-sdk/{anthropic.__version__}",
                             parameters={k: v for k, v in params.items() if k != "messages"},
                             usage=usage)


class _OpenAICompatibleClient(ModelClient):
    """Shared impl for OpenAI and xAI (OpenAI-compatible chat completions)."""
    base_url: Optional[str] = None

    def _raw_complete(self, prompt, reasoning_level, temperature) -> RawCompletion:
        import openai  # lazy
        client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
        rk = dict(self.spec.reasoning_kwargs[reasoning_level])  # {'reasoning_effort': ...}
        params = {"model": self.spec.model_id,
                  "messages": [{"role": "user", "content": prompt}], **rk}
        if temperature is not None:
            params["temperature"] = temperature
        resp = client.chat.completions.create(**params)
        text = resp.choices[0].message.content or ""
        u = resp.usage
        reasoning = 0
        details = getattr(u, "completion_tokens_details", None)
        if details is not None:
            reasoning = getattr(details, "reasoning_tokens", 0) or 0
        usage = TokenUsage(input_tokens=u.prompt_tokens, output_tokens=u.completion_tokens,
                           reasoning_tokens=reasoning, total_tokens=u.total_tokens)
        return RawCompletion(text=text, api_version=f"openai-sdk/{openai.__version__}",
                             parameters={k: v for k, v in params.items() if k != "messages"},
                             usage=usage)


class OpenAIClient(_OpenAICompatibleClient):
    """GPT-5.5 via the OpenAI API."""
    base_url = None


class XAIClient(_OpenAICompatibleClient):
    """Grok 4.3 via the xAI OpenAI-compatible endpoint."""
    base_url = XAI_BASE_URL


class GeminiClient(ModelClient):
    """Gemini 3.1 Pro via the Google Gen AI SDK (always-on thinking; high only)."""

    def _raw_complete(self, prompt, reasoning_level, temperature) -> RawCompletion:
        from google import genai  # lazy
        from google.genai import types
        client = genai.Client(api_key=self.api_key)
        cfg = {}
        if temperature is not None:
            cfg["temperature"] = temperature
        resp = client.models.generate_content(
            model=self.spec.model_id, contents=prompt,
            config=types.GenerateContentConfig(**cfg) if cfg else None)
        text = resp.text or ""
        um = getattr(resp, "usage_metadata", None)
        usage = TokenUsage()
        if um is not None:
            usage = TokenUsage(
                input_tokens=getattr(um, "prompt_token_count", 0) or 0,
                output_tokens=getattr(um, "candidates_token_count", 0) or 0,
                reasoning_tokens=getattr(um, "thoughts_token_count", 0) or 0,
                total_tokens=getattr(um, "total_token_count", 0) or 0)
        import google.genai as _g
        return RawCompletion(text=text, api_version=f"google-genai/{_g.__version__}",
                             parameters={"model": self.spec.model_id, **cfg},
                             usage=usage)


_PROVIDER_CLASSES = {
    "anthropic": AnthropicClient,
    "openai": OpenAIClient,
    "xai": XAIClient,
    "google": GeminiClient,
}


def client_class_for(provider: str):
    if provider not in _PROVIDER_CLASSES:
        raise ValueError(f"no client for provider {provider!r}")
    return _PROVIDER_CLASSES[provider]
