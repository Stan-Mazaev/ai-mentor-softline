import math

from app.rag.embeddings import HashingEmbeddingProvider


def test_dim_and_normalization():
    p = HashingEmbeddingProvider(dim=64)
    vec = p.embed("выбор вуза и программы")
    assert len(vec) == 64
    norm = math.sqrt(sum(x * x for x in vec))
    assert math.isclose(norm, 1.0, rel_tol=1e-9)


def test_determinism():
    p = HashingEmbeddingProvider(dim=64)
    a = p.embed("абитуриент выбирает вуз")
    b = p.embed("абитуриент выбирает вуз")
    assert a == b


def test_similar_texts_have_higher_similarity():
    from app.rag.retrieval import cosine

    p = HashingEmbeddingProvider(dim=256)
    q = p.embed("как выбрать вуз по рейтингам")
    same = p.embed("выбор вуза рейтинги и отзывы")
    other = p.embed("первый месяц в компании онбординг")
    assert cosine(q, same) > cosine(q, other)


def test_empty_text_returns_zero_vector():
    p = HashingEmbeddingProvider(dim=32)
    assert p.embed("") == [0.0] * 32