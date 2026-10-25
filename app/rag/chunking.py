from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    index: int
    text: str


def chunk_text(text: str, *, max_chars: int = 800, overlap: int = 100) -> list[TextChunk]:
    """Режет текст на чанки по абзацам, длинные абзацы — с перекрытием."""
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if overlap < 0 or overlap >= max_chars:
        raise ValueError("overlap must be in [0, max_chars)")

    text = text.strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    parts: list[str] = []
    buf = ""

    def flush() -> None:
        nonlocal buf
        if buf:
            parts.append(buf)
            buf = ""

    for p in paragraphs:
        if len(p) <= max_chars:
            if not buf:
                buf = p
            elif len(buf) + 2 + len(p) <= max_chars:
                buf = f"{buf}\n\n{p}"
            else:
                flush()
                buf = p
        else:
            flush()
            start = 0
            while start < len(p):
                end = min(start + max_chars, len(p))
                parts.append(p[start:end].strip())
                if end == len(p):
                    break
                start = end - overlap
    flush()

    return [TextChunk(index=i, text=t) for i, t in enumerate(parts)]