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


SELECTED_IDS = [
    "D30Q06",
    "D30Q07",
    "D30Q09",
    "D30Q13",
    "D30Q15",
    "D30Q16",
    "D30Q17",
    "D30Q20",
    "D30Q24",
    "D30Q27",
    "D30Q29",
    "D30Q30",
]

OLD_HYBRID_3PT_CEILING = {
    "D30Q06": 2,
    "D30Q07": 0,
    "D30Q09": 3,
    "D30Q13": 3,
    "D30Q15": 2,
    "D30Q16": 2,
    "D30Q17": 3,
    "D30Q20": 3,
    "D30Q24": 1,
    "D30Q27": 3,
    "D30Q29": 3,
    "D30Q30": 2,
}

OLD_HYBRID_5PT_EVIDENCE = {
    "D30Q06": 5,
    "D30Q07": 0,
    "D30Q09": 5,
    "D30Q15": 5,
    "D30Q16": 5,
    "D30Q17": 5,
    "D30Q24": 3,
    "D30Q27": 5,
    "D30Q29": 5,
}


def main() -> int:
    eval_dir = Path(__file__).resolve().parent
    question_path = eval_dir / "questions_direct30_lenient_20260615.json"
    all_questions = json.loads(question_path.read_text(encoding="utf-8"))
    selected_ids = _optional_ids(os.getenv("RAG_EVAL_IDS")) or SELECTED_IDS
    selected = set(selected_ids)
    questions = [item for item in all_questions if item["id"] in selected]

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
    raw_path = eval_dir / f"direct30_bad_open_retrieval_upper_bound_raw_{timestamp}.jsonl"
    report_path = eval_dir / f"direct30_bad_open_retrieval_upper_bound_report_{timestamp}.md"

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
            old_3pt = OLD_HYBRID_3PT_CEILING.get(item["id"])
            old_5pt = OLD_HYBRID_5PT_EVIDENCE.get(item["id"])
            record = {
                "id": item["id"],
                "question": question,
                "rewritten_query": rewritten_query,
                "current_5pt_upper": score["score"],
                "max_5pt": score["max_score"],
                "current_3pt_criteria_hits": score["criteria_hits"],
                "max_3pt": score["criteria_total"],
                "old_hybrid_3pt_ceiling": old_3pt,
                "old_hybrid_5pt_evidence": old_5pt,
                "delta_3pt": None if old_3pt is None else score["criteria_hits"] - old_3pt,
                "delta_5pt": None if old_5pt is None else score["score"] - old_5pt,
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
                f"{record['id']} current={record['current_5pt_upper']}/{record['max_5pt']} "
                f"criteria={record['current_3pt_criteria_hits']}/{record['max_3pt']} "
                f"old3={_fmt(old_3pt)}/3 elapsed={record['elapsed_seconds']}s",
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
    criteria_hits = 0
    matched = []
    missed = []
    for criterion in item.get("criteria", []):
        aliases = [normalize_text(alias) for alias in criterion.get("aliases", [])]
        if any(alias and alias in context_text for alias in aliases):
            weight = int(criterion.get("weight", 1))
            score += weight
            criteria_hits += 1
            matched.append(f"{criterion['label']} (+{weight})")
        else:
            missed.append(criterion["label"])
    return {
        "score": min(score, max_score(item)),
        "max_score": max_score(item),
        "criteria_hits": criteria_hits,
        "criteria_total": len(item.get("criteria", [])),
        "matched": matched,
        "missed": missed,
    }


def write_report(report_path: Path, raw_path: Path, question_path: Path, records, started: float, rewrite_enabled: bool) -> None:
    current_5pt = sum(record["current_5pt_upper"] for record in records)
    max_5pt = sum(record["max_5pt"] for record in records)
    current_3pt = sum(record["current_3pt_criteria_hits"] for record in records)
    max_3pt = sum(record["max_3pt"] for record in records)
    old_3pt_records = [record for record in records if record["old_hybrid_3pt_ceiling"] is not None]
    old_3pt = sum(record["old_hybrid_3pt_ceiling"] for record in old_3pt_records)
    old_3pt_max = sum(record["max_3pt"] for record in old_3pt_records)
    old_5pt_records = [record for record in records if record["old_hybrid_5pt_evidence"] is not None]
    old_5pt = sum(record["old_hybrid_5pt_evidence"] for record in old_5pt_records)
    old_5pt_max = sum(record["max_5pt"] for record in old_5pt_records)
    current_known_5pt = sum(record["current_5pt_upper"] for record in old_5pt_records)

    lines = [
        "# Direct30 Bad Open Retrieval Upper Bound",
        "",
        f"- Questions: `{question_path.name}`",
        f"- Selected IDs: `{', '.join(record['id'] for record in records)}`",
        f"- Raw JSONL: `{raw_path.name}`",
        f"- Query rewrite enabled: `{rewrite_enabled}`",
        f"- Current 5pt upper bound: **{current_5pt}/{max_5pt} = {_pct(current_5pt, max_5pt)}**",
        f"- Current 3pt criteria hit ceiling: **{current_3pt}/{max_3pt} = {_pct(current_3pt, max_3pt)}**",
        f"- Previous hybrid 3pt ceiling on same set: **{old_3pt}/{old_3pt_max} = {_pct(old_3pt, old_3pt_max)}**",
        f"- Previous hybrid 5pt evidence on known subset: **{old_5pt}/{old_5pt_max} = {_pct(old_5pt, old_5pt_max)}**",
        f"- Current 5pt on same known subset: **{current_known_5pt}/{old_5pt_max} = {_pct(current_known_5pt, old_5pt_max)}**",
        f"- Elapsed seconds: `{round(time.perf_counter() - started, 3)}`",
        "",
        "## Comparison",
        "",
        "| ID | Current 5pt | Old 5pt Evidence | Delta 5pt | Current 3pt | Old 3pt Ceiling | Delta 3pt | Missed | Top Contexts |",
        "|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for record in records:
        contexts = "<br>".join(
            f"{index + 1}. {Path(context['source']).name} / {context['title']} / {context['retrieval_method']}"
            for index, context in enumerate(record["contexts"][:8])
        )
        lines.append(
            "| {id} | {current_5}/{max_5} | {old_5} | {delta_5} | {current_3}/{max_3} | {old_3} | {delta_3} | {missed} | {contexts} |".format(
                id=record["id"],
                current_5=record["current_5pt_upper"],
                max_5=record["max_5pt"],
                old_5=_fmt(record["old_hybrid_5pt_evidence"]),
                delta_5=_fmt_delta(record["delta_5pt"]),
                current_3=record["current_3pt_criteria_hits"],
                max_3=record["max_3pt"],
                old_3=_fmt(record["old_hybrid_3pt_ceiling"]),
                delta_3=_fmt_delta(record["delta_3pt"]),
                missed="<br>".join(record["missed"]) or "-",
                contexts=contexts or "-",
            )
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Current architecture is the active retrieval path: Query Rewrite, metadata/filter helpers, BM25(original question) + Dense(original question), RRF merge, reranker, graph merge when applicable, parent chunk expansion, Top 8 context.",
            "- `Old 3pt Ceiling` comes from `direct30_failure_cause_diagnosis_20260615-074407.md` under `hybrid rerank 實驗版`.",
            "- `Old 5pt Evidence` is only available for the low-score questions explicitly listed in `direct30_retrieval_mode_comparison_with_hybrid_20260615-011430.md`; missing old 5pt values are shown as `n/a`.",
        ]
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
        "retrieval_method": chunk.get("retrieval_method", ""),
        "rerank_trace": chunk.get("rerank_trace", ""),
        "graph_trace": chunk.get("graph_trace", ""),
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


def _fmt(value) -> str:
    return "n/a" if value is None else str(value)


def _fmt_delta(value) -> str:
    if value is None:
        return "n/a"
    return f"{value:+d}"


def _pct(value: int, total: int) -> str:
    if not total:
        return "n/a"
    return f"{value / total * 100:.1f}%"


if __name__ == "__main__":
    raise SystemExit(main())
