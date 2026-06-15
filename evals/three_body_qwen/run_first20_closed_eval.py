from datetime import datetime
from pathlib import Path
import json
import os
import re
import sys
import time
from typing import Optional


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag_demo.config import RagConfig
from rag_demo.query import answer_question


DETAIL_INSTRUCTION = (
    "請用 4 到 6 句回答，回答要詳細一點；先直接回答標準答案，"
    "再補充來源中的關鍵依據。不要使用第一集以外的資訊。"
)


def main() -> int:
    eval_dir = Path(__file__).resolve().parent
    question_path = _resolve_questions_path(eval_dir)
    questions = json.loads(question_path.read_text(encoding="utf-8"))
    selected_ids = _optional_ids(os.getenv("RAG_EVAL_IDS"))
    if selected_ids:
        selected = set(selected_ids)
        questions = [item for item in questions if item["id"] in selected]
    limit = _optional_int(os.getenv("RAG_EVAL_LIMIT"))
    if limit is not None:
        questions = questions[:limit]

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    model = os.getenv("RAG_EVAL_MODEL", "qwen2.5:7b")
    top_k = int(os.getenv("RAG_EVAL_TOP_K", str(RagConfig.from_env().top_k)))
    raw_path = eval_dir / f"first20_closed_raw_answers_{timestamp}.jsonl"
    report_path = eval_dir / f"first20_closed_scored_report_{timestamp}.md"

    started = time.perf_counter()
    records = []
    with raw_path.open("w", encoding="utf-8") as raw_file:
        for item in questions:
            q_started = time.perf_counter()
            asked_question = build_eval_question(item["question"])
            record = {
                "id": item["id"],
                "category": item.get("category", ""),
                "question": item["question"],
                "asked_question": asked_question,
                "standard_answer": item["standard_answer"],
                "answer_output": "",
                "final_answer": "",
                "score": 0,
                "max_score": max_score(item),
                "matched": [],
                "missed": [],
                "penalties": [],
                "error": None,
                "elapsed_seconds": None,
            }
            try:
                record["answer_output"] = answer_question(asked_question, model=model, top_k=top_k)
                record["final_answer"] = extract_final_answer(record["answer_output"])
                record.update(score_answer(record["final_answer"], item))
            except Exception as exc:
                record["error"] = f"{type(exc).__name__}: {exc}"
                record["missed"] = [criterion["label"] for criterion in item["criteria"]]
            record["elapsed_seconds"] = round(time.perf_counter() - q_started, 3)
            records.append(record)
            raw_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            raw_file.flush()
            print(
                f"{record['id']} score={record['score']}/{record['max_score']} "
                f"elapsed={record['elapsed_seconds']}s error={record['error'] is not None}",
                flush=True,
            )

    write_report(report_path, raw_path, question_path, records, model, top_k, started)
    print(f"Raw JSONL: {raw_path}", flush=True)
    print(f"Scored report: {report_path}", flush=True)
    return 0 if all(record["error"] is None for record in records) else 1


def build_eval_question(question: str) -> str:
    return f"{question}\n{DETAIL_INSTRUCTION}"


def extract_final_answer(answer_output: str) -> str:
    marker = "Final Answer:"
    if marker in answer_output:
        return answer_output.split(marker, 1)[1].strip()
    return str(answer_output).strip()


def score_answer(final_answer: str, item: dict) -> dict:
    answer = normalize_text(final_answer)
    score = 0
    matched = []
    missed = []
    penalties = []

    for criterion in item.get("criteria", []):
        aliases = [normalize_text(alias) for alias in criterion.get("aliases", [])]
        if any(alias and alias in answer for alias in aliases):
            weight = int(criterion.get("weight", 1))
            score += weight
            matched.append(f"{criterion['label']} (+{weight})")
        else:
            missed.append(criterion["label"])

    for forbidden in item.get("forbidden", []):
        aliases = [normalize_text(alias) for alias in forbidden.get("aliases", [])]
        if any(_contains_unnegated_alias(answer, alias) for alias in aliases if alias):
            penalty = int(forbidden.get("penalty", 1))
            score -= penalty
            penalties.append(f"{forbidden['label']} (-{penalty})")

    return {
        "score": max(0, min(score, max_score(item))),
        "max_score": max_score(item),
        "matched": matched,
        "missed": missed,
        "penalties": penalties,
    }


def max_score(item: dict) -> int:
    return sum(int(criterion.get("weight", 1)) for criterion in item.get("criteria", []))


def normalize_text(text: str) -> str:
    table = str.maketrans({"臺": "台", "裡": "裏"})
    return re.sub(r"\s+", "", str(text).translate(table)).lower()


def _contains_unnegated_alias(answer: str, alias: str) -> bool:
    start = 0
    while True:
        index = answer.find(alias, start)
        if index < 0:
            return False
        prefix = answer[max(0, index - 8) : index]
        if not any(cue in prefix for cue in ("不是", "並非", "非", "而不是", "沒有", "不應是")):
            return True
        start = index + len(alias)


def write_report(report_path, raw_path, question_path, records, model, top_k, started) -> None:
    total_score = sum(record["score"] for record in records)
    total_max = sum(record["max_score"] for record in records)
    percent = round(total_score / total_max * 100, 1) if total_max else 0.0
    completed = sum(1 for record in records if record["error"] is None)
    elapsed = round(time.perf_counter() - started, 1)
    config = RagConfig.from_env()

    lines = [
        "# First20 Closed Three Body QA Agent Eval",
        "",
        f"- Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Model: `{model}`",
        f"- Top K: `{top_k}`",
        f"- Chunk size / stride: `{config.chunk_size}/{config.chunk_stride}`",
        f"- Questions: `{question_path.relative_to(ROOT)}`",
        f"- Raw answers: `{raw_path.relative_to(ROOT)}`",
        f"- Detail instruction: `{DETAIL_INSTRUCTION}`",
        "",
        "## Scoring Mechanism",
        "",
        "- 20 closed-answer questions limited to the first volume of Three Body.",
        "- Each question has a standard answer and weighted criteria totaling 5 points.",
        "- A criterion gets full credit when the Final Answer contains one configured alias.",
        "- Forbidden aliases subtract points for common wrong answers, with a floor of 0.",
        "- This is deterministic keyword scoring for regression tracking; human review is still useful for borderline phrasing.",
        "",
        "## Run Result",
        "",
        f"- Completed: `{completed}/{len(records)}`",
        f"- Runtime errors: `{len(records) - completed}`",
        f"- Total elapsed: about `{elapsed}s`",
        f"- Total score: `{total_score} / {total_max} = {percent} / 100`",
        "",
        "## Score Table",
        "",
        "| ID | Category | Score | Missed Criteria | Penalties |",
        "| --- | --- | ---: | --- | --- |",
    ]

    for record in records:
        missed = "; ".join(record["missed"]) if record["missed"] else "None"
        penalties = "; ".join(record["penalties"]) if record["penalties"] else "None"
        lines.append(
            f"| {record['id']} | {record['category']} | "
            f"{record['score']}/{record['max_score']} | {missed} | {penalties} |"
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
        lines.append("Penalties:")
        lines.extend(f"- {item}" for item in record["penalties"]) if record["penalties"] else lines.append("- None")
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


def _resolve_questions_path(eval_dir: Path) -> Path:
    configured = os.getenv("RAG_EVAL_QUESTIONS_FILE")
    if not configured or not configured.strip():
        return eval_dir / "questions_first20_closed_20260615.json"
    path = Path(configured)
    if not path.is_absolute():
        path = ROOT / path
    return path


def _optional_int(value: Optional[str]):
    if value is None or not value.strip():
        return None
    return int(value)


def _optional_ids(value: Optional[str]):
    if value is None or not value.strip():
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
