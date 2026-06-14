from datetime import datetime
from pathlib import Path
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag_demo.query import answer_question


def main() -> int:
    eval_dir = Path(__file__).resolve().parent
    questions = json.loads((eval_dir / "questions.json").read_text(encoding="utf-8"))
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    raw_path = eval_dir / f"qwen_rag_raw_answers_{timestamp}.jsonl"
    report_path = eval_dir / f"qwen_rag_raw_report_{timestamp}.md"

    model = "qwen2.5:7b"
    top_k = 5
    started = time.perf_counter()
    completed = 0

    with raw_path.open("w", encoding="utf-8") as raw_file, report_path.open("w", encoding="utf-8") as report:
        report.write(f"# Qwen RAG Raw Eval {timestamp}\n\n")
        report.write(f"- Model: `{model}`\n")
        report.write(f"- Top K: `{top_k}`\n")
        report.write("- Knowledge base: `data/raw/three-body-1.txt`\n\n")

        for item in questions:
            q_started = time.perf_counter()
            record = {
                "id": item["id"],
                "category": item["category"],
                "question": item["question"],
                "expected_points": item["expected_points"],
                "error": None,
                "answer_output": "",
                "elapsed_seconds": None,
            }
            try:
                record["answer_output"] = answer_question(item["question"], model=model, top_k=top_k)
                completed += 1
            except Exception as exc:
                record["error"] = f"{type(exc).__name__}: {exc}"
            record["elapsed_seconds"] = round(time.perf_counter() - q_started, 3)
            raw_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            raw_file.flush()

            report.write(f"## {item['id']} {item['category']}\n\n")
            report.write(f"Question: {item['question']}\n\n")
            report.write("Expected points:\n")
            for point in item["expected_points"]:
                report.write(f"- {point}\n")
            report.write("\n")
            report.write(f"Elapsed: `{record['elapsed_seconds']}s`\n\n")
            if record["error"]:
                report.write(f"Error: `{record['error']}`\n\n")
            else:
                report.write("Raw output:\n\n```text\n")
                report.write(record["answer_output"])
                report.write("\n```\n\n")
            report.flush()
            print(f"{item['id']} done in {record['elapsed_seconds']}s error={record['error'] is not None}")

    print(f"Completed {completed}/{len(questions)} questions")
    print(f"Raw JSONL: {raw_path}")
    print(f"Raw report: {report_path}")
    print(f"Total elapsed: {round(time.perf_counter() - started, 3)}s")
    return 0 if completed == len(questions) else 1


if __name__ == "__main__":
    raise SystemExit(main())
