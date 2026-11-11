"""Estruturas de dados da leitura de documentos. Coordenadas em pontos do PDF, origem no topo."""

from dataclasses import dataclass, field

NATIVE = "native"
OCR = "ocr"


@dataclass(frozen=True)
class Word:
    """Palavra com a caixa delimitadora (x0, top, x1, bottom)."""

    text: str
    x0: float
    top: float
    x1: float
    bottom: float

    def as_list(self) -> list:
        """Formato compacto para guardar em JSON."""
        return [
            self.text,
            round(self.x0, 1),
            round(self.top, 1),
            round(self.x1, 1),
            round(self.bottom, 1),
        ]


@dataclass
class PageContent:
    """Conteúdo de uma página: palavras com coordenadas e de onde vieram (texto nativo ou OCR)."""

    number: int
    width: float
    height: float
    source: str
    words: list[Word] = field(default_factory=list)
    ocr_confidence: float | None = None

    @property
    def char_count(self) -> int:
        """Quantidade de caracteres (sem espaços)."""
        return sum(len(w.text) for w in self.words)


@dataclass(frozen=True)
class Chunk:
    """Trecho de uma página (parágrafo ou cláusula) com a caixa que envolve todas as palavras."""

    page_number: int
    index: int
    text: str
    x0: float
    top: float
    x1: float
    bottom: float
    source: str
