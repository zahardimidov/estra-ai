"""
ML inference stubs for content moderation.

These are heuristic-based stubs that simulate real ML models.
They use keyword matching + light scoring to produce realistic results.
Replace each handler with a real model loader when ready.
"""
import random
import re

MODEL_VERSIONS: dict[str, str] = {
    "toxicity": "0.1.0-stub",
    "spam": "0.1.0-stub",
    "scam": "0.1.0-stub",
    "nsfw": "0.1.0-stub",
}

BLOCK_THRESHOLD = 0.7

_TOXICITY_KW = [
    "hate", "kill", "die", "stupid", "idiot", "loser", "ugly",
    "dumb", "moron", "screw you", "shut up", "trash", "garbage",
]

_SPAM_KW = [
    "buy now", "click here", "free money", "limited offer", "act now",
    "subscribe", "discount", "promo code", "special offer", "earn cash",
    "get paid", "make money", "order now", "sale", "100% free",
]

_SCAM_KW = [
    "investment opportunity", "crypto", "bitcoin", "earn money fast",
    "get rich", "passive income", "guaranteed profit", "wire transfer",
    "lottery", "you have won", "claim your prize", "nigerian prince",
    "double your money", "risk-free", "secret method",
]

_NSFW_KW = [
    "explicit", "nude", "naked", "porn", "xxx", "adult content",
    "18+", "onlyfans", "sex", "erotic", "nsfw",
]


def _keyword_score(text: str, keywords: list[str]) -> float:
    """Return a 0-1 score based on keyword density with small random noise."""
    text_lower = text.lower()
    matches = sum(1 for kw in keywords if kw in text_lower)

    if matches == 0:
        return round(random.uniform(0.0, 0.12), 4)

    raw = 0.45 + matches * 0.18 + random.uniform(-0.04, 0.04)
    return round(min(raw, 0.97), 4)


def _infer_toxicity(text: str) -> dict:
    return {"score": _keyword_score(text, _TOXICITY_KW), "version": MODEL_VERSIONS["toxicity"]}


def _infer_spam(text: str) -> dict:
    url_count = len(re.findall(r"https?://\S+", text))
    base = _keyword_score(text, _SPAM_KW)
    score = round(min(base + url_count * 0.08, 0.97), 4)
    return {"score": score, "version": MODEL_VERSIONS["spam"]}


def _infer_scam(text: str) -> dict:
    return {"score": _keyword_score(text, _SCAM_KW), "version": MODEL_VERSIONS["scam"]}


def _infer_nsfw_text(text: str) -> dict:
    return {"score": _keyword_score(text, _NSFW_KW), "version": MODEL_VERSIONS["nsfw"]}


_CATEGORY_HANDLERS: dict[str, callable] = {
    "toxicity": _infer_toxicity,
    "spam": _infer_spam,
    "scam": _infer_scam,
    "nsfw": _infer_nsfw_text,
}

# Image categories currently have a single stub handler each — no keyword
# signal is available (we don't decode the image), so it's pure noise biased
# low, same shape as the "no match" branch of the text stubs.
_IMAGE_CATEGORY_HANDLERS: dict[str, callable] = {
    "nsfw": lambda: {"score": round(random.uniform(0.0, 0.2), 4), "version": MODEL_VERSIONS["nsfw"]},
}


def run_text_inference(
    text: str,
    categories: list[str],
) -> tuple[dict[str, float], dict[str, str], str]:
    """
    Run stub inference for text content.

    Returns:
        scores         — {category: probability}
        model_versions — {category: version_string}
        decision       — "approved" | "blocked"
    """
    scores: dict[str, float] = {}
    model_versions: dict[str, str] = {}

    for category in categories:
        handler = _CATEGORY_HANDLERS.get(category)
        if handler is None:
            continue
        result = handler(text)
        scores[category] = result["score"]
        model_versions[category] = result["version"]

    max_score = max(scores.values()) if scores else 0.0
    decision = "blocked" if max_score >= BLOCK_THRESHOLD else "approved"

    return scores, model_versions, decision


def run_image_inference(
    categories: list[str],
) -> tuple[dict[str, float], dict[str, str], str]:
    """
    Run stub inference for image content.

    Same return shape as run_text_inference — see there for details.
    """
    scores: dict[str, float] = {}
    model_versions: dict[str, str] = {}

    for category in categories:
        handler = _IMAGE_CATEGORY_HANDLERS.get(category)
        if handler is None:
            continue
        result = handler()
        scores[category] = result["score"]
        model_versions[category] = result["version"]

    max_score = max(scores.values()) if scores else 0.0
    decision = "blocked" if max_score >= BLOCK_THRESHOLD else "approved"

    return scores, model_versions, decision
