"""Offline request preparation only. No HTTP, credentials, or model inference.

The small demo uses a 16 KiB state cap of its own; it is NOT a tokenizer or a
claim about a provider context window. Sources are linked from README.md.
"""
from __future__ import annotations
from copy import deepcopy
from decimal import Decimal
import json
from typing import Any

CF_MODELS = {
    "cf-jev": ("typesafe/jev", None),
    "cf-clef-flash": ("@cf/cloudflare/clef-flash", "clef-flash"),
    "cf-clef": ("@cf/cloudflare/clef", "clef"),
}


def prepare_cf(route: str, state: Any, questions: dict[str, Any]) -> dict[str, Any]:
    """Construct a unified /ai/run body. Unknown routes never fall back."""
    if route not in CF_MODELS:
        raise ValueError("unknown route")
    if not isinstance(state, (str, dict, list)):
        raise ValueError("state must be text or JSON data")
    encoded = json.dumps(state, ensure_ascii=False, allow_nan=False).encode("utf-8")
    if len(encoded) > 16384:
        raise ValueError("demo state limit exceeded")
    if not isinstance(questions, dict) or not 1 <= len(questions) <= 64:
        raise ValueError("demo requires 1 to 64 questions")
    for name, question in questions.items():
        if not isinstance(name, str) or not name or not isinstance(question, dict):
            raise ValueError("invalid question")
        if question.get("type") not in {"noul", "choice", "score"}:
            raise ValueError("unsupported question primitive")
        if not isinstance(question.get("instructions"), str) or not question["instructions"].strip():
            raise ValueError("question instructions required")
        kind, criteria = question["type"], question.get("criteria")
        if kind == "choice" and (not isinstance(criteria, dict) or len(criteria) < 2):
            raise ValueError("choice requires at least two criteria")
        if kind == "score" and (not isinstance(criteria, list) or len(criteria) < 2):
            raise ValueError("score requires at least two ordered levels")
    # Validate JSON-serializability without generating or inferring model answers.
    json.dumps(questions, ensure_ascii=False, allow_nan=False)
    outer, inner = CF_MODELS[route]
    payload = {"state": deepcopy(state), "questions": deepcopy(questions)}
    if inner:
        payload["model"] = inner
    return {"model": outer, "input": payload}


def input_cost(input_tokens: int, usd_per_million: str) -> Decimal:
    """Illustrative model input charge; excludes fees, credits and retries."""
    if isinstance(input_tokens, bool) or not isinstance(input_tokens, int) or input_tokens < 0:
        raise ValueError("input_tokens must be a nonnegative integer")
    price = Decimal(usd_per_million)
    if not price.is_finite() or price < 0:
        raise ValueError("invalid unit price")
    return Decimal(input_tokens) * price / Decimal(1000000)


if __name__ == "__main__":
    # Hand-authored synthetic input, no real correspondence or account data.
    state = "这是一条只有标题的材料；正文尚未取得。"
    questions = {"next_read": {
        "type": "choice",
        "instructions": "下一步最需要哪种阅读动作？仅给建议。",
        "criteria": {"read_source": "取得原文", "classify": "材料足够，直接分类", "need_context": "需要其他上下文"},
    }}
    print(json.dumps({route: prepare_cf(route, state, questions) for route in CF_MODELS}, ensure_ascii=False, indent=2))
