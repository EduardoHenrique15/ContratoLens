from contratolens.documents.chunker import chunk_pages, group_lines
from contratolens.documents.types import NATIVE, PageContent, Word


def line(top, *texts, x=72.0, height=11.0):
    words, cursor = [], x
    for text in texts:
        words.append(Word(text, cursor, top, cursor + 6 * len(text), top + height))
        cursor += 6 * len(text) + 4
    return words


def test_group_lines_orders_words():
    words = line(100, "b", x=200) + line(100.5, "a", x=72) + line(130, "c")
    lines = group_lines(words)
    assert [[w.text for w in item] for item in lines] == [["a", "b"], ["c"]]


def test_splits_on_clause_heading_and_keeps_heading_with_body():
    words = (
        line(72, "CONTRATO", "Nº", "52/2026", "entre", "as", "partes", "abaixo", "assinadas")
        + line(88, "CLÁUSULA", "PRIMEIRA", "-", "DO", "OBJETO")
        + line(104, "Aquisição", "de", "gêneros", "alimentícios", "para", "a", "rede")
        + line(120, "CLÁUSULA", "SEGUNDA", "-", "DO", "VALOR")
        + line(136, "O", "valor", "total", "é", "de", "R$", "71.240,90", "conforme", "proposta")
    )
    chunks = chunk_pages([PageContent(1, 595, 842, NATIVE, words)])
    texts = [c.text for c in chunks]
    assert len(chunks) == 3
    assert texts[1].startswith("CLÁUSULA PRIMEIRA") and "gêneros" in texts[1]
    assert texts[2].startswith("CLÁUSULA SEGUNDA") and "71.240,90" in texts[2]
    assert [c.index for c in chunks] == [0, 1, 2]
    second = chunks[1]
    assert second.top == 88 and second.bottom == 115 and second.x0 == 72


def test_splits_on_large_vertical_gap():
    words = line(72, "Primeiro", "parágrafo", "com", "texto", "suficiente", "aqui") + line(
        200, "Segundo", "parágrafo", "bem", "mais", "abaixo", "na", "página"
    )
    chunks = chunk_pages([PageContent(1, 595, 842, NATIVE, words)])
    assert len(chunks) == 2


def test_long_block_is_split_under_limit():
    words = []
    for index in range(80):
        words += line(72 + index * 12, *["palavra"] * 4)
    chunks = chunk_pages([PageContent(1, 595, 2000, NATIVE, words)])
    assert len(chunks) > 1
    assert all(len(c.text) <= 1500 for c in chunks)


def test_empty_page_has_no_chunks():
    assert chunk_pages([PageContent(1, 595, 842, NATIVE, [])]) == []
