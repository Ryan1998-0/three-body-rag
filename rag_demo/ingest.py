from pathlib import Path

from rag_demo.chunking import load_knowledge_base_chunks
from rag_demo.config import resolve_project_path
from rag_demo.embeddings import embed_chunks, save_embedding_matrix
from rag_demo.index_store import save_index


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_index() -> Path:
    kb_dir = resolve_project_path("RAG_KB_DIR", "data/raw", project_root=PROJECT_ROOT)
    index_dir = resolve_project_path("RAG_INDEX_DIR", "data/index", project_root=PROJECT_ROOT)
    index_path = index_dir / "chunks.json"
    embedding_path = index_dir / "embeddings.npy"
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
