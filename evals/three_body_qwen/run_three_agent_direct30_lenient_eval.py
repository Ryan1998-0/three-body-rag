from datetime import datetime
from pathlib import Path
import json
import re
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag_demo.config import RagConfig
from rag_demo.query import answer_question


def main() -> int:
    eval_dir = Path(__file__).resolve().parent
    question_path = eval_dir / "questions_direct30_lenient_20260615.json"
    questions = json.loads(question_path.read_text(encoding="utf-8"))
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    raw_path = eval_dir / f"three_agent_direct30_lenient_raw_answers_{timestamp}.jsonl"
    report_path = eval_dir / f"three_agent_direct30_lenient_scored_report_{timestamp}.md"

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
                record["answer_output"] = answer_question(item["question"], model=model, top_k=top_k)
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
        "# Three-Agent Direct30 Lenient Scored Report",
        "",
        f"- Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Model: `{model}`",
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
        "- This is intentionally lenient and should be treated as a regression signal, not final human grading.",
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
