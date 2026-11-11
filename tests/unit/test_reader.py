import shutil

import pytest

from contratolens.documents.reader import (
    UnsupportedDocumentError,
    detect_file_type,
    needs_ocr,
    read_document,
)
from contratolens.documents.types import NATIVE, OCR
from tests.fakes.pdf_factory import CONTRACT_PAGE, scanned_pdf, text_pdf

needs_tesseract = pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract ausente")


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (b"%PDF-1.7", "pdf"),
        (b"\xff\xd8\xff\xe0", "jpeg"),
        (b"\x89PNG\r\n", "png"),
        (b"PK\x03\x04", "zip"),
        (b"\xd0\xcf\x11\xe0", "ole"),
        (b"  <!DOCTYPE html>", "html"),
        (b"xyz", "desconhecido"),
    ],
)
def test_detect_file_type(header, expected):
    assert detect_file_type(header) == expected


def test_needs_ocr_rules():
    assert needs_ocr(native_chars=0, image_coverage=1.0)  # página escaneada
    assert needs_ocr(native_chars=120, image_coverage=0.9)  # carimbo sobre página escaneada
    assert not needs_ocr(native_chars=2000, image_coverage=0.9)  # texto sobre imagem de fundo
    assert not needs_ocr(native_chars=800, image_coverage=0.0)
    assert needs_ocr(native_chars=10, image_coverage=0.2)  # pouco texto e alguma imagem
    assert not needs_ocr(native_chars=21, image_coverage=0.0)  # página curta de verdade
    assert not needs_ocr(native_chars=0, image_coverage=0.0, has_ink=False)  # página em branco
    assert needs_ocr(native_chars=0, image_coverage=0.0, has_ink=True)  # imagem não detectada


def test_reads_native_text_with_coordinates(tmp_path):
    path = text_pdf(
        tmp_path / "nativo.pdf", [CONTRACT_PAGE, [(72, 72, "Página dois do contrato.")]]
    )
    content = read_document(path)
    assert content.file_type == "pdf"
    assert [page.source for page in content.pages] == [NATIVE, NATIVE]
    assert content.ocr_pages == 0
    words = {w.text: w for w in content.pages[0].words}
    assert "71.240,90." in words
    valor = words["71.240,90."]
    assert 230 < valor.top < 250 and valor.x0 > 72  # linha "O valor total..." começa em y=236
    assert "gêneros" in words  # acentos preservados


@needs_tesseract
def test_ocr_on_scanned_page(tmp_path):
    source = text_pdf(tmp_path / "fonte.pdf", [CONTRACT_PAGE])
    scanned = scanned_pdf(tmp_path / "escaneado.pdf", source)
    content = read_document(scanned)
    page = content.pages[0]
    assert page.source == OCR and content.ocr_pages == 1
    text = " ".join(w.text for w in page.words)
    assert "CONTRATO" in text and "71.240,90" in text
    assert page.ocr_confidence > 70
    # As coordenadas do OCR ficam em pontos do PDF, perto das posições originais.
    valor = next(w for w in page.words if "71.240" in w.text)
    assert 225 < valor.top < 255


def test_unsupported_format(tmp_path):
    path = tmp_path / "arquivo.pdf"
    path.write_bytes(b"\xd0\xcf\x11\xe0" + b"0" * 100)
    with pytest.raises(UnsupportedDocumentError) as error:
        read_document(path)
    assert str(error.value) == "ole"


def test_detects_docx_inside_zip(tmp_path):
    import zipfile

    path = tmp_path / "contrato.pdf"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", "<w:document/>")
    with pytest.raises(UnsupportedDocumentError) as error:
        read_document(path)
    assert str(error.value) == "docx"


def test_clean_text_removes_control_and_invisible_chars():
    from contratolens.documents.types import clean_text

    assert clean_text("CON\x00TRATO​ nº\x07 1") == "CONTRATO nº 1"
    assert clean_text("linha\nnova\tcom tab") == "linha\nnova\tcom tab"


def test_reader_cleans_text_returned_by_pdfplumber(tmp_path, monkeypatch):
    """O PDF real (contrato de PE) trouxe \x00 no texto extraído; o leitor precisa limpá-lo."""
    import pdfplumber

    path = text_pdf(tmp_path / "a.pdf", [CONTRACT_PAGE])
    original_open = pdfplumber.open

    def open_with_nul(*args, **kwargs):
        pdf = original_open(*args, **kwargs)
        page = pdf.pages[0]
        extract = page.extract_words
        page.extract_words = lambda **kw: [
            {**w, "text": w["text"].replace("CONTRATO", "CON\x00TRATO")} for w in extract(**kw)
        ]
        return pdf

    monkeypatch.setattr(pdfplumber, "open", open_with_nul)
    content = read_document(path)
    texts = [w.text for w in content.pages[0].words]
    assert "CONTRATO" in texts
    assert not any("\x00" in t for t in texts)
