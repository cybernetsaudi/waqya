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
import re
import time
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


def _retry_cfg(config: dict) -> dict:
    return _llm_cfg(config).get("retry", {})


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
            "model": g.get("headline_model", g.get("model", "gemini-2.5-flash")),
            "temperature": float(g.get("headline_temperature", g.get("temperature", 0.9))),
            "max_output_tokens": int(g.get("headline_max_output_tokens", 512)),
        }
    return {
        "model": g.get("model", "gemini-2.5-flash"),
        "temperature": float(g.get("temperature", 0.85)),
        "max_output_tokens": int(g.get("max_output_tokens", 2000)),
    }


def _groq_params(task: Task, config: dict, *, model_override: str | None = None) -> dict:
    g = _llm_cfg(config).get("groq", {})
    if task == "headline":
        return {
            "model": model_override or g.get("headline_model", "llama-3.1-8b-instant"),
            "temperature": float(g.get("headline_temperature", g.get("temperature", 0.9))),
            "max_tokens": int(g.get("headline_max_tokens", 400)),
        }
    return {
        "model": model_override or g.get("model", "llama-3.3-70b-versatile"),
        "temperature": float(g.get("temperature", 0.85)),
        "max_tokens": int(g.get("max_tokens", 2000)),
    }


def model_for_provider(provider: str, task: Task, config: dict, *, model_override: str | None = None) -> str:
    """Return configured model id for logging and post meta."""
    if provider == "gemini":
        return _gemini_params(task, config)["model"]
    if provider == "groq":
        return _groq_params(task, config, model_override=model_override)["model"]
    return provider


def _word_count(text: str) -> int:
    return len(re.findall(r"\w+", text or ""))


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


def _call_groq(
    *,
    system: str,
    user: str,
    task: Task,
    config: dict,
    model_override: str | None = None,
) -> str:
    api_key = _groq_key()
    if not api_key:
        raise LLMAuthError("GROQ_API_KEY is not set")

    from openai import APIStatusError, AuthenticationError, OpenAI, RateLimitError

    params = _groq_params(task, config, model_override=model_override)
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
            "unavailable",
        )
    )


def _body_limits(config: dict) -> tuple[int, int]:
    retry = _retry_cfg(config)
    pipe = config.get("pipeline", {})
    min_words = int(retry.get("min_body_words", pipe.get("min_words", 400)))
    min_chars = int(retry.get("min_body_chars", 1200))
    return min_words, min_chars


def _body_too_short(text: str, config: dict) -> bool:
    min_words, min_chars = _body_limits(config)
    return _word_count(text) < min_words or len(text) < min_chars


def _call_provider(
    provider: str,
    *,
    system: str,
    user: str,
    task: Task,
    config: dict,
) -> tuple[str, str]:
    """Call one provider; returns (text, model_id)."""
    if provider == "gemini":
        text = _call_gemini(system=system, user=user, task=task, config=config)
        return text, _gemini_params(task, config)["model"]

    if provider == "groq":
        groq_fb = _llm_cfg(config).get("groq", {}).get("fallback_model")
        try:
            text = _call_groq(system=system, user=user, task=task, config=config)
            return text, _groq_params(task, config)["model"]
        except LLMError as exc:
            if task == "body" and groq_fb and "rate limit" in str(exc).lower():
                log.warning("Groq primary model rate limited — trying %s", groq_fb)
                text = _call_groq(
                    system=system,
                    user=user,
                    task=task,
                    config=config,
                    model_override=groq_fb,
                )
                return text, groq_fb
            raise

    raise LLMError(f"{provider}: unknown provider")


def _attempt_completion(
    *,
    system: str,
    user: str,
    config: dict,
    task: Task,
) -> tuple[str, str, str]:
    """Try each configured provider once. Returns (text, provider, model_id)."""
    errors: list[str] = []
    for provider in _provider_order(task, config):
        if provider == "gemini" and not _gemini_key():
            errors.append("gemini: no API key")
            continue
        if provider == "groq" and not _groq_key():
            errors.append("groq: no API key")
            continue
        try:
            text, model_id = _call_provider(
                provider,
                system=system,
                user=user,
                task=task,
                config=config,
            )
            log.info(
                "LLM %s via %s/%s (%d chars, %d words)",
                task,
                provider,
                model_id,
                len(text),
                _word_count(text),
            )
            return text, provider, model_id
        except LLMAuthError as exc:
            log.error("%s", exc)
            errors.append(str(exc))
            continue
        except LLMError as exc:
            log.warning("LLM %s %s failed: %s", task, provider, exc)
            errors.append(f"{provider}: {exc}")
            continue

    raise LLMError(
        f"All providers failed for {task}: " + "; ".join(errors) if errors else "no providers"
    )


def chat_completion(
    *,
    system: str,
    user: str,
    config: dict,
    task: Task = "body",
) -> tuple[str, str, str]:
    """
    Generate text using configured provider order for the task.
    Returns (text, provider_name, model_id).
    """
    retry = _retry_cfg(config)
    max_attempts = int(retry.get("max_attempts", 3 if task == "body" else 2))
    backoffs = retry.get("backoff_seconds", [8, 20, 45])
    if not isinstance(backoffs, list):
        backoffs = [8, 20, 45]

    min_words, min_chars = _body_limits(config)
    last_error = "no providers"

    for attempt in range(max_attempts):
        user_msg = user
        if task == "body" and attempt > 0:
            user_msg = (
                f"{user}\n\n"
                f"IMPORTANT (attempt {attempt + 1}): Your previous draft was too short. "
                f"Write the COMPLETE article — minimum {min_words} words, "
                f"with exactly 2–3 ## subheadings and full Hook → Facts → Context → Hot take → Close."
            )

        try:
            text, provider, model_id = _attempt_completion(
                system=system,
                user=user_msg,
                config=config,
                task=task,
            )
        except LLMError as exc:
            last_error = str(exc)
            if attempt < max_attempts - 1:
                wait = backoffs[min(attempt, len(backoffs) - 1)]
                log.warning(
                    "LLM %s attempt %d/%d failed — retry in %ds: %s",
                    task,
                    attempt + 1,
                    max_attempts,
                    wait,
                    exc,
                )
                time.sleep(wait)
                continue
            raise

        if task == "body" and _body_too_short(text, config):
            last_error = f"Body too short ({_word_count(text)} words, {len(text)} chars)"
            if attempt < max_attempts - 1:
                wait = backoffs[min(attempt, len(backoffs) - 1)]
                log.warning(
                    "LLM body attempt %d/%d too short (%d words) — retry in %ds",
                    attempt + 1,
                    max_attempts,
                    _word_count(text),
                    wait,
                )
                time.sleep(wait)
                continue
            raise LLMError(f"{last_error} after {max_attempts} attempts")

        return text, provider, model_id

    raise LLMError(f"All providers failed for {task}: {last_error}")


def ensure_providers(config: dict | None = None) -> bool:
    """Return True if at least one provider can run."""
    if config is None:
        import yaml

        with open(CONFIG_PATH) as f:
            config = yaml.safe_load(f)
    order = set(_provider_order("body", config) + _provider_order("headline", config))
    return ("gemini" in order and bool(_gemini_key())) or ("groq" in order and bool(_groq_key()))
