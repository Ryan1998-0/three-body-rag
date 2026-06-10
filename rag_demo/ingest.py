from pathlib import Path

from rag_demo.chunking import load_knowledge_base_chunks
from rag_demo.embeddings import embed_chunks, save_embedding_matrix
from rag_demo.index_store import save_index


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_index() -> Path:
    kb_dir = PROJECT_ROOT / "data" / "avalon-game-records"
    index_path = PROJECT_ROOT / "data" / "index" / "chunks.json"
    embedding_path = PROJECT_ROOT / "data" / "index" / "embeddings.npy"
    chunks = load_knowledge_base_chunks(kb_dir)
    save_index(chunks, index_path)
    embeddings = embed_chunks(chunks)
    save_embedding_matrix(embeddings, embedding_path)
    return index_path


def main() -> None:
    index_path = build_index()
    print(f"Index written: {index_path}")
    print(f"Embeddings written: {index_path.parent / 'embeddings.npy'}")


if __name__ == "__main__":
    main()
