"""Verificação da Fase 0: OCR (Tesseract, idioma por) na primeira página de um PDF escaneado.

Renderiza a página com pypdfium2, roda o Tesseract e mostra tempo, quantidade de texto,
confiança média e um trecho curto com CPFs mascarados. Não chama nenhum serviço externo.

Uso (PowerShell): .\\.venv\\Scripts\\python.exe scripts\\verificar_ocr.py "$env:TEMP\\contrato_teste.pdf"
"""

import re
import sys
import time

import pypdfium2 as pdfium
import pytesseract

CPF_PATTERN = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
DPI = 300


def main() -> int:
    """Faz o OCR da primeira página e mostra as métricas da verificação."""
    if len(sys.argv) != 2:
        print("Uso: python scripts/verificar_ocr.py caminho/do/arquivo.pdf")
        return 1
    pdf = pdfium.PdfDocument(sys.argv[1])
    page = pdf[0]
    native_text = page.get_textpage().get_text_range().strip()
    print(f"Páginas no PDF: {len(pdf)}")
    print(f"Caracteres de texto nativo na página 1: {len(native_text)}")

    start = time.perf_counter()
    image = page.render(scale=DPI / 72).to_pil()
    data = pytesseract.image_to_data(
        image, lang="por", output_type=pytesseract.Output.DICT
    )
    elapsed = time.perf_counter() - start

    words = [w for w in data["text"] if w.strip()]
    confidences = [float(c) for c, w in zip(data["conf"], data["text"]) if w.strip()]
    text = " ".join(words)
    mean_conf = sum(confidences) / len(confidences) if confidences else 0.0

    print(f"Tempo de OCR da página 1 ({DPI} dpi): {elapsed:.2f} s")
    print(f"Palavras reconhecidas: {len(words)}")
    print(f"Confiança média do Tesseract: {mean_conf:.1f}")
    print("Trecho (CPFs mascarados):")
    print(CPF_PATTERN.sub("***.***.***-**", text[:400]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
