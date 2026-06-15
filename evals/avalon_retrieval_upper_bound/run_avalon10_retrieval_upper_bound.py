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

from rag_demo.embeddings import load_embedding_matrix
from rag_demo.event_list_retrieval import (
    find_event_list_chunks,
    find_result_constrained_chunks,
    merge_event_list_chunks,
)
from rag_demo.index_store import load_index
from rag_demo.query import _rrf_parent_context_results
from rag_demo.query_rewriter import rewrite_query_for_retrieval


def main() -> int:
    eval_dir = Path(__file__).resolve().parent
    question_file = os.getenv("RAG_EVAL_QUESTION_FILE", "questions_avalon10.json")
    question_path = eval_dir / question_file
    questions = json.loads(question_path.read_text(encoding="utf-8"))

    index_dir = Path(os.getenv("RAG_INDEX_DIR", "data/index_avalon"))
    chunks = load_index(index_dir / "chunks.json")
    embeddings = load_embedding_matrix(index_dir / "embeddings.npy")
    section_titles = _section_titles(chunks)

    candidate_k = int(os.getenv("RAG_RETRIEVAL_CANDIDATE_K", "50"))
    rerank_top_k = int(os.getenv("RAG_RETRIEVAL_RERANK_TOP_K", "12"))
    final_context_k = int(os.getenv("RAG_FINAL_CONTEXT_K", "8"))
    rewrite_enabled = _bool_env("RAG_QUERY_REWRITE_ENABLED", False)
    structured_enabled = _bool_env("RAG_USE_STRUCTURED_RETRIEVAL", False)
    exact_round_oracle_enabled = _bool_env("RAG_EXACT_ROUND_ORACLE", False)
    model = os.getenv("RAG_EVAL_MODEL", "qwen2.5:7b")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    raw_path = eval_dir / f"avalon10_retrieval_upper_bound_raw_{timestamp}.jsonl"
    report_path = eval_dir / f"avalon10_retrieval_upper_bound_report_{timestamp}.md"

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
            if structured_enabled:
                structured_results = merge_event_list_chunks(
                    find_result_constrained_chunks(question, chunks, max_results=final_context_k),
                    find_event_list_chunks(question, chunks, max_results=final_context_k),
                )
                results = merge_event_list_chunks(structured_results, results)[:final_context_k]
            if exact_round_oracle_enabled:
                round_results = _exact_round_chunks(question, chunks)
                results = merge_event_list_chunks(round_results, results)[:final_context_k]
            score = score_retrieved_context(results, item)
            record = {
                "id": item["id"],
                "question": question,
                "rewritten_query": rewritten_query,
                "retrieval_upper_bound_score": score["score"],
                "max_score": score["max_score"],
                "percentage": round(score["score"] / score["max_score"] * 100, 2)
                if score["max_score"]
                else 0,
                "matched": score["matched"],
                "missed": score["missed"],
                "rewrite_enabled": rewrite_enabled,
                "structured_retrieval_enabled": structured_enabled,
                "exact_round_oracle_enabled": exact_round_oracle_enabled,
                "rewrite_error": rewrite_error,
                "contexts": [_context_record(chunk) for chunk in results],
                "elapsed_seconds": round(time.perf_counter() - q_started, 3),
            }
            records.append(record)
            raw_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            raw_file.flush()
            print(
                f"{record['id']} retrieval_upper={record['retrieval_upper_bound_score']}/"
                f"{record['max_score']} contexts={len(record['contexts'])} "
                f"elapsed={record['elapsed_seconds']}s",
                flush=True,
            )

    write_report(report_path, raw_path, question_path, records, started)
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


def write_report(report_path: Path, raw_path: Path, question_path: Path, records, started: float) -> None:
    total_score = sum(record["retrieval_upper_bound_score"] for record in records)
    total_max = sum(record["max_score"] for record in records)
    percentage = round(total_score / total_max * 100, 2) if total_max else 0
    lines = [
        "# Avalon10 Retrieval Upper Bound",
        "",
        f"- Questions: `{question_path.name}`",
        f"- Raw JSONL: `{raw_path.name}`",
        f"- Total: **{total_score}/{total_max} ({percentage}%)**",
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


def _exact_round_chunks(question: str, chunks):
    match = re.search(r"第\s*(\d+)\s*輪", question)
    if not match:
        return []
    round_title = f"第{match.group(1)}輪"
    results = []
    for chunk in chunks:
        title = str(chunk.get("title", ""))
        parent = str(chunk.get("parent_title", ""))
        if round_title in title or round_title in parent:
            result = dict(chunk)
            result["exact_round_oracle_match"] = True
            results.append(result)
    results.sort(key=lambda item: int(item.get("chunk_index", 0)))
    return results


def _bool_env(key: str, default: bool) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    raise SystemExit(main())
