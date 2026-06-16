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
from rag_demo.model_providers import ask_model
from rag_demo.query import _rrf_parent_context_results
from rag_demo.query_rewriter import rewrite_query_for_retrieval


QUESTION_FILE = "questions_current25_v2_20260616.json"
DETAIL_INSTRUCTION = "請根據第一集來源回答，使用繁體中文，先直接回答，再用 2 到 4 句補充關鍵依據。"


def main() -> int:
    eval_dir = Path(__file__).resolve().parent
    question_path = eval_dir / QUESTION_FILE
    questions = json.loads(question_path.read_text(encoding="utf-8"))
    selected_ids = _optional_ids(os.getenv("RAG_EVAL_IDS"))
    if selected_ids:
        selected = set(selected_ids)
        questions = [item for item in questions if item["id"] in selected]
    limit = _optional_int(os.getenv("RAG_EVAL_LIMIT"))
    if limit is not None:
        questions = questions[:limit]

    config = RagConfig.from_env()
    model = os.getenv("RAG_EVAL_MODEL", "qwen2.5:7b")
    candidate_k = int(os.getenv("RAG_RETRIEVAL_CANDIDATE_K", str(config.retrieval_candidate_k)))
    rerank_top_k = int(os.getenv("RAG_RETRIEVAL_RERANK_TOP_K", "12"))
    final_context_k = int(os.getenv("RAG_FINAL_CONTEXT_K", "8"))
    rewrite_enabled = _bool_env("RAG_QUERY_REWRITE_ENABLED", True)
    max_context_chars = int(os.getenv("RAG_EVAL_MAX_CONTEXT_CHARS", "520"))

    chunks = _load_chunks()
    embeddings = _load_embeddings()
    section_titles = _section_titles(chunks)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    raw_path = eval_dir / f"current25_v2_raw_answers_{timestamp}.jsonl"
    report_path = eval_dir / f"current25_v2_scored_report_{timestamp}.md"

    started = time.perf_counter()
    records = []
    with raw_path.open("w", encoding="utf-8") as raw_file:
        for item in questions:
            q_started = time.perf_counter()
            record = run_question(
                item=item,
                chunks=chunks,
                embeddings=embeddings,
                section_titles=section_titles,
                model=model,
                candidate_k=candidate_k,
                rerank_top_k=rerank_top_k,
                final_context_k=final_context_k,
                rewrite_enabled=rewrite_enabled,
                max_context_chars=max_context_chars,
            )
            record["elapsed_seconds"] = round(time.perf_counter() - q_started, 3)
            records.append(record)
            raw_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            raw_file.flush()
            print(
                f"{record['id']} lenient={record['lenient_score']}/{record['max_score']} "
                f"strict={record['strict_score']}/{record['max_score']} "
                f"retrieval={record['retrieval_upper_bound']}/{record['max_score']} "
                f"elapsed={record['elapsed_seconds']}s error={record['error'] is not None}",
                flush=True,
            )

    write_report(
        report_path=report_path,
        raw_path=raw_path,
        question_path=question_path,
        records=records,
        model=model,
        started=started,
        rewrite_enabled=rewrite_enabled,
        max_context_chars=max_context_chars,
    )
    print(f"Raw JSONL: {raw_path}", flush=True)
    print(f"Scored report: {report_path}", flush=True)
    return 0 if all(record["error"] is None for record in records) else 1


def run_question(
    item,
    chunks,
    embeddings,
    section_titles,
    model: str,
    candidate_k: int,
    rerank_top_k: int,
    final_context_k: int,
    rewrite_enabled: bool,
    max_context_chars: int,
) -> dict:
    question = item["question"]
    record = {
        "id": item["id"],
        "category": item["category"],
        "question": question,
        "asked_question": f"{question}\n{DETAIL_INSTRUCTION}",
        "standard_answer": item["standard_answer"],
        "rewritten_query": question,
        "rewrite_error": None,
        "final_answer": "",
        "answer_output": "",
        "lenient_score": 0,
        "strict_score": 0,
        "retrieval_upper_bound": 0,
        "max_score": max_score(item),
        "lenient_matched": [],
        "lenient_missed": [],
        "strict_matched": [],
        "strict_missed": [],
        "retrieval_matched": [],
        "retrieval_missed": [],
        "contexts": [],
        "error": None,
        "elapsed_seconds": None,
    }
    try:
        if rewrite_enabled:
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
            top_k=rerank_top_k,
            candidate_k=candidate_k,
            final_context_k=final_context_k,
        )
        record["contexts"] = [_context_record(chunk) for chunk in results]
        retrieval_score = score_context(results, item["lenient_criteria"])
        record["retrieval_upper_bound"] = retrieval_score["score"]
        record["retrieval_matched"] = retrieval_score["matched"]
        record["retrieval_missed"] = retrieval_score["missed"]

        answer = ask_model(
            build_concise_answer_prompt(record, results, max_context_chars=max_context_chars),
            model=model,
            system="你是 QA Agent。只能根據提供的 Context 回答，不可使用來源外資訊。請使用繁體中文。",
        )
        record["final_answer"] = answer.strip()
        record["answer_output"] = format_answer_output(record, results)
        lenient_score = score_text(record["final_answer"], item["lenient_criteria"])
        strict_score = score_text(record["final_answer"], item["strict_criteria"])
        record["lenient_score"] = lenient_score["score"]
        record["lenient_matched"] = lenient_score["matched"]
        record["lenient_missed"] = lenient_score["missed"]
        record["strict_score"] = strict_score["score"]
        record["strict_matched"] = strict_score["matched"]
        record["strict_missed"] = strict_score["missed"]
    except Exception as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
        record["lenient_missed"] = [criterion["label"] for criterion in item["lenient_criteria"]]
        record["strict_missed"] = [criterion["label"] for criterion in item["strict_criteria"]]
    return record


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
    return {"score": score, "matched": matched, "missed": missed}


def score_context(chunks, criteria) -> dict:
    context_text = "\n".join(
        f"{chunk.get('parent_title', '')}\n{chunk.get('title', '')}\n{chunk.get('content', '')}"
        for chunk in chunks
    )
    return score_text(context_text, criteria)


def write_report(report_path, raw_path, question_path, records, model: str, started: float, rewrite_enabled: bool, max_context_chars: int) -> None:
    total_max = sum(record["max_score"] for record in records)
    lenient_total = sum(record["lenient_score"] for record in records)
    strict_total = sum(record["strict_score"] for record in records)
    retrieval_total = sum(record["retrieval_upper_bound"] for record in records)
    elapsed = round(time.perf_counter() - started, 3)
    by_category = {}
    for record in records:
        by_category.setdefault(record["category"], []).append(record)

    lines = [
        "# Current25 V2 QA and Retrieval Eval",
        "",
        f"- Time: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`",
        f"- Model: `{model}`",
        f"- Questions: `{question_path.relative_to(ROOT)}`",
        f"- Raw answers: `{raw_path.relative_to(ROOT)}`",
        f"- Query rewrite enabled: `{rewrite_enabled}`",
        f"- LLM answer prompt: `concise top-8 context, max {max_context_chars} chars per context`",
        f"- Total elapsed seconds: `{elapsed}`",
        "",
        "## Scoring Standards",
        "",
        "- QA 語意評分（寬鬆）：意思對就給分，同義詞、簡稱、等價表達可命中。",
        "- QA 語意評分（嚴謹）：要求回答保留更精準的關鍵詞、因果、限制條件或來源中的核心表述。",
        "- Retrieval Upper Bound：不看 LLM 回答，只看 Top 8 Context 是否包含寬鬆標準所需 evidence。",
        "",
        "## Summary",
        "",
        "| Metric | Score |",
        "| --- | ---: |",
        f"| QA 語意評分（寬鬆） | `{lenient_total} / {total_max} = {_pct(lenient_total, total_max)}` |",
        f"| QA 語意評分（嚴謹） | `{strict_total} / {total_max} = {_pct(strict_total, total_max)}` |",
        f"| Retrieval Upper Bound | `{retrieval_total} / {total_max} = {_pct(retrieval_total, total_max)}` |",
        "",
        "## Category Summary",
        "",
        "| Category | Count | Lenient | Strict | Retrieval Upper Bound |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for category, items in by_category.items():
        cat_max = sum(record["max_score"] for record in items)
        cat_lenient = sum(record["lenient_score"] for record in items)
        cat_strict = sum(record["strict_score"] for record in items)
        cat_retrieval = sum(record["retrieval_upper_bound"] for record in items)
        lines.append(
            f"| {category} | {len(items)} | `{cat_lenient}/{cat_max}` | `{cat_strict}/{cat_max}` | `{cat_retrieval}/{cat_max}` |"
        )

    lines.extend(
        [
            "",
            "## Question Table",
            "",
            "| ID | Category | Lenient | Strict | Retrieval UB | Question |",
            "| --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for record in records:
        lines.append(
            f"| {record['id']} | {record['category']} | "
            f"`{record['lenient_score']}/{record['max_score']}` | "
            f"`{record['strict_score']}/{record['max_score']}` | "
            f"`{record['retrieval_upper_bound']}/{record['max_score']}` | "
            f"{record['question']} |"
        )

    for record in records:
        lines.extend(
            [
                "",
                f"## {record['id']} {record['category']}",
                "",
                f"Question: {record['question']}",
                "",
                f"Standard answer: {record['standard_answer']}",
                "",
                f"Rewritten query: `{record['rewritten_query']}`",
                "",
                f"Scores: lenient `{record['lenient_score']}/{record['max_score']}`, "
                f"strict `{record['strict_score']}/{record['max_score']}`, "
                f"retrieval upper bound `{record['retrieval_upper_bound']}/{record['max_score']}`",
                "",
                "Final Answer:",
                "",
                "```text",
                record["final_answer"] or "",
                "```",
                "",
                "Missed Criteria:",
                "",
                f"- Lenient: {'; '.join(record['lenient_missed']) or 'None'}",
                f"- Strict: {'; '.join(record['strict_missed']) or 'None'}",
                f"- Retrieval: {'; '.join(record['retrieval_missed']) or 'None'}",
                "",
                "Top Contexts:",
            ]
        )
        for index, context in enumerate(record["contexts"][:8], start=1):
            lines.append(
                f"{index}. `{Path(context['source']).name}` / {context['title']} / {context['retrieval_method']}"
            )
        if record["error"]:
            lines.append("")
            lines.append(f"Error: `{record['error']}`")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_concise_answer_prompt(record, results, max_context_chars: int) -> str:
    context_lines = []
    for index, chunk in enumerate(results[:8], start=1):
        content = re.sub(r"\s+", " ", str(chunk.get("content", ""))).strip()
        if len(content) > max_context_chars:
            content = content[:max_context_chars].rstrip() + "..."
        context_lines.append(
            f"[來源 {index}] {Path(str(chunk.get('source', ''))).name} / {chunk.get('title', '')}\n{content}"
        )
    contexts = "\n\n".join(context_lines) or "沒有找到來源。"
    return f"""請根據 Context 回答問題。

## 問題
{record['question']}

## 回答要求
{DETAIL_INSTRUCTION}

## Context
{contexts}

## 標準
- 只能使用 Context 中的資訊。
- 如果 Context 不足，請明確說無法從來源確認。
- 請保留問題需要的專名、數字、派別、事件名稱與因果關係。
"""


def format_answer_output(record, results) -> str:
    contexts = "\n".join(
        f"{index}. {Path(context.get('source', '')).name} / {context.get('title', '')} / {context.get('retrieval_method', '')}"
        for index, context in enumerate(results, start=1)
    )
    return f"""Question:
{record['question']}

Asked Question:
{record['asked_question']}

Rewritten Query:
{record['rewritten_query']}

Retrieved Contexts:
{contexts}

Final Answer:
{record['final_answer']}
"""


def max_score(item: dict) -> int:
    return sum(int(criterion.get("weight", 1)) for criterion in item["lenient_criteria"])


def normalize_text(text: str) -> str:
    table = str.maketrans({"臺": "台", "裡": "裏", "妳": "你"})
    return re.sub(r"\s+", "", str(text).translate(table)).lower()


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
        "retrieval_method": chunk.get("retrieval_method", ""),
        "score": chunk.get("score", 0),
        "content": chunk.get("content", ""),
    }


def _optional_ids(raw_value: str):
    if not raw_value:
        return []
    return [value.strip() for value in raw_value.split(",") if value.strip()]


def _optional_int(raw_value: str):
    if raw_value is None or str(raw_value).strip() == "":
        return None
    return int(raw_value)


def _bool_env(key: str, default: bool) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _pct(value: int, total: int) -> str:
    if not total:
        return "n/a"
    return f"{value / total * 100:.1f}%"


if __name__ == "__main__":
    raise SystemExit(main())
