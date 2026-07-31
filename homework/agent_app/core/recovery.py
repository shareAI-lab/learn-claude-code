import random
import time
from dataclasses import dataclass


@dataclass(slots=True)
class RecoveryState:
    current_model: str
    fallback_model: str | None = None
    consecutive_529: int = 0
    continuation_count: int = 0
    reactive_compact_count: int = 0
    has_escalated: bool = False


class PartialStreamError(Exception):
    def __init__(self, partial_text: str, cause: Exception):
        super().__init__(f"{type(cause).__name__}: {cause}")
        self.partial_text = partial_text
        self.cause = cause


def get_status_code(exc):
    status_code = getattr(exc, "status_code", None)
    if status_code:
        return status_code

    response = getattr(exc, "response", None)
    return getattr(response, "status_code", None)


def is_rate_limit_error(exc):
    name = type(exc).__name__.lower()
    message = str(exc).lower()

    return (
        get_status_code(exc) == 429
        or "ratelimit" in message
        or "rate limit" in message
        or "429" in message
    )


def is_overloaded_error(exc):
    name = type(exc).__name__.lower()
    message = str(exc).lower()

    return (
        get_status_code(exc) == 529
        or "overloaded" in name
        or "overloaded" in message
        or "529" in message
    )


def is_prompt_too_long_error(exc):
    message = str(exc).lower()
    return (
        "prompt_is_too_long" in message
        or "context_length_exceeded" in message
        or "max_context_window" in message
        or ("prompt" in message and "too long" in message)
    )


def extract_retry_after(exc):
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)

    if not headers:
        headers = getattr(exc, "headers", None)

    if not headers:
        return None

    value = headers.get("retry-after")

    try:
        delay = float(value)
    except (TypeError, ValueError):
        return None

    return delay if delay > 0 else None


def retry_delay(
    attempt: int,
    retry_after: float | None = None,
    *,
    base_delay_ms: int = 500,
) -> float:
    if retry_after:
        return retry_after

    base = min(base_delay_ms * (2 ** attempt), 32000) / 1000
    jitter = random.uniform(0, base * 0.25)
    return base + jitter


def with_retry(
    fn,
    state: RecoveryState,
    *,
    max_transient_retries: int = 10,
    max_consecutive_529: int = 3,
    base_delay_ms: int = 500,
):
    for attempt in range(max_transient_retries):
        try:
            response = fn()
            state.consecutive_529 = 0
            return response
        except PartialStreamError:
            raise
        except Exception as e:
            is_429 = is_rate_limit_error(e)
            is_529 = is_overloaded_error(e)

            if not is_429 and not is_529:
                raise

            if is_429:
                state.consecutive_529 = 0

            if is_529:
                state.consecutive_529 += 1
                if state.consecutive_529 >= max_consecutive_529:
                    if (
                        state.fallback_model
                        and state.current_model != state.fallback_model
                    ):
                        state.current_model = state.fallback_model
                        state.consecutive_529 = 0
                        print(f"  \033[31m[529 x{max_consecutive_529}]"
                              f" switching to {state.fallback_model}\033[0m")
                    else:
                        state.consecutive_529 = 0
                        print(f"  \033[31m[529 x{max_consecutive_529}]"
                              " no FALLBACK_MODEL_ID configured, continuing retry\033[0m")

            if attempt == max_transient_retries - 1:
                raise

            delay = retry_delay(
                attempt,
                extract_retry_after(e),
                base_delay_ms=base_delay_ms,
            )
            print(f"  \033[33m[529 overloaded] retry {attempt+1}/{max_transient_retries},"
                  f" wait {delay:.1f}s\033[0m")

            time.sleep(delay)

    raise RuntimeError("unreachable")


def append_unrecoverable_error(messages, exc):
    name = type(exc).__name__
    text = f"[Error] {type(exc).__name__}: {str(exc)[:300]}"

    messages.append({
        "role": "assistant",
        "content": [{
            "type": "text",
            "text": text,
        }],
    })

    print(f"  \033[31m[unrecoverable] {name}: {str(exc)[:100]}\033[0m")
