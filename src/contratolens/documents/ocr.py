"""OCR com Tesseract (idioma por), devolvendo palavras com coordenadas em pontos do PDF."""

from PIL import Image

from contratolens.documents.types import Word, clean_text

POINTS_PER_INCH = 72


def ocr_image(image: Image.Image, dpi: int, lang: str = "por") -> tuple[list[Word], float | None]:
    """Roda o Tesseract na imagem e converte as caixas de pixels para pontos.

    Devolve as palavras e a confiança média (0 a 100) das palavras reconhecidas.
    """
    import pytesseract

    data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)
    scale = POINTS_PER_INCH / dpi
    words: list[Word] = []
    confidences: list[float] = []
    for text, conf, left, top, width, height in zip(
        data["text"],
        data["conf"],
        data["left"],
        data["top"],
        data["width"],
        data["height"],
        strict=True,
    ):
        text = clean_text(text).strip()
        confidence = float(conf)
        if not text or confidence < 0:
            continue
        words.append(
            Word(text, left * scale, top * scale, (left + width) * scale, (top + height) * scale)
        )
        confidences.append(confidence)
    mean = round(sum(confidences) / len(confidences), 1) if confidences else None
    return words, mean
