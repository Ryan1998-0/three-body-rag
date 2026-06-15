from datetime import datetime
from pathlib import Path
import json
import os
import re
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag_demo.chunking import load_knowledge_base_chunks
from rag_demo.config import RagConfig, resolve_project_path
from rag_demo.embeddings import load_embedding_matrix
from rag_demo.index_store import load_index
from rag_demo.query import _rrf_parent_context_results
from rag_demo.query_rewriter import rewrite_query_for_retrieval


def main() -> int:
    eval_dir = Path(__file__).resolve().parent
    question_path = eval_dir / "questions_first20_closed_20260615.json"
    questions = json.loads(question_path.read_text(encoding="utf-8"))
    selected_ids = _optional_ids(os.getenv("RAG_EVAL_IDS"))
    if selected_ids:
        selected = set(selected_ids)
        questions = [item for item in questions if item["id"] in selected]

    config = RagConfig.from_env()
    candidate_k = int(os.getenv("RAG_RETRIEVAL_CANDIDATE_K", str(config.retrieval_candidate_k)))
    rerank_top_k = int(os.getenv("RAG_RETRIEVAL_RERANK_TOP_K", "12"))
    final_context_k = int(os.getenv("RAG_FINAL_CONTEXT_K", "8"))
    rewrite_enabled = _bool_env("RAG_QUERY_REWRITE_ENABLED", True)
    model = os.getenv("RAG_EVAL_MODEL", "qwen2.5:7b")

    chunks = _load_chunks()
    embeddings = _load_embeddings()
    section_titles = _section_titles(chunks)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    raw_path = eval_dir / f"first20_retrieval_upper_bound_raw_{timestamp}.jsonl"
    report_path = eval_dir / f"first20_retrieval_upper_bound_report_{timestamp}.md"

    started = time.perf_counter()
    records = []
    with raw_path.open("w", encoding="utf-8") as raw_file:
        for item in questions:
            q_started = time.perf_counter()
            question = item["question"]
            rewritten_query = question
            rewrite_error = None
            if rewrite_enabled:
                try:
                    rewritten_query = rewrite_query_for_retrieval(
                        question,
                        model=model,
                        section_titles=section_titles,
                    )
                except Exception as exc:
                    rewrite_error = f"{type(exc).__name__}: {exc}"

            results = _rrf_parent_context_results(
                question=question,
                rewritten_query=rewritten_query,
                chunks=chunks,
                embeddings=embeddings,
                top_k=rerank_top_k,
                candidate_k=candidate_k,
                final_context_k=final_context_k,
            )
            score = score_retrieved_context(results, item)
            record = {
                "id": item["id"],
                "category": item.get("category", ""),
                "question": question,
                "rewritten_query": rewritten_query,
                "standard_answer": item["standard_answer"],
                "retrieval_upper_bound_score": score["score"],
                "max_score": score["max_score"],
                "matched": score["matched"],
                "missed": score["missed"],
                "rewrite_error": rewrite_error,
                "contexts": [_context_record(chunk) for chunk in results],
                "elapsed_seconds": round(time.perf_counter() - q_started, 3),
            }
            records.append(record)
            raw_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            raw_file.flush()
            print(
                f"{record['id']} retrieval_upper={record['retrieval_upper_bound_score']}/{record['max_score']} "
                f"contexts={len(record['contexts'])} elapsed={record['elapsed_seconds']}s",
                flush=True,
            )

    write_report(report_path, raw_path, question_path, records, started, rewrite_enabled)
    print(f"Raw JSONL: {raw_path}", flush=True)
    print(f"Report: {report_path}", flush=True)
    return 0


def score_retrieved_context(chunks, item: dict) -> dict:
    context_text = normalize_text(
        "\n".join(
            f"{chunk.get('parent_title', '')}\n{chunk.get('title', '')}\n{chunk.get('content', '')}"
            for chunk in chunks
        )
    )
    score = 0
    matched = []
    missed = []
    for criterion in item.get("criteria", []):
        aliases = [normalize_text(alias) for alias in criterion.get("aliases", [])]
        if any(alias and alias in context_text for alias in aliases):
            weight = int(criterion.get("weight", 1))
            score += weight
            matched.append(f"{criterion['label']} (+{weight})")
        else:
            missed.append(criterion["label"])
    return {
        "score": min(score, max_score(item)),
        "max_score": max_score(item),
        "matched": matched,
        "missed": missed,
    }


def write_report(report_path: Path, raw_path: Path, question_path: Path, records, started: float, rewrite_enabled: bool) -> None:
    total_score = sum(record["retrieval_upper_bound_score"] for record in records)
    total_max = sum(record["max_score"] for record in records)
    lines = [
        "# First20 Retrieval Upper Bound",
        "",
        f"- Questions: `{question_path.name}`",
        f"- Raw JSONL: `{raw_path.name}`",
        f"- Query rewrite enabled: `{rewrite_enabled}`",
        f"- Total: **{total_score}/{total_max}**",
        f"- Elapsed seconds: `{round(time.perf_counter() - started, 3)}`",
        "",
        "| ID | Retrieval Upper | Matched | Missed | Top Contexts |",
        "|---|---:|---|---|---|",
    ]
    for record in records:
        contexts = "<br>".join(
            f"{index + 1}. {Path(context['source']).name} / {context['title']}"
            for index, context in enumerate(record["contexts"][:8])
        )
        lines.append(
            "| {id} | {score}/{max_score} | {matched} | {missed} | {contexts} |".format(
                id=record["id"],
                score=record["retrieval_upper_bound_score"],
                max_score=record["max_score"],
                matched="<br>".join(record["matched"]) or "-",
                missed="<br>".join(record["missed"]) or "-",
                contexts=contexts or "-",
            )
        )

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def max_score(item: dict) -> int:
    return sum(int(criterion.get("weight", 1)) for criterion in item.get("criteria", []))


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", str(text)).lower()


def _load_chunks():
    kb_dir = resolve_project_path("RAG_KB_DIR", "data/raw", project_root=ROOT)
    index_dir = resolve_project_path("RAG_INDEX_DIR", "data/index", project_root=ROOT)
    index_path = index_dir / "chunks.json"
    if index_path.exists():
        return load_index(index_path)
    return load_knowledge_base_chunks(kb_dir)


def _load_embeddings():
    index_dir = resolve_project_path("RAG_INDEX_DIR", "data/index", project_root=ROOT)
    embedding_path = index_dir / "embeddings.npy"
    if not embedding_path.exists():
        return None
    return load_embedding_matrix(embedding_path)


def _section_titles(chunks):
    titles = []
    for chunk in chunks:
        for title in (chunk.get("parent_title", ""), chunk.get("title", "")):
            cleaned = str(title).strip()
            if cleaned:
                titles.append(cleaned)
    return list(dict.fromkeys(titles))[:200]


def _context_record(chunk):
    return {
        "id": chunk.get("id", ""),
        "source": chunk.get("source", ""),
        "parent_title": chunk.get("parent_title", ""),
        "title": chunk.get("title", ""),
        "score": chunk.get("score", 0),
        "rerank_trace": chunk.get("rerank_trace", ""),
        "content": chunk.get("content", ""),
    }


def _optional_ids(raw_value: str):
    if not raw_value:
        return []
    return [value.strip() for value in raw_value.split(",") if value.strip()]


def _bool_env(key: str, default: bool) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    raise SystemExit(main())
