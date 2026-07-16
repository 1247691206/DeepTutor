"""Cost-tier LLM routing: strong for tutor chat, cheap for internal work.

Coach/chat keep the catalog active model (strong). Internal capabilities
(quiz gen/judge, notebook summary, memory consolidation, research) prefer
``llm-model-cheap`` when present. Falls back silently if missing.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from contextvars import Token
from typing import Any, Iterator

from deeptutor.services.llm.config import (
    LLMConfig,
    get_scoped_llm_config,
    reset_scoped_llm_config,
)

logger = logging.getLogger(__name__)

CHEAP_PROFILE_ID = "llm-profile-default"
CHEAP_MODEL_ID = "llm-model-cheap"

# Unified WS capabilities that should use the cheap tier by default.
CHEAP_CAPABILITIES = frozenset(
    {
        "deep_question",
        "deep_research",
    }
)


def capability_prefers_cheap(capability: str | None) -> bool:
    name = str(capability or "").strip().lower()
    return name in CHEAP_CAPABILITIES


def find_cheap_llm_selection(catalog: dict[str, Any] | None = None) -> dict[str, str] | None:
    """Return ``{profile_id, model_id}`` for the cheap model if configured."""
    if catalog is None:
        try:
            from deeptutor.services.config import get_model_catalog_service

            catalog = get_model_catalog_service().load()
        except Exception:
            logger.debug("cost_tier: catalog unavailable", exc_info=True)
            return None
    if not isinstance(catalog, dict):
        return None
    services = catalog.get("services") or {}
    llm = services.get("llm") if isinstance(services, dict) else {}
    if not isinstance(llm, dict):
        return None

    for profile in llm.get("profiles") or []:
        if not isinstance(profile, dict):
            continue
        profile_id = str(profile.get("id") or "").strip()
        if not profile_id:
            continue
        for model in profile.get("models") or []:
            if not isinstance(model, dict):
                continue
            model_id = str(model.get("id") or "").strip()
            if model_id == CHEAP_MODEL_ID:
                return {"profile_id": profile_id, "model_id": model_id}
            if str(model.get("cost_tier") or "").strip().lower() == "cheap":
                return {"profile_id": profile_id, "model_id": model_id}

    for profile in llm.get("profiles") or []:
        if not isinstance(profile, dict):
            continue
        profile_id = str(profile.get("id") or "").strip()
        for model in profile.get("models") or []:
            if not isinstance(model, dict):
                continue
            label = f"{model.get('name') or ''} {model.get('model') or ''}".lower()
            model_id = str(model.get("id") or "").strip()
            if model_id and any(tok in label for tok in ("mini", "flash", "small", "nano")):
                if model_id == str(llm.get("active_model_id") or ""):
                    continue
                return {"profile_id": profile_id, "model_id": model_id}
    return None


def selection_for_capability(
    capability: str | None,
    explicit: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Pick LLM selection for a unified-WS capability.

    For cheap capabilities we prefer the catalog cheap model (server-side)
    so students without a model picker still get cost savings.
    """
    if capability_prefers_cheap(capability):
        cheap = find_cheap_llm_selection()
        if cheap:
            return cheap
    return explicit


def activate_cheap_llm() -> Token[LLMConfig | None] | None:
    """Install cheap LLM as scoped config. Returns reset token, or None."""
    cheap = find_cheap_llm_selection()
    if not cheap:
        return None
    try:
        from deeptutor.services.model_selection.runtime import activate_llm_selection

        _config, token = activate_llm_selection(cheap)
        logger.info(
            "cost_tier: using cheap LLM profile=%s model=%s (%s)",
            cheap.get("profile_id"),
            cheap.get("model_id"),
            getattr(_config, "model", "?"),
        )
        return token
    except Exception:
        logger.warning("cost_tier: failed to activate cheap LLM", exc_info=True)
        return None


def reset_cheap_llm(token: Token[LLMConfig | None] | None) -> None:
    if token is not None:
        reset_scoped_llm_config(token)


@contextmanager
def cheap_llm_scope(*, only_if_idle: bool = False) -> Iterator[bool]:
    """Activate cheap LLM for the block. Yields whether cheap was activated."""
    if only_if_idle and get_scoped_llm_config() is not None:
        yield False
        return
    token = activate_cheap_llm()
    try:
        yield token is not None
    finally:
        reset_cheap_llm(token)


__all__ = [
    "CHEAP_CAPABILITIES",
    "CHEAP_MODEL_ID",
    "CHEAP_PROFILE_ID",
    "activate_cheap_llm",
    "capability_prefers_cheap",
    "cheap_llm_scope",
    "find_cheap_llm_selection",
    "reset_cheap_llm",
    "selection_for_capability",
]
