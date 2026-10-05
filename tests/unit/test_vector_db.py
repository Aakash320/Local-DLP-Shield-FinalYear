import chromadb


def test_vector_roundtrip(tmp_path):
    client = chromadb.PersistentClient(path=str(tmp_path))
    col = client.get_or_create_collection("test", metadata={"hnsw:space": "cosine"})
    col.add(
        ids=["a", "b"],
        embeddings=[[1, 0, 0, 0], [0, 1, 0, 0]],
        documents=["first", "second"],
    )
    res = col.query(query_embeddings=[[1, 0, 0, 0]], n_results=1)
    assert res["ids"][0][0] == "a"
