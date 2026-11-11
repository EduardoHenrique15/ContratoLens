"""Leitura de documentos: texto nativo com coordenadas (pdfplumber) e OCR só nas páginas escaneadas.

Regras para decidir se uma página precisa de OCR (só ela, não o documento inteiro):
- imagem cobre a maior parte da página e o texto nativo é curto (carimbo sobre o scan): OCR;
- texto nativo suficiente: sem OCR;
- pouco texto e alguma imagem: OCR;
- pouco texto e nenhuma imagem: página curta de verdade (sem OCR), a não ser que esteja totalmente
  sem texto e tenha "tinta" ao renderizar em baixa resolução (imagem que o pdfplumber não detectou).
"""

import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from contratolens.documents.ocr import ocr_image
from contratolens.documents.types import NATIVE, OCR, PageContent, Word, clean_text

MIN_NATIVE_CHARS = 50
IMAGE_COVERAGE_FOR_SCAN = 0.5
MAX_CHARS_ON_SCANNED_PAGE = 500
OCR_DPI = 300


class UnsupportedDocumentError(Exception):
    """Formato de arquivo que o leitor não trata (ex.: .docx)."""


@dataclass
class DocumentContent:
    """Resultado da leitura de um arquivo."""

    file_type: str
    pages: list[PageContent] = field(default_factory=list)

    @property
    def ocr_pages(self) -> int:
        """Quantas páginas precisaram de OCR."""
        return sum(1 for page in self.pages if page.source == OCR)


def detect_file_type(header: bytes) -> str:
    """Identifica o formato pelos primeiros bytes (não confia na extensão)."""
    signatures = {
        b"%PDF": "pdf",
        b"\xff\xd8\xff": "jpeg",
        b"\x89PNG": "png",
        b"II*\x00": "tiff",
        b"MM\x00*": "tiff",
        b"\xd0\xcf\x11\xe0": "ole",  # .doc/.xls antigos
        b"{\\rtf": "rtf",
    }
    for signature, name in signatures.items():
        if header.startswith(signature):
            return name
    if header.startswith(b"PK"):
        return "zip"
    if header.lstrip().lower().startswith((b"<!doctype html", b"<html")):
        return "html"
    return "desconhecido"


def _zip_kind(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
    except zipfile.BadZipFile:
        return "zip"
    if "word/document.xml" in names:
        return "docx"
    if "content.xml" in names:
        return "odt"
    return "zip"


def needs_ocr(native_chars: int, image_coverage: float, has_ink: bool = False) -> bool:
    """Decide se a página precisa de OCR (regras no topo do módulo)."""
    if image_coverage >= IMAGE_COVERAGE_FOR_SCAN and native_chars < MAX_CHARS_ON_SCANNED_PAGE:
        return True
    if native_chars >= MIN_NATIVE_CHARS:
        return False
    if image_coverage > 0:
        return True
    return native_chars == 0 and has_ink


def has_ink(pdfium_page, threshold: float = 0.005) -> bool:
    """Renderiza a página em baixa resolução e diz se há conteúdo visível (pixels não brancos)."""
    image = pdfium_page.render(scale=36 / 72).to_pil().convert("L")
    histogram = image.histogram()
    dark = sum(histogram[:200])
    return dark / max(sum(histogram), 1) > threshold


def _image_coverage(page) -> float:
    area = float(page.width * page.height) or 1.0
    covered = sum(
        max(0.0, (img["x1"] - img["x0"])) * max(0.0, (img["bottom"] - img["top"]))
        for img in page.images
    )
    return min(covered / area, 1.0)


def read_pdf(path: Path, ocr_dpi: int = OCR_DPI, lang: str = "por") -> list[PageContent]:
    """Lê todas as páginas de um PDF, aplicando OCR só onde precisa."""
    import pdfplumber
    import pypdfium2 as pdfium

    pages: list[PageContent] = []
    rendered = None
    with pdfplumber.open(path) as pdf:
        for number, page in enumerate(pdf.pages, start=1):
            native = [
                Word(text, w["x0"], w["top"], w["x1"], w["bottom"])
                for w in page.extract_words(use_text_flow=True)
                if (text := clean_text(w["text"]).strip())
            ]
            native_chars = sum(len(w.text) for w in native)
            coverage = _image_coverage(page)
            ink = False
            if native_chars == 0 and coverage == 0:
                if rendered is None:
                    rendered = pdfium.PdfDocument(str(path))
                ink = has_ink(rendered[number - 1])
            if not needs_ocr(native_chars, coverage, ink):
                pages.append(
                    PageContent(number, float(page.width), float(page.height), NATIVE, native)
                )
                continue
            if rendered is None:
                rendered = pdfium.PdfDocument(str(path))
            image = rendered[number - 1].render(scale=ocr_dpi / 72).to_pil()
            words, confidence = ocr_image(image, ocr_dpi, lang)
            pages.append(
                PageContent(number, float(page.width), float(page.height), OCR, words, confidence)
            )
    if rendered is not None:
        rendered.close()
    return pages


def read_image(path: Path, lang: str = "por") -> list[PageContent]:
    """Lê uma imagem (JPEG, PNG, TIFF) com OCR, uma página por quadro."""
    from PIL import Image

    pages = []
    with Image.open(path) as image:
        frame = 0
        while True:
            dpi = int((image.info.get("dpi") or (300, 300))[0]) or 300
            words, confidence = ocr_image(image.convert("RGB"), dpi, lang)
            width, height = image.size[0] * 72 / dpi, image.size[1] * 72 / dpi
            pages.append(PageContent(frame + 1, width, height, OCR, words, confidence))
            frame += 1
            try:
                image.seek(frame)
            except EOFError:
                break
    return pages


def read_document(path: Path, lang: str = "por") -> DocumentContent:
    """Lê qualquer arquivo baixado. Formatos não tratados levantam UnsupportedDocumentError."""
    with path.open("rb") as handle:
        header = handle.read(16)
    file_type = detect_file_type(header)
    if file_type == "zip":
        file_type = _zip_kind(path)
    if file_type == "pdf":
        return DocumentContent(file_type, read_pdf(path, lang=lang))
    if file_type in {"jpeg", "png", "tiff"}:
        return DocumentContent(file_type, read_image(path, lang=lang))
    raise UnsupportedDocumentError(file_type)
