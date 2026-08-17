from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TextUnit:
    text: str
    locator: str = ""


@dataclass(frozen=True)
class Chunk:
    text: str
    locator: str
    index: int


_SENTENCE_BOUNDARY = re.compile(r"(?<=[。！？!?；;])\s*|\n+")


def _pieces(text: str) -> list[str]:
    normalized = re.sub(r"[ \t\u3000]+", " ", text.replace("\r\n", "\n").replace("\r", "\n"))
    return [part.strip() for part in _SENTENCE_BOUNDARY.split(normalized) if part.strip()]


def chunk_units(units: list[TextUnit], chunk_size: int = 700, overlap: int = 100) -> list[Chunk]:
    if chunk_size < 100:
        raise ValueError("chunk_size must be at least 100")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")

    result: list[Chunk] = []
    for unit in units:
        current = ""
        for piece in _pieces(unit.text):
            while len(piece) > chunk_size:
                if current:
                    result.append(Chunk(current, unit.locator, len(result)))
                    current = current[-overlap:] if overlap else ""
                take = chunk_size - len(current)
                current += piece[:take]
                piece = piece[take:]
                result.append(Chunk(current, unit.locator, len(result)))
                current = current[-overlap:] if overlap else ""

            candidate = f"{current}\n{piece}".strip() if current else piece
            if len(candidate) <= chunk_size:
                current = candidate
                continue

            result.append(Chunk(current, unit.locator, len(result)))
            prefix = current[-overlap:] if overlap else ""
            current = f"{prefix}\n{piece}".strip()

        if current.strip():
            result.append(Chunk(current.strip(), unit.locator, len(result)))
    return result
