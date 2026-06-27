"""
LLM client — Gemini (primary body) + Groq (primary headlines, fallback).

Planning:
  - Article body: Gemini first (quality) → Groq fallback on rate limit / outage
  - Headline/meta: Groq first (fast, spare Gemini quota) → Gemini fallback
  - OpenAI is no longer required for the main pipeline
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Literal

log = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent / "config.yaml"

Task = Literal["body", "headline"]

_RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


class LLMError(Exception):
    """All configured providers failed for a generation step."""


class LLMAuthError(LLMError):
    """API key missing or rejected."""


def _llm_cfg(config: dict) -> dict:
    return config.get("llm", {})


def _provider_order(task: Task, config: dict) -> list[str]:
    llm = _llm_cfg(config)
    section = llm.get(task, {})
    primary = section.get("primary", "gemini" if task == "body" else "groq")
    fallback = section.get("fallback", "groq" if task == "body" else "gemini")
    order: list[str] = []
    for name in (primary, fallback):
        if name and name not in order:
            order.append(name)
    return order


def _gemini_key() -> str:
    return (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()


def _groq_key() -> str:
    return (os.environ.get("GROQ_API_KEY") or "").strip()


def available_providers() -> list[str]:
    out: list[str] = []
    if _gemini_key():
        out.append("gemini")
    if _groq_key():
        out.append("groq")
    return out


def _gemini_params(task: Task, config: dict) -> dict:
    g = _llm_cfg(config).get("gemini", {})
    if task == "headline":
        return {
            "model": g.get("headline_model", g.get("model", "gemini-2.0-flash")),
            "temperature": float(g.get("headline_temperature", g.get("temperature", 0.9))),
            "max_output_tokens": int(g.get("headline_max_output_tokens", 512)),
        }
    return {
        "model": g.get("model", "gemini-2.0-flash"),
        "temperature": float(g.get("temperature", 0.85)),
        "max_output_tokens": int(g.get("max_output_tokens", 2000)),
    }


def _groq_params(task: Task, config: dict) -> dict:
    g = _llm_cfg(config).get("groq", {})
    if task == "headline":
        return {
            "model": g.get("headline_model", "llama-3.1-8b-instant"),
            "temperature": float(g.get("headline_temperature", g.get("temperature", 0.9))),
            "max_tokens": int(g.get("headline_max_tokens", 400)),
        }
    return {
        "model": g.get("model", "llama-3.3-70b-versatile"),
        "temperature": float(g.get("temperature", 0.85)),
        "max_tokens": int(g.get("max_tokens", 2000)),
    }


def _gemini_client(api_key: str, config: dict):
    from google import genai

    gcfg = _llm_cfg(config).get("gemini", {})
    use_vertex = bool(gcfg.get("vertexai", False))
    if use_vertex:
        return genai.Client(vertexai=True, api_key=api_key)
    return genai.Client(api_key=api_key)


def _call_gemini(*, system: str, user: str, task: Task, config: dict) -> str:
    api_key = _gemini_key()
    if not api_key:
        raise LLMAuthError("GEMINI_API_KEY is not set")

    from google.genai import types

    params = _gemini_params(task, config)
    client = _gemini_client(api_key, config)
    try:
        response = client.models.generate_content(
            model=params["model"],
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=params["temperature"],
                max_output_tokens=params["max_output_tokens"],
            ),
        )
    except Exception as exc:
        if _is_auth_error(exc):
            raise LLMAuthError(f"Gemini auth failed: {exc}") from exc
        if _is_retryable(exc):
            raise LLMError(f"Gemini transient error: {exc}") from exc
        raise LLMError(f"Gemini failed: {exc}") from exc

    text = (getattr(response, "text", None) or "").strip()
    if not text:
        raise LLMError("Gemini returned empty response")
    return text


def _call_groq(*, system: str, user: str, task: Task, config: dict) -> str:
    api_key = _groq_key()
    if not api_key:
        raise LLMAuthError("GROQ_API_KEY is not set")

    from openai import APIStatusError, AuthenticationError, OpenAI, RateLimitError

    params = _groq_params(task, config)
    client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
    try:
        resp = client.chat.completions.create(
            model=params["model"],
            temperature=params["temperature"],
            max_tokens=params["max_tokens"],
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
    except AuthenticationError as exc:
        raise LLMAuthError(f"Groq auth failed: {exc}") from exc
    except RateLimitError as exc:
        raise LLMError(f"Groq rate limited: {exc}") from exc
    except APIStatusError as exc:
        if exc.status_code in _RETRYABLE_STATUS:
            raise LLMError(f"Groq HTTP {exc.status_code}: {exc}") from exc
        raise LLMError(f"Groq failed: {exc}") from exc
    except Exception as exc:
        raise LLMError(f"Groq failed: {exc}") from exc

    text = (resp.choices[0].message.content or "").strip()
    if not text:
        raise LLMError("Groq returned empty response")
    return text


def _is_auth_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(
        token in msg
        for token in (
            "api key",
            "api_key",
            "unauthorized",
            "permission denied",
            "invalid",
            "401",
            "403",
        )
    )


def _is_retryable(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(
        token in msg
        for token in (
            "429",
            "rate",
            "quota",
            "resource exhausted",
            "503",
            "502",
            "504",
            "timeout",
            "overloaded",
        )
    )


def chat_completion(
    *,
    system: str,
    user: str,
    config: dict,
    task: Task = "body",
) -> tuple[str, str]:
    """
    Generate text using configured provider order for the task.
    Returns (text, provider_name).
    """
    errors: list[str] = []
    for provider in _provider_order(task, config):
        if provider == "gemini" and not _gemini_key():
            errors.append("gemini: no API key")
            continue
        if provider == "groq" and not _groq_key():
            errors.append("groq: no API key")
            continue
        try:
            if provider == "gemini":
                text = _call_gemini(system=system, user=user, task=task, config=config)
            elif provider == "groq":
                text = _call_groq(system=system, user=user, task=task, config=config)
            else:
                errors.append(f"{provider}: unknown")
                continue
            log.info("LLM %s via %s (%d chars)", task, provider, len(text))
            return text, provider
        except LLMAuthError as exc:
            log.error("%s", exc)
            errors.append(str(exc))
            # Auth on one provider — still try the other
            continue
        except LLMError as exc:
            log.warning("LLM %s %s failed: %s", task, provider, exc)
            errors.append(f"{provider}: {exc}")
            continue

    raise LLMError(
        f"All providers failed for {task}: " + "; ".join(errors) if errors else "no providers"
    )


def ensure_providers(config: dict | None = None) -> bool:
    """Return True if at least one provider can run."""
    if config is None:
        import yaml

        with open(CONFIG_PATH) as f:
            config = yaml.safe_load(f)
    order = set(_provider_order("body", config) + _provider_order("headline", config))
    return ("gemini" in order and bool(_gemini_key())) or ("groq" in order and bool(_groq_key()))
