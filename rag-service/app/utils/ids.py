from __future__ import annotations

import re


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    if not value:
        return "unknown"
    lowered = value.strip().lower()
    slug = _SLUG_RE.sub("_", lowered).strip("_")
    return slug or "unknown"


def build_doc_id(match_id: int, source: str, doc_type: str, slug: str | None = None) -> str:
    base = f"match_{match_id}_{slugify(source)}_{slugify(doc_type)}"
    if slug:
        return f"{base}_{slugify(slug)}"
    return base

