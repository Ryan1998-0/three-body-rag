from datetime import datetime
from pathlib import Path
import json
import os
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag_demo.query import answer_question


def main() -> int:
    eval_dir = Path(__file__).resolve().parent
    record_dir = ROOT / "test-records"
    record_dir.mkdir(exist_ok=True)

    questions_path = _resolve_questions_path(eval_dir)
    questions = json.loads(questions_path.read_text(encoding="utf-8"))
    selected_ids = _optional_ids(os.getenv("RAG_EVAL_IDS"))
    if selected_ids:
        selected = set(selected_ids)
        questions = [item for item in questions if item["id"] in selected]
    limit = _optional_int(os.getenv("RAG_EVAL_LIMIT"))
    if limit is not None:
        questions = questions[:limit]

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    model = os.getenv("RAG_EVAL_MODEL", "qwen2.5:7b")
    top_k = int(os.getenv("RAG_EVAL_TOP_K", "5"))

    raw_path = eval_dir / f"three_body_35_raw_answers_{timestamp}.jsonl"
    report_path = eval_dir / f"three_body_35_raw_report_{timestamp}.md"
    record_path = record_dir / f"qwen-rag-three-body-35q-{timestamp}.md"

    started = time.perf_counter()
    completed = 0
    errors = 0

    with raw_path.open("w", encoding="utf-8") as raw_file, report_path.open("w", encoding="utf-8") as report:
        report.write(f"# Three Body 35-Question RAG Eval {timestamp}\n\n")
        report.write(f"- Model: `{model}`\n")
        report.write(f"- Top K: `{top_k}`\n")
        report.write(f"- Question file: `{questions_path.relative_to(ROOT)}`\n")
        if selected_ids:
            report.write(f"- Selected IDs: `{', '.join(selected_ids)}`\n")
        report.write("- Knowledge base: `data/raw/three-body-1.txt`\n")
        report.write("- Scoring: raw answer run only; manual scoring not applied in this batch.\n\n")

        for item in questions:
            q_started = time.perf_counter()
            record = {
                "id": item["id"],
                "category": item["category"],
                "question": item["question"],
                "error": None,
                "answer_output": "",
                "elapsed_seconds": None,
            }

            try:
                record["answer_output"] = answer_question(item["question"], model=model, top_k=top_k)
                completed += 1
            except Exception as exc:
                record["error"] = f"{type(exc).__name__}: {exc}"
                errors += 1

            record["elapsed_seconds"] = round(time.perf_counter() - q_started, 3)
            raw_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            raw_file.flush()

            report.write(f"## {item['id']} {item['category']}\n\n")
            report.write(f"Question: {item['question']}\n\n")
            report.write(f"Elapsed: `{record['elapsed_seconds']}s`\n\n")
            if record["error"]:
                report.write(f"Error: `{record['error']}`\n\n")
            else:
                report.write("Raw output:\n\n```text\n")
                report.write(record["answer_output"])
                report.write("\n```\n\n")
            report.flush()

            print(f"{item['id']} done in {record['elapsed_seconds']}s error={record['error'] is not None}", flush=True)

    total_elapsed = round(time.perf_counter() - started, 3)
    record_lines = [
        f"# Qwen RAG Three Body 35Q Test Record {timestamp}",
        "",
        f"- Command: `{Path(sys.executable).name} -X utf8 evals/three_body_qwen/run_eval_35.py`",
        f"- Model: `{model}`",
        f"- Top K: `{top_k}`",
        f"- Question file: `{questions_path.relative_to(ROOT)}`",
        f"- Selected IDs: `{', '.join(selected_ids) if selected_ids else 'all'}`",
        f"- Raw JSONL: `{raw_path.relative_to(ROOT)}`",
        f"- Raw report: `{report_path.relative_to(ROOT)}`",
        f"- Completed: `{completed}/{len(questions)}`",
        f"- Errors: `{errors}`",
        f"- Total elapsed: `{total_elapsed}s`",
        "",
        "## Notes",
        "",
        "- This run records raw RAG/Qwen outputs for review.",
        "- Manual answer scoring is intentionally not included in this runner.",
        "",
    ]
    record_path.write_text("\n".join(record_lines), encoding="utf-8")

    print(f"Completed {completed}/{len(questions)} questions", flush=True)
    print(f"Errors: {errors}", flush=True)
    print(f"Raw JSONL: {raw_path}", flush=True)
    print(f"Raw report: {report_path}", flush=True)
    print(f"Test record: {record_path}", flush=True)
    print(f"Total elapsed: {total_elapsed}s", flush=True)
    return 0 if errors == 0 else 1


def _optional_int(value: str | None):
    if value is None or not value.strip():
        return None
    return int(value)


def _resolve_questions_path(eval_dir: Path) -> Path:
    configured = os.getenv("RAG_EVAL_QUESTIONS_FILE")
    if not configured or not configured.strip():
        return eval_dir / "questions_35_20260613.json"
    path = Path(configured)
    if not path.is_absolute():
        path = ROOT / path
    return path


def _optional_ids(value: str | None):
    if value is None or not value.strip():
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
