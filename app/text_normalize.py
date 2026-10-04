from __future__ import annotations

import re
import unicodedata


_WS_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"[a-z0-9']+")


def normalize_dialogue(text: str) -> str:
    """Normalize OCR/source text for stable matching without destroying words."""
    text = unicodedata.normalize("NFKC", text)
    text = (
        text.replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
        .replace("…", "...")
    )
    text = text.casefold()
    text = _WS_RE.sub(" ", text).strip()

    # OCR punctuation is less reliable than lexical content. Keep apostrophes
    # inside words but turn most punctuation into spaces.
    cleaned: list[str] = []
    for ch in text:
        if ch.isalnum() or ch in {"'", " "}:
            cleaned.append(ch)
        else:
            cleaned.append(" ")

    return _WS_RE.sub(" ", "".join(cleaned)).strip()


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(normalize_dialogue(text))


def token_key(text: str) -> str:
    """Order-preserving normalized token string used for exact lookup."""
    return " ".join(tokenize(text))
