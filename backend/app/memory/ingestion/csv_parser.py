"""CSV document parser — row-group chunks for registry tables."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

ROWS_PER_CHUNK = 12


@dataclass(frozen=True)
class CsvChunk:
    content: str
    page: int
    section_ref: str


def parse_csv(path: Path, *, section_ref: str | None = None) -> list[CsvChunk]:
    """Chunk a CSV into row groups with a header row repeated per chunk."""
    ref = section_ref or path.stem.replace("_", " ").title()
    with open(path, newline="") as fh:
        reader = csv.reader(fh)
        rows = list(reader)
    if not rows:
        return []

    header, body = rows[0], rows[1:]
    chunks: list[CsvChunk] = []
    for i in range(0, len(body), ROWS_PER_CHUNK):
        group = body[i : i + ROWS_PER_CHUNK]
        lines = [",".join(header)] + [",".join(r) for r in group]
        chunks.append(CsvChunk(content="\n".join(lines), page=1, section_ref=ref))
    return chunks
