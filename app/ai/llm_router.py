import asyncio
import hashlib
from typing import AsyncGenerator, Optional, Tuple
from app.config import settings
from app.ai.provider_health import (
    is_healthy, mark_healthy, mark_unhealthy, log_usage
)
from app.ai.providers.gemini_provider import (
    call_gemini, GeminiError, GeminiRateLimitError
)
from app.ai.providers.groq_provider import (
    call_groq, GroqError, GroqRateLimitError
)
from app.ai.providers.openrouter_provider import (
    call_openrouter, OpenRouterError, OpenRouterRateLimitError
)


# ─── Provider registry ────────────────────────────────────────────────────────
# Order defines priority: Gemini first, Groq second, OpenRouter last.

PROVIDERS = [
    {
        "name": "gemini",
        "fn": call_gemini,
        "rate_limit_error": GeminiRateLimitError,
        "base_error": GeminiError,
        "key_setting": "GEMINI_API_KEYS",
    },
    {
        "name": "groq",
        "fn": call_groq,
        "rate_limit_error": GroqRateLimitError,
        "base_error": GroqError,
        "key_setting": "GROQ_API_KEYS",
    },
    {
        "name": "openrouter",
        "fn": call_openrouter,
        "rate_limit_error": OpenRouterRateLimitError,
        "base_error": OpenRouterError,
        "key_setting": "OPENROUTER_API_KEYS",
    },
]


# ─── Check if a provider has an API key configured ───────────────────────────

def _is_configured(provider: dict) -> bool:
    key_attr = provider["key_setting"]
    value = getattr(settings, key_attr, None)
    return bool(value)


def _get_keys(provider: dict) -> list[str]:
    raw = getattr(settings, provider["key_setting"], None)
    if not raw:
        return []
    return [k.strip() for k in raw.split(",") if k.strip()]


# ─── Collect full response from async generator ───────────────────────────────

async def _collect(gen: AsyncGenerator[str, None]) -> str:
    chunks = []
    async for chunk in gen:
        chunks.append(chunk)
    return "".join(chunks)


# ─── Main router: call_llm ────────────────────────────────────────────────────

async def call_llm(
    prompt: str,
    system: str,
    stream: bool = False,
) -> Tuple[AsyncGenerator[str, None], str]:
    """
    Main LLM entry point for all Egloo modules.
    Tries providers in priority order with health checks.

    Returns: (async_generator, model_name_used)

    Fallback logic:
      1. Skip provider if no API key configured
      2. Skip provider if marked unhealthy in Redis
      3. Try provider — on rate limit: mark unhealthy, move on
      4. On success: mark healthy, log usage
      5. If all fail: raise RuntimeError with clear message

    Caller iterates the generator to get tokens.
    For non-streaming: use call_llm_simple() instead.
    """
    errors = []

    for provider in PROVIDERS:
        name = provider["name"]
        fn = provider["fn"]

        # Skip if no API key
        if not _is_configured(provider):
            print(f"[SKIP] Skipping {name} — no API key")
            continue

        # Skip if marked unhealthy in Redis
        if not await is_healthy(name):
            print(f"[SKIP] Skipping {name} — marked unhealthy")
            errors.append(f"{name}: temporarily unhealthy")
            continue

        print(f"[INFO] Trying provider: {name}")

        try:
            # ── Try the provider ──────────────────────────────────────────
            keys = _get_keys(provider)
            if not keys:
                continue

            last_key_error = None
            gen = None

            for api_key in keys:
                try:
                    gen = fn(
                        api_key=api_key,
                        prompt=prompt,
                        system=system,
                        stream=stream,
                    )
                    break
                except Exception as e:
                    last_key_error = e
                    continue

            if gen is None:
                raise provider["base_error"](
                    f"All API keys exhausted for {name}: {last_key_error}"
                )

            buffer = []
            first_token = None

            async for token in gen:
                first_token = token
                buffer.append(token)
                break

            if first_token is None:
                raise provider["base_error"](
                    f"{name} returned empty response"
                )

            # ── Success ───────────────────────────────────────────────────
            await mark_healthy(name)
            await log_usage(name, success=True, tokens_est=len(prompt) // 4)
            print(f"[OK] Provider {name} responded successfully")

            # Rebuild full generator: buffer + remaining tokens
            async def _full_generator(
                buffered: list,
                remaining: AsyncGenerator,
                provider_name: str,
            ) -> AsyncGenerator[str, None]:
                for t in buffered:
                    yield t
                try:
                    async for t in remaining:
                        yield t
                except Exception as e:
                    print(f"[WARNING] Stream error from {provider_name}: {e}")

            return (
                _full_generator(buffer, gen, name),
                name,
            )

        except provider["rate_limit_error"] as e:
            # Rate limit — back off for health TTL seconds
            print(f"[WARNING] {name} rate limited: {e}")
            await mark_unhealthy(name, f"rate_limited: {str(e)[:80]}")
            await log_usage(name, success=False)
            errors.append(f"{name}: rate limited")
            # Short backoff before trying next provider
            await asyncio.sleep(0.5)
            continue

        except provider["base_error"] as e:
            # Provider error (timeout, config, API error)
            print(f"[ERROR] {name} error: {e}")
            await mark_unhealthy(name, f"error: {str(e)[:80]}")
            await log_usage(name, success=False)
            errors.append(f"{name}: {str(e)[:60]}")
            continue

        except Exception as e:
            # Unexpected error — log but don't mark unhealthy
            print(f"[WARNING] Unexpected error from {name}: {e}")
            errors.append(f"{name}: unexpected error")
            continue

    # All providers failed
    error_summary = " | ".join(errors) if errors else "No providers configured"
    raise RuntimeError(
        f"All LLM providers failed. Details: {error_summary}. "
        f"Add at least one API key to .env: "
        f"GEMINI_API_KEYS, GROQ_API_KEYS, or OPENROUTER_API_KEYS"
    )


# ─── Simple non-streaming call ────────────────────────────────────────────────

async def call_llm_simple(
    prompt: str,
    system: str,
) -> Tuple[str, str]:
    """
    Non-streaming LLM call.
    Collects full response as a single string.
    Returns: (full_response_text, model_name)

    Use this for:
    - Digest generation
    - Topic clustering
    - Action item extraction
    - Any task where you need the full response at once
    """
    gen, model_name = await call_llm(
        prompt=prompt,
        system=system,
        stream=False,
    )
    full_text = await _collect(gen)
    return full_text, model_name


# ─── Query cache key helper ───────────────────────────────────────────────────

def hash_query(user_id: str, question: str) -> str:
    """
    Deterministic cache key from user_id + question.
    Same user asking same question → same key → cached.
    """
    raw = f"{user_id}:{question.strip().lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()
