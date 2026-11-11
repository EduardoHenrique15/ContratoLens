"""Divisão das páginas em trechos (parágrafos ou cláusulas), cada um com a caixa delimitadora."""

import re
import statistics

from contratolens.documents.types import Chunk, PageContent, Word

MAX_CHUNK_CHARS = 1500
MIN_CHUNK_CHARS = 40
PARAGRAPH_GAP_FACTOR = 1.2
HEADING = re.compile(r"^(CL[ÁA]USULA|SUBCL[ÁA]USULA|PAR[ÁA]GRAFO)\b", re.IGNORECASE)


def group_lines(words: list[Word]) -> list[list[Word]]:
    """Agrupa palavras em linhas pela posição vertical; cada linha fica em ordem horizontal."""
    lines: list[list[Word]] = []
    for word in sorted(words, key=lambda w: (round(w.top), w.x0)):
        height = max(word.bottom - word.top, 1.0)
        if lines:
            current = lines[-1]
            reference = statistics.median(w.top for w in current)
            if abs(word.top - reference) <= height * 0.5:
                current.append(word)
                continue
        lines.append([word])
    return [sorted(line, key=lambda w: w.x0) for line in lines]


def _line_text(line: list[Word]) -> str:
    return " ".join(w.text for w in line)


def _block_chars(block: list[list[Word]]) -> int:
    """Tamanho do texto do bloco, contando as quebras de linha entre as linhas."""
    return sum(len(_line_text(line)) for line in block) + max(len(block) - 1, 0)


def _bbox(lines: list[list[Word]]) -> tuple[float, float, float, float]:
    words = [w for line in lines for w in line]
    return (
        min(w.x0 for w in words),
        min(w.top for w in words),
        max(w.x1 for w in words),
        max(w.bottom for w in words),
    )


def _blocks(lines: list[list[Word]]) -> list[list[list[Word]]]:
    if not lines:
        return []
    heights = [max(w.bottom - w.top for w in line) for line in lines]
    typical = statistics.median(heights)
    blocks: list[list[list[Word]]] = [[lines[0]]]
    for previous, line in zip(lines, lines[1:], strict=False):
        gap = min(w.top for w in line) - max(w.bottom for w in previous)
        starts_heading = bool(HEADING.match(_line_text(line)))
        if (
            gap > typical * PARAGRAPH_GAP_FACTOR
            or starts_heading
            or _block_chars(blocks[-1]) + 1 + len(_line_text(line)) > MAX_CHUNK_CHARS
        ):
            blocks.append([line])
        else:
            blocks[-1].append(line)
    merged: list[list[list[Word]]] = []
    for block in blocks:
        small = _block_chars(block) < MIN_CHUNK_CHARS
        fits = merged and _block_chars(merged[-1]) + 1 + _block_chars(block) <= MAX_CHUNK_CHARS
        if small and fits and not HEADING.match(_line_text(block[0])):
            merged[-1].extend(block)
        else:
            merged.append(block)
    return merged


def chunk_pages(pages: list[PageContent]) -> list[Chunk]:
    """Gera os trechos de todas as páginas, numerados em ordem no documento."""
    chunks: list[Chunk] = []
    for page in pages:
        for block in _blocks(group_lines(page.words)):
            x0, top, x1, bottom = _bbox(block)
            text = "\n".join(_line_text(line) for line in block)
            chunks.append(Chunk(page.number, len(chunks), text, x0, top, x1, bottom, page.source))
    return chunks
