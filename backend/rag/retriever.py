import chromadb

def get_relevant_theory(query_text, db_path="chroma_db", collection_name="chess_theory", n_results=2):
    """
    Given a query (e.g., a blunder description), retrieve the most relevant
    chunks of chess theory from ChromaDB.
    """
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_collection(collection_name)

    results = collection.query(
        query_texts=[query_text],
        n_results=n_results
    )

    return results["documents"][0]  # list of matched chunk texts


if __name__ == "__main__":
    # Quick test with a sample blunder description
    test_query = "moving the bishop to an aggressive square too early before castling, losing material"
    theory = get_relevant_theory(test_query)

    print(f"Query: {test_query}\n")
    print("Retrieved theory:\n")
    for i, chunk in enumerate(theory, 1):
        print(f"--- Chunk {i} ---")
        print(chunk[:300])
        print()