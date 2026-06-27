"""
factory.py — build provider clients from config + .env (§5, §18.2).

Keys load from the environment (.env via python-dotenv), never from code (§16).
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional

from config import config as C
from config.config import ModelSpec
from src.clients.base import ModelClient
from src.clients.providers import client_class_for


def _load_dotenv_once() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass  # dotenv optional; env may already be populated


def get_api_key(provider: str) -> Optional[str]:
    _load_dotenv_once()
    return os.environ.get(C.PROVIDER_ENV_VARS[provider])


def build_client(spec: ModelSpec) -> ModelClient:
    key = get_api_key(spec.provider)
    if not key:
        raise RuntimeError(
            f"missing API key for {spec.provider}: set "
            f"{C.PROVIDER_ENV_VARS[spec.provider]} in .env")
    return client_class_for(spec.provider)(spec, key)


def build_all_clients() -> Dict[str, ModelClient]:
    """One client per configured model (skips any with a missing key)."""
    out: Dict[str, ModelClient] = {}
    for spec in C.MODELS:
        try:
            out[spec.name] = build_client(spec)
        except RuntimeError:
            continue
    return out
