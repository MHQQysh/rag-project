from rag_app.chunking import TextUnit, chunk_units


def test_chunking_preserves_locator_and_limits_size():
    text = "第一段。" * 80 + "\n第二段说明。" * 60
    chunks = chunk_units([TextUnit(text, "第 2 页")], chunk_size=120, overlap=20)
    assert len(chunks) > 2
    assert all(len(chunk.text) <= 120 for chunk in chunks)
    assert all(chunk.locator == "第 2 页" for chunk in chunks)
    assert [chunk.index for chunk in chunks] == list(range(len(chunks)))


def test_chunking_rejects_invalid_overlap():
    try:
        chunk_units([TextUnit("text")], chunk_size=100, overlap=100)
    except ValueError as error:
        assert "overlap" in str(error)
    else:
        raise AssertionError("expected ValueError")
