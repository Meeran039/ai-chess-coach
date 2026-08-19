import chromadb
import re

def chunk_markdown(filepath):
    """
    Splits the markdown file into chunks by section (## headers).
    Each chunk keeps its header as context.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Split on ## or ### headers, keeping the header with its content
    sections = re.split(r'\n(?=##)', content)
    chunks = []
    for section in sections:
        section = section.strip()
        if section and not section.startswith("# Chess"):  # skip the top title-only chunk
            chunks.append(section)
    return chunks

def build_vector_db(md_path="rag/opening_theory.md", db_path="chroma_db", collection_name="chess_theory"):
    chunks = chunk_markdown(md_path)
    print(f"Split into {len(chunks)} chunks")

    client = chromadb.PersistentClient(path=db_path)

    # Delete old collection if it exists, so re-running doesn't duplicate
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass

    collection = client.create_collection(collection_name)

    ids = [f"chunk_{i}" for i in range(len(chunks))]
    collection.add(
        documents=chunks,
        ids=ids
    )

    print(f"Ingested {len(chunks)} chunks into ChromaDB collection '{collection_name}'")
    return collection

if __name__ == "__main__":
    build_vector_db()