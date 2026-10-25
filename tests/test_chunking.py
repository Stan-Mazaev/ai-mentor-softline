import pytest

from app.rag.chunking import chunk_text


def test_empty_returns_empty():
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_short_text_single_chunk():
    chunks = chunk_text("Короткий текст без абзацев.")
    assert len(chunks) == 1
    assert chunks[0].index == 0


def test_paragraphs_merge_until_max_chars():
    text = "A" * 300 + "\n\n" + "B" * 300 + "\n\n" + "C" * 300
    chunks = chunk_text(text, max_chars=800, overlap=50)
    # 300+2+300 = 602 <= 800, третья не влезет → 2 чанка
    assert len(chunks) == 2


def test_long_paragraph_splits_with_overlap():
    text = "X" * 2000
    chunks = chunk_text(text, max_chars=800, overlap=100)
    assert len(chunks) == 3
    # каждый чанк не больше max_chars
    assert all(len(c.text) <= 800 for c in chunks)


def test_invalid_overlap_raises():
    with pytest.raises(ValueError):
        chunk_text("text", max_chars=100, overlap=100)