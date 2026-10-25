from app.rag.retrieval import cosine, top_k


def test_cosine_identical():
    v = [1.0, 0.0, 0.0]
    assert cosine(v, v) == 1.0


def test_cosine_orthogonal():
    assert cosine([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_cosine_mismatched_lengths():
    assert cosine([1.0], [1.0, 0.0]) == 0.0


def test_top_k_orders_by_score():
    from app.models.knowledge_chunk import KnowledgeChunk
    import uuid

    c1 = KnowledgeChunk(scenario_id=uuid.uuid4(), source_url="a", source_title="",
                        source_type="open", chunk_index=0, content="a",
                        embedding=[1.0, 0.0], meta={})
    c2 = KnowledgeChunk(scenario_id=uuid.uuid4(), source_url="b", source_title="",
                        source_type="open", chunk_index=0, content="b",
                        embedding=[0.0, 1.0], meta={})
    hits = top_k([1.0, 0.0], [c1, c2], k=2)
    assert hits[0].chunk is c1
    assert hits[0].score > hits[1].score