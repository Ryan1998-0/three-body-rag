from datetime import datetime
from pathlib import Path
from time import perf_counter
import json
import os
import re
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("RAG_PROFILE", "three_body_trilogy")

from rag_demo.chunking import load_knowledge_base_chunks
from rag_demo.config import RagConfig
from rag_demo.embeddings import load_embedding_matrix
from rag_demo.index_store import load_index
from rag_demo.knowledge_base import active_knowledge_base
from rag_demo.qa_agent import answer_with_qa_agent
from rag_demo.query import _rrf_parent_context_results, _section_titles
from rag_demo.query_rewriter import rewrite_query_for_retrieval
from rag_demo.vector_store import load_or_build_qdrant_vector_store


EVAL_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = EVAL_DIR / "qa_agent_comparison"
READER300_FILE = EVAL_DIR / "questions_trilogy_300_reader.json"
MIXED200_FILE = EVAL_DIR / "questions_trilogy_mixed200_20260620-045105.json"
EMPTY_ALIASES_FILE = OUTPUT_DIR / "empty_aliases.json"


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not EMPTY_ALIASES_FILE.exists():
        EMPTY_ALIASES_FILE.write_text("[]\n", encoding="utf-8")

    run_id = os.getenv("RAG_QA_COMPARE_RUN_ID") or datetime.now().strftime("%Y%m%d-%H%M%S")
    raw_path = OUTPUT_DIR / f"qa_agent_comparison_raw_{run_id}.jsonl"
    report_path = OUTPUT_DIR / f"qa_agent_comparison_report_{run_id}.md"
    log_path = OUTPUT_DIR / f"qa_agent_comparison_progress_{run_id}.log"

    model = os.getenv("RAG_EVAL_MODEL", "ollama:qwen2.5:7b")
    final_context_k = int(os.getenv("RAG_FINAL_CONTEXT_K", "8"))
    limit = _optional_int(os.getenv("RAG_QA_COMPARE_LIMIT"))
    selected_variants = _selected_variants()

    chunks = _load_chunks()
    embeddings = _load_embeddings()
    vector_store = _load_vector_store(chunks, embeddings)
    section_titles = _section_titles(chunks)
    config = RagConfig.from_env()
    candidate_k = int(os.getenv("RAG_RETRIEVAL_CANDIDATE_K", str(config.retrieval_candidate_k)))

    variants = _build_variants(limit=limit)
    if selected_variants:
        variants = [variant for variant in variants if variant["name"] in selected_variants]

    completed = _load_completed(raw_path)
    rewrite_cache = _load_rewrite_cache(raw_path)
    started = perf_counter()
    total_expected = sum(len(variant["questions"]) for variant in variants)
    remaining = sum(
        1
        for variant in variants
        for item in variant["questions"]
        if (variant["name"], item["id"]) not in completed
    )

    _log(
        log_path,
        f"run_id={run_id} model={model} total_expected={total_expected} "
        f"completed={len(completed)} remaining={remaining}",
    )

    with raw_path.open("a", encoding="utf-8") as raw_file:
        for variant in variants:
            for index, item in enumerate(variant["questions"], start=1):
                key = (variant["name"], item["id"])
                if key in completed:
                    continue
                record_started = perf_counter()
                record = run_question(
                    item=item,
                    variant=variant,
                    chunks=chunks,
                    embeddings=embeddings,
                    vector_store=vector_store,
                    section_titles=section_titles,
                    model=model,
                    candidate_k=candidate_k,
                    final_context_k=final_context_k,
                    rewrite_cache=rewrite_cache,
                )
                record["elapsed_seconds"] = round(perf_counter() - record_started, 3)
                raw_file.write(json.dumps(record, ensure_ascii=False) + "\n")
                raw_file.flush()
                completed.add(key)
                if record.get("rewritten_query"):
                    rewrite_cache[record["question"]] = record["rewritten_query"]
                progress = (
                    f"{variant['name']} {index}/{len(variant['questions'])} "
                    f"{record['id']} qa={record['qa_score']}/{record['max_score']} "
                    f"retrieval={record['retrieval_upper_bound']}/{record['max_score']} "
                    f"elapsed={record['elapsed_seconds']}s error={record['error'] is not None}"
                )
                print(progress, flush=True)
                _log(log_path, progress)
                write_report(
                    report_path=report_path,
                    raw_path=raw_path,
                    run_id=run_id,
                    model=model,
                    records=_read_records(raw_path),
                    started=started,
                )

    records = _read_records(raw_path)
    write_report(
        report_path=report_path,
        raw_path=raw_path,
        run_id=run_id,
        model=model,
        records=records,
        started=started,
    )
    print(f"Raw JSONL: {raw_path}", flush=True)
    print(f"Report: {report_path}", flush=True)
    return 0 if all(record.get("error") is None for record in records) else 1


def run_question(
    item,
    variant,
    chunks,
    embeddings,
    vector_store,
    section_titles,
    model: str,
    candidate_k: int,
    final_context_k: int,
    rewrite_cache,
) -> dict:
    previous_alias_path = os.environ.get("RAG_ENTITY_ALIASES")
    if variant["alias_mode"] == "disabled":
        os.environ["RAG_ENTITY_ALIASES"] = str(EMPTY_ALIASES_FILE)
    else:
        os.environ.pop("RAG_ENTITY_ALIASES", None)

    question = item["question"]
    record = {
        "variant": variant["name"],
        "question_set": variant["question_set"],
        "alias_mode": variant["alias_mode"],
        "id": item["id"],
        "book": item.get("book", ""),
        "type": item.get("type", ""),
        "answer_style": item.get("answer_style", ""),
        "prompt_style": item.get("prompt_style", ""),
        "length_style": item.get("length_style", ""),
        "phrasing": item.get("phrasing", ""),
        "user_level": item.get("user_level", ""),
        "question": question,
        "standard_answer": item.get("standard_answer", ""),
        "rewritten_query": rewrite_cache.get(question, ""),
        "rewrite_error": None,
        "contexts": [],
        "final_answer": "",
        "qa_score": 0,
        "retrieval_upper_bound": 0,
        "max_score": max_score(item),
        "qa_matched": [],
        "qa_missed": [],
        "retrieval_matched": [],
        "retrieval_missed": [],
        "error": None,
        "elapsed_seconds": None,
    }

    try:
        if not record["rewritten_query"]:
            try:
                record["rewritten_query"] = rewrite_query_for_retrieval(
                    question,
                    model=model,
                    section_titles=section_titles,
                )
            except Exception as exc:
                record["rewrite_error"] = f"{type(exc).__name__}: {exc}"
                record["rewritten_query"] = question

        results = _rrf_parent_context_results(
            question=question,
            rewritten_query=record["rewritten_query"],
            chunks=chunks,
            embeddings=embeddings,
            top_k=final_context_k,
            candidate_k=candidate_k,
            final_context_k=final_context_k,
            vector_store=vector_store,
        )
        record["contexts"] = [_context_record(chunk) for chunk in results]
        retrieval_score = score_text(_contexts_text(results), item["criteria"])
        record["retrieval_upper_bound"] = retrieval_score["score"]
        record["retrieval_matched"] = retrieval_score["matched"]
        record["retrieval_missed"] = retrieval_score["missed"]

        answer = answer_with_qa_agent(
            original_question=question,
            refined_question=question,
            keywords=[],
            chunks=results,
            model=model,
        )
        record["final_answer"] = answer.strip()
        qa_score = score_text(record["final_answer"], item["criteria"])
        record["qa_score"] = qa_score["score"]
        record["qa_matched"] = qa_score["matched"]
        record["qa_missed"] = qa_score["missed"]
    except Exception as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
        record["qa_missed"] = [criterion["label"] for criterion in item["criteria"]]
        record["retrieval_missed"] = [criterion["label"] for criterion in item["criteria"]]
    finally:
        if previous_alias_path is None:
            os.environ.pop("RAG_ENTITY_ALIASES", None)
        else:
            os.environ["RAG_ENTITY_ALIASES"] = previous_alias_path
    return record


def write_report(report_path: Path, raw_path: Path, run_id: str, model: str, records, started: float) -> None:
    by_variant = {}
    for record in records:
        by_variant.setdefault(record["variant"], []).append(record)

    lines = [
        "# QA Agent Comparison",
        "",
        f"- Run ID: `{run_id}`",
        f"- Model: `{model}`",
        f"- Raw JSONL: `{raw_path.relative_to(ROOT)}`",
        f"- Elapsed Seconds This Session: `{round(perf_counter() - started, 3)}`",
        "",
        "## Summary",
        "",
        "| Variant | Questions Done | QA Score | QA % | Retrieval Upper Bound | Retrieval % | Errors |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for variant_name in sorted(by_variant):
        items = by_variant[variant_name]
        max_total = sum(int(record.get("max_score", 0)) for record in items)
        qa_total = sum(int(record.get("qa_score", 0)) for record in items)
        retrieval_total = sum(int(record.get("retrieval_upper_bound", 0)) for record in items)
        errors = sum(1 for record in items if record.get("error"))
        lines.append(
            f"| {_variant_label(variant_name)} | {len(items)} | "
            f"`{qa_total}/{max_total}` | `{_percent(qa_total, max_total)}%` | "
            f"`{retrieval_total}/{max_total}` | `{_percent(retrieval_total, max_total)}%` | {errors} |"
        )

    lines.extend(
        [
            "",
            "## Delta",
            "",
            "| Pair | QA Delta | Retrieval Delta |",
            "| --- | ---: | ---: |",
        ]
    )
    for base, strong in (
        ("reader300_plain", "reader300_strengthened"),
        ("mixed200_plain", "mixed200_strengthened"),
    ):
        if base not in by_variant or strong not in by_variant:
            continue
        base_summary = _summary(by_variant[base])
        strong_summary = _summary(by_variant[strong])
        lines.append(
            f"| {_variant_label(base)} -> {_variant_label(strong)} | "
            f"`{strong_summary['qa_percent'] - base_summary['qa_percent']:.1f} pp` | "
            f"`{strong_summary['retrieval_percent'] - base_summary['retrieval_percent']:.1f} pp` |"
        )

    lines.extend(["", "## Error Records", ""])
    error_records = [record for record in records if record.get("error")]
    if not error_records:
        lines.append("No errors recorded so far.")
    else:
        lines.extend(
            f"- `{record['variant']}` `{record['id']}`: {record['error']}"
            for record in error_records[:80]
        )

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_variants(limit=None):
    reader300 = json.loads(READER300_FILE.read_text(encoding="utf-8"))
    mixed200 = json.loads(MIXED200_FILE.read_text(encoding="utf-8"))
    if limit is not None:
        reader300 = reader300[:limit]
        mixed200 = mixed200[:limit]
    return [
        {
            "name": "reader300_plain",
            "question_set": "三體三部曲 Reader 300",
            "alias_mode": "disabled",
            "questions": reader300,
        },
        {
            "name": "reader300_strengthened",
            "question_set": "三體三部曲 Reader 300",
            "alias_mode": "strengthened",
            "questions": reader300,
        },
        {
            "name": "mixed200_plain",
            "question_set": "三體三部曲 Mixed 200",
            "alias_mode": "disabled",
            "questions": mixed200,
        },
        {
            "name": "mixed200_strengthened",
            "question_set": "三體三部曲 Mixed 200",
            "alias_mode": "strengthened",
            "questions": mixed200,
        },
    ]


def _variant_label(variant_name: str) -> str:
    labels = {
        "reader300_plain": "Reader 300 原版",
        "reader300_strengthened": "Reader 300 附檢索詞表",
        "mixed200_plain": "Mixed 200 原版",
        "mixed200_strengthened": "Mixed 200 附檢索詞表",
    }
    return labels.get(variant_name, variant_name)


def _selected_variants():
    raw = os.getenv("RAG_QA_COMPARE_VARIANTS", "").strip()
    if not raw:
        return set()
    return {item.strip() for item in raw.split(",") if item.strip()}


def score_text(text: str, criteria) -> dict:
    normalized = normalize_text(text)
    score = 0
    matched = []
    missed = []
    for criterion in criteria:
        aliases = [normalize_text(alias) for alias in criterion.get("aliases", [])]
        if any(alias and alias in normalized for alias in aliases):
            weight = int(criterion.get("weight", 1))
            score += weight
            matched.append(f"{criterion['label']} (+{weight})")
        else:
            missed.append(criterion["label"])
    return {"score": min(score, sum(int(c.get("weight", 1)) for c in criteria)), "matched": matched, "missed": missed}


def max_score(item: dict) -> int:
    return sum(int(criterion.get("weight", 1)) for criterion in item.get("criteria", []))


def normalize_text(text: str) -> str:
    table = str.maketrans({"臺": "台", "裡": "裏", "妳": "你"})
    return re.sub(r"\s+", "", str(text).translate(table)).lower()


def _contexts_text(chunks) -> str:
    return "\n".join(
        f"{chunk.get('parent_title', '')}\n{chunk.get('title', '')}\n{chunk.get('content', '')}"
        for chunk in chunks
    )


def _context_record(chunk) -> dict:
    return {
        "id": chunk.get("id", ""),
        "source": str(chunk.get("source", "")),
        "parent_title": chunk.get("parent_title", ""),
        "title": chunk.get("title", ""),
        "score": round(float(chunk.get("score", 0.0)), 6),
        "retrieval_method": chunk.get("retrieval_method", ""),
        "rerank_trace": chunk.get("rerank_trace", ""),
        "content_preview": re.sub(r"\s+", " ", str(chunk.get("content", ""))).strip()[:500],
    }


def _load_chunks():
    knowledge_base = active_knowledge_base(project_root=ROOT)
    index_path = knowledge_base.index_dir / "chunks.json"
    if index_path.exists():
        return load_index(index_path)
    return load_knowledge_base_chunks(knowledge_base.raw_dir)


def _load_embeddings():
    knowledge_base = active_knowledge_base(project_root=ROOT)
    embedding_path = knowledge_base.index_dir / "embeddings.npy"
    if not embedding_path.exists():
        return None
    return load_embedding_matrix(embedding_path)


def _load_vector_store(chunks, embeddings):
    if embeddings is None:
        return None
    knowledge_base = active_knowledge_base(project_root=ROOT)
    try:
        return load_or_build_qdrant_vector_store(
            index_dir=knowledge_base.index_dir,
            chunks=chunks,
            embeddings=embeddings,
        )
    except Exception:
        return None


def _load_completed(raw_path: Path):
    completed = set()
    if not raw_path.exists():
        return completed
    for line in raw_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        completed.add((record["variant"], record["id"]))
    return completed


def _load_rewrite_cache(raw_path: Path):
    cache = {}
    if not raw_path.exists():
        return cache
    for line in raw_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        question = str(record.get("question", "")).strip()
        rewritten = str(record.get("rewritten_query", "")).strip()
        if question and rewritten:
            cache[question] = rewritten
    return cache


def _read_records(raw_path: Path):
    if not raw_path.exists():
        return []
    records = []
    for line in raw_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def _summary(records):
    max_total = sum(int(record.get("max_score", 0)) for record in records)
    qa_total = sum(int(record.get("qa_score", 0)) for record in records)
    retrieval_total = sum(int(record.get("retrieval_upper_bound", 0)) for record in records)
    return {
        "qa_percent": _percent(qa_total, max_total),
        "retrieval_percent": _percent(retrieval_total, max_total),
    }


def _percent(total: int, maximum: int) -> float:
    return round(total / maximum * 100, 1) if maximum else 0.0


def _optional_int(value):
    if value is None or str(value).strip() == "":
        return None
    return int(value)


def _log(path: Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as log:
        log.write(f"{datetime.now().isoformat(timespec='seconds')} {message}\n")


if __name__ == "__main__":
    raise SystemExit(main())
