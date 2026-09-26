"""Provider-agnostic LLM interface. Swap providers by adding a class and a settings value."""

from __future__ import annotations

import logging
from typing import Protocol, TypeVar

import anthropic
from pydantic import BaseModel

from app.config import settings

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class LLMRefused(Exception):
    """The model declined the request (safety stop), so the document is skipped."""


class LLMProvider(Protocol):
    def extract(self, system: str, user: str, schema: type[T]) -> T: ...

    def write(self, system: str, user: str) -> str: ...


class AnthropicProvider:
    def __init__(self, client: anthropic.Anthropic | None = None) -> None:
        # Resolves ANTHROPIC_API_KEY or an `ant auth login` profile.
        self.client = client or anthropic.Anthropic()

    def extract(self, system: str, user: str, schema: type[T]) -> T:
        response = self.client.messages.parse(
            model=settings.extraction_model,
            max_tokens=16000,
            # Taxonomy prompt is identical for every document, so cache it.
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
            output_format=schema,
            output_config={"effort": settings.extraction_effort},
        )
        if response.stop_reason == "refusal":
            raise LLMRefused(str(response.stop_details))
        return response.parsed_output

    def write(self, system: str, user: str) -> str:
        response = self.client.messages.create(
            model=settings.summary_model,
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        if response.stop_reason == "refusal":
            raise LLMRefused(str(response.stop_details))
        return "".join(b.text for b in response.content if b.type == "text").strip()


def get_provider() -> LLMProvider:
    if settings.llm_provider == "anthropic":
        return AnthropicProvider()
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
