"""Structured-output schema for extraction, generated from taxonomy.yaml.

Codes are Literal enums, so the model can only answer with valid taxonomy codes.
"""

from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, create_model

from app.taxonomy import load_taxonomy

Stance = Literal["rising", "declining", "neutral"]


def _mention_model(dimension: str, codes: list[str]) -> type[BaseModel]:
    return create_model(
        f"{dimension.title()}Mention",
        code=(Literal[tuple(codes)], ...),
        stance=(
            Stance,
            Field(description="rising = presented as trending/new/in demand; declining = presented as fading/out; neutral = merely mentioned"),
        ),
        evidence=(str, Field(description="Short verbatim quote from the text (max ~25 words), in its original language")),
    )


@lru_cache
def extraction_model() -> type[BaseModel]:
    tax = load_taxonomy()
    fields: dict = {
        "is_relevant": (bool, Field(description="True only if the text discusses eyewear (glasses/sunglasses) design, fashion or demand")),
        "language": (Literal["fr", "en", "other"], ...),
    }
    for dim in tax.dimensions:
        fields[dim] = (list[_mention_model(dim, tax.codes(dim))], Field(default_factory=list))
    fields["brands"] = (list[str], Field(default_factory=list, description="Eyewear brands or retailers mentioned"))
    fields["summary_fr"] = (str, Field(description="One sentence in French summarizing the eyewear trend signal of this text; empty if not relevant"))
    return create_model("EyewearExtraction", **fields)
