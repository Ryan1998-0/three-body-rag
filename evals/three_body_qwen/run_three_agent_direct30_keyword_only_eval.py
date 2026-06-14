from datetime import datetime
from pathlib import Path
import json
import re
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag_demo.chunking import load_knowledge_base_chunks
from rag_demo.config import RagConfig, resolve_project_path
from rag_demo.index_store import load_index
from rag_demo.keyword_extraction import extract_keywords
from rag_demo.qa_agent import answer_with_qa_agent
from rag_demo.question_extraction import extract_real_question
from rag_demo.retrieval import keyword_search


PROJECT_ROOT = ROOT


def main() -> int:
    eval_dir = Path(__file__).resolve().parent
    question_path = eval_dir / "questions_direct30_lenient_20260615.json"
    questions = json.loads(question_path.read_text(encoding="utf-8"))
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    raw_path = eval_dir / f"three_agent_direct30_keyword_only_raw_answers_{timestamp}.jsonl"
    report_path = eval_dir / f"three_agent_direct30_keyword_only_scored_report_{timestamp}.md"

    model = "qwen2.5:7b"
    top_k = RagConfig.from_env().top_k
    started = time.perf_counter()
    records = []

    with raw_path.open("w", encoding="utf-8") as raw_file:
        for item in questions:
            q_started = time.perf_counter()
            record = {
                "id": item["id"],
                "question": item["question"],
                "answer_output": "",
                "final_answer": "",
                "score": 0,
                "max_score": sum(int(criterion.get("weight", 1)) for criterion in item["criteria"]),
                "matched": [],
                "missed": [],
                "error": None,
                "elapsed_seconds": None,
            }
            try:
                record["answer_output"] = answer_question_keyword_only(
                    item["question"],
                    model=model,
                    top_k=top_k,
                )
                record["final_answer"] = extract_final_answer(record["answer_output"])
                score_record(record, item["criteria"])
            except Exception as exc:
                record["error"] = f"{type(exc).__name__}: {exc}"
                record["missed"] = [criterion["label"] for criterion in item["criteria"]]
            record["elapsed_seconds"] = round(time.perf_counter() - q_started, 3)
            records.append(record)
            raw_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            raw_file.flush()
            print(
                f"{record['id']} score={record['score']}/{record['max_score']} "
                f"elapsed={record['elapsed_seconds']}s error={record['error'] is not None}"
            )

    write_report(report_path, raw_path, question_path, records, model, top_k, started)
    print(f"Raw JSONL: {raw_path}")
    print(f"Scored report: {report_path}")
    return 0 if all(record["error"] is None for record in records) else 1


def answer_question_keyword_only(question: str, model: str, top_k: int = 5) -> str:
    total_started_at = time.perf_counter()
    timing = {}
    config = RagConfig.from_env()
    top_k = top_k or config.top_k

    kb_dir = resolve_project_path("RAG_KB_DIR", "data/raw", project_root=PROJECT_ROOT)
    index_dir = resolve_project_path("RAG_INDEX_DIR", "data/index", project_root=PROJECT_ROOT)
    index_path = index_dir / "chunks.json"

    started_at = time.perf_counter()
    if index_path.exists():
        chunks = load_index(index_path)
    else:
        chunks = load_knowledge_base_chunks(kb_dir)
    timing["load_index"] = time.perf_counter() - started_at

    started_at = time.perf_counter()
    keywords = extract_keywords(question, model=model)
    timing["keyword_extraction_agent"] = time.perf_counter() - started_at

    started_at = time.perf_counter()
    refined_question = extract_real_question(question, model=model)
    timing["question_extraction_agent"] = time.perf_counter() - started_at

    retrieval_query = " ".join(keywords) if keywords else question
    started_at = time.perf_counter()
    results = keyword_search(retrieval_query, chunks, top_k=top_k)
    timing["keyword_retrieval"] = time.perf_counter() - started_at

    started_at = time.perf_counter()
    answer = answer_with_qa_agent(
        original_question=question,
        refined_question=refined_question,
        keywords=keywords,
        chunks=results,
        model=model,
    )
    timing["qa_agent"] = time.perf_counter() - started_at
    timing["total"] = time.perf_counter() - total_started_at

    return format_output(
        question=question,
        retrieval_query=retrieval_query,
        keywords=keywords,
        refined_question=refined_question,
        results=results,
        answer=answer,
        timing=timing,
    )


def format_output(question, retrieval_query, keywords, refined_question, results, answer, timing) -> str:
    source_lines = []
    for index, chunk in enumerate(results, start=1):
        source_lines.append(
            f"{index}. {Path(str(chunk['source'])).name} / {chunk['title']} / score={chunk.get('score', 0)}"
        )

    sources = "\n".join(source_lines) if source_lines else "No sources found"
    keyword_text = ", ".join(str(keyword) for keyword in keywords) if keywords else "None"
    timing_text = format_timing(timing)

    return f"""Question:
{question}

Keyword Extraction Agent:
{keyword_text}

Question Extraction Agent:
{refined_question}

Keyword retrieval query:
{retrieval_query}

Retrieved sources Top {len(results)}:
{sources}
{timing_text}

Final Answer:
{answer}
"""


def format_timing(timing) -> str:
    if not timing:
        return ""
    lines = ["Timing:"]
    for key, value in timing.items():
        lines.append(f"- {key}: {float(value):.2f}s")
    return "\n".join(lines)


def extract_final_answer(answer_output: str) -> str:
    marker = "Final Answer:"
    if marker in answer_output:
        return answer_output.split(marker, 1)[1].strip()
    return str(answer_output).strip()


def score_record(record, criteria) -> None:
    answer = normalize_text(record["final_answer"])
    score = 0
    matched = []
    missed = []

    for criterion in criteria:
        aliases = [normalize_text(alias) for alias in criterion.get("aliases", [])]
        if any(alias and alias in answer for alias in aliases):
            weight = int(criterion.get("weight", 1))
            score += weight
            matched.append(f"{criterion['label']} (+{weight})")
        else:
            missed.append(criterion["label"])

    record["score"] = min(score, record["max_score"])
    record["matched"] = matched
    record["missed"] = missed


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", str(text)).lower()


def write_report(report_path, raw_path, question_path, records, model, top_k, started) -> None:
    total_score = sum(record["score"] for record in records)
    max_score = sum(record["max_score"] for record in records)
    percent = round(total_score / max_score * 100, 1) if max_score else 0.0
    completed = sum(1 for record in records if record["error"] is None)
    elapsed = round(time.perf_counter() - started, 1)
    config = RagConfig.from_env()

    lines = [
        "# Three-Agent Direct30 Keyword-Only Scored Report",
        "",
        f"- Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Model: `{model}`",
        "- Retrieval mode: `keyword_search` only",
        f"- Top K: `{top_k}`",
        f"- Chunk size / stride: `{config.chunk_size}/{config.chunk_stride}`",
        f"- Questions: `{question_path.as_posix()}`",
        f"- Raw answers: `{raw_path.as_posix()}`",
        "",
        "## Scoring Mechanism",
        "",
        "- 30 narrower questions designed for direct retrieval checks.",
        "- Each question has 3 weighted criteria adding up to 5 points.",
        "- A criterion gets full weighted credit if the Final Answer contains any configured alias.",
        "- This run forces retrieval to `keyword_search` and does not use embeddings.",
        "",
        "## Run Result",
        "",
        f"- Completed: `{completed}/{len(records)}`",
        f"- Runtime errors: `{len(records) - completed}`",
        f"- Total elapsed: about `{elapsed}s`",
        f"- Total score: `{total_score} / {max_score} = {percent} / 100`",
        "",
        "## Score Table",
        "",
        "| ID | Score | Missed Criteria |",
        "| --- | ---: | --- |",
    ]

    for record in records:
        missed = "; ".join(record["missed"]) if record["missed"] else "None"
        lines.append(f"| {record['id']} | {record['score']}/{record['max_score']} | {missed} |")

    for record in records:
        lines.extend(
            [
                "",
                f"## {record['id']}",
                "",
                f"Question: {record['question']}",
                "",
                f"Elapsed: `{record['elapsed_seconds']}s`",
                "",
                f"Score: `{record['score']} / {record['max_score']}`",
                "",
                "Matched criteria:",
            ]
        )
        lines.extend(f"- {item}" for item in record["matched"]) if record["matched"] else lines.append("- None")
        lines.append("")
        lines.append("Missed criteria:")
        lines.extend(f"- {item}" for item in record["missed"]) if record["missed"] else lines.append("- None")
        lines.append("")
        if record["error"]:
            lines.append(f"Error: `{record['error']}`")
        else:
            lines.extend(
                [
                    "Final Answer:",
                    "",
                    "```text",
                    record["final_answer"],
                    "```",
                    "",
                    "Full RAG Output:",
                    "",
                    "```text",
                    record["answer_output"],
                    "```",
                ]
            )

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
