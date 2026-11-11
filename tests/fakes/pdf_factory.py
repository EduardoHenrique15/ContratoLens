"""Gera PDFs fictícios pequenos para os testes: com texto nativo ou escaneados (só imagem)."""

from pathlib import Path

PAGE_WIDTH, PAGE_HEIGHT = 595, 842  # A4 em pontos


def _escape(text: str) -> bytes:
    raw = text.encode("cp1252")
    return raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def text_pdf(path: Path, pages: list[list[tuple[float, float, str]]], font_size: int = 11) -> Path:
    """Cria um PDF com texto nativo. Cada página é uma lista de (x, y_do_topo, texto) em pontos."""
    objects: list[bytes] = []
    font_id = 3
    page_ids = []
    content_ids = []
    next_id = 4
    for _ in pages:
        page_ids.append(next_id)
        content_ids.append(next_id + 1)
        next_id += 2
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = b" ".join(f"{pid} 0 R".encode() for pid in page_ids)
    objects.append(
        b"<< /Type /Pages /Kids [" + kids + b"] /Count " + str(len(pages)).encode() + b" >>"
    )
    objects.append(
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    )
    for lines, content_id in zip(pages, content_ids, strict=True):
        stream = b"".join(
            b"BT /F1 %d Tf %.1f %.1f Td (" % (font_size, x, PAGE_HEIGHT - y - font_size)
            + _escape(text)
            + b") Tj ET\n"
            for x, y, text in lines
        )
        objects.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] " % (PAGE_WIDTH, PAGE_HEIGHT)
            + b"/Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>" % (font_id, content_id)
        )
        objects.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"endstream")

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref,
    )
    path.write_bytes(bytes(out))
    return path


def scanned_pdf(path: Path, source_pdf: Path, dpi: int = 200) -> Path:
    """Cria um PDF "escaneado": as páginas de `source_pdf` viram imagens, sem texto nativo."""
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(str(source_pdf))
    images = [page.render(scale=dpi / 72).to_pil().convert("RGB") for page in document]
    document.close()
    images[0].save(path, "PDF", resolution=dpi, save_all=True, append_images=images[1:])
    return path


CONTRACT_PAGE = [
    (72, 72, "CONTRATO Nº 52/2026"),
    (72, 100, "CONTRATANTE: Município de Exemplo, CNPJ 11.222.333/0001-81."),
    (72, 116, "CONTRATADA: Empresa Fictícia Ltda, CNPJ 11.444.777/0001-61."),
    (72, 160, "CLÁUSULA PRIMEIRA - DO OBJETO"),
    (72, 176, "Aquisição de gêneros alimentícios para a rede municipal de ensino."),
    (72, 220, "CLÁUSULA SEGUNDA - DO VALOR"),
    (72, 236, "O valor total do contrato é de R$ 71.240,90."),
    (72, 280, "CLÁUSULA TERCEIRA - DA VIGÊNCIA"),
    (72, 296, "A vigência será de 14/08/2026 a 14/08/2027."),
]
