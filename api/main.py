"""FastAPI integration shell for the accessible ordering prototype."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
MENU = json.loads((ROOT / "shared" / "menu.json").read_text(encoding="utf-8"))
VALID_STATES = ("REQUEST", "CLARIFY", "REVIEW", "CONFIRMED", "CANCELLED")


class BasketLine(BaseModel):
    product_id: str
    quantity: int = Field(ge=1)
    modifier_ids: list[str] = Field(default_factory=list)
    line_total_mad: int = Field(ge=0)


class PendingItem(BaseModel):
    product_id: str | None = None
    quantity: int | None = None
    modifier_ids: list[str] = Field(default_factory=list)
    missing_field: str | None = None


class InterpretRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    basket: list[BasketLine] = Field(default_factory=list)
    state: Literal["REQUEST", "CLARIFY", "REVIEW", "CONFIRMED", "CANCELLED"] = "REQUEST"
    pending: PendingItem | None = None


class InterpretResponse(BaseModel):
    state: Literal["REQUEST", "CLARIFY", "REVIEW", "CONFIRMED", "CANCELLED"]
    reply_text: str
    basket: list[BasketLine]
    total_mad: int = Field(ge=0)
    question: str | None = None
    pending: PendingItem | None = None
    error: str | None = None


app = FastAPI(title="Accessible Ordering API", version="0.1.0")


def _use_mock() -> bool:
    return os.getenv("USE_MOCK_AI", "true").strip().lower() not in {"0", "false", "no"}


def _fixture_response(request: InterpretRequest) -> dict:
    """Deterministic integration fixture; replaced by interpreter + logic after merge."""
    normalized = request.text.casefold().strip()
    basket = [line.model_dump() for line in request.basket]
    total = sum(line["line_total_mad"] for line in basket)

    if request.state == "REVIEW" and normalized in {"confirmer", "confirme", "confirm", "oui, confirmer"}:
        return {
            "state": "CONFIRMED",
            "reply_text": f"Commande simulée confirmée. Total : {total} dirhams.",
            "basket": basket,
            "total_mad": total,
            "question": None,
            "pending": None,
            "error": None,
        }

    if "café" in normalized or "cafe" in normalized:
        modifiers = []
        if "grand" in normalized:
            modifiers.append("large")
        else:
            modifiers.append("small")
        if "sans sucre" in normalized:
            modifiers.append("no_sugar")
        line_total = 12 + (6 if "large" in modifiers else 0)
        basket = [{"product_id": "coffee", "quantity": 1, "modifier_ids": modifiers, "line_total_mad": line_total}]
        return {
            "state": "REVIEW",
            "reply_text": f"Café ajouté, {line_total} dirhams. Confirmer, modifier ou annuler ?",
            "basket": basket,
            "total_mad": line_total,
            "question": None,
            "pending": None,
            "error": None,
        }

    return {
        "state": "CLARIFY",
        "reply_text": "Je n'ai pas compris. Veuillez choisir un article du menu.",
        "basket": basket,
        "total_mad": total,
        "question": "Quel article souhaitez-vous ?",
        "pending": request.pending.model_dump() if request.pending else None,
        "error": None,
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "mode": "mock" if _use_mock() else "integration"}


@app.post("/interpret", response_model=InterpretResponse)
async def interpret_order(request: InterpretRequest) -> dict:
    # Mock-first by design. The integration lead will replace the non-mock path
    # with redact -> interpret -> next_step once all three modules are merged.
    return _fixture_response(request)

