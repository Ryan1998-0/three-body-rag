from datetime import datetime
from pathlib import Path
import json
import re


EVAL_DIR = Path(__file__).resolve().parent
QUESTION_PATH = EVAL_DIR / "questions_direct30_lenient_20260615.json"
RUNS = [
    {
        "mode": "原本 keyword query + embedding retrieval",
        "raw_path": EVAL_DIR / "three_agent_direct30_lenient_raw_answers_20260615-005520.jsonl",
        "previous_score": "104 / 150 = 69.3",
    },
    {
        "mode": "純 keyword retrieval",
        "raw_path": EVAL_DIR / "three_agent_direct30_keyword_only_raw_answers_20260615-010646.jsonl",
        "previous_score": "116 / 150 = 77.3",
    },
    {
        "mode": "hybrid rerank 實驗版",
        "raw_path": EVAL_DIR / "three_agent_direct30_hybrid_rerank_raw_answers_20260615-011430.jsonl",
        "previous_score": "124 / 150 = 82.7",
    },
    {
        "mode": "已切換後的主流程重跑",
        "raw_path": EVAL_DIR / "three_agent_direct30_lenient_raw_answers_20260615-012237.jsonl",
        "previous_score": "128 / 150 = 85.3",
    },
]


def main() -> int:
    questions = json.loads(QUESTION_PATH.read_text(encoding="utf-8"))
    criteria_by_id = {item["id"]: item["criteria"] for item in questions}
    question_by_id = {item["id"]: item["question"] for item in questions}

    summaries = []
    details_by_mode = {}
    for run in RUNS:
        records = load_records(run["raw_path"])
        rescored = [rescore_record(record, criteria_by_id[record["id"]]) for record in records]
        total = sum(item["score"] for item in rescored)
        max_score = sum(item["max_score"] for item in rescored)
        percent = round(total / max_score * 100, 1) if max_score else 0.0
        summaries.append(
            {
                **run,
                "total": total,
                "max_score": max_score,
                "percent": percent,
            }
        )
        details_by_mode[run["mode"]] = rescored

    report_path = EVAL_DIR / f"direct30_initial_standard_rescore_{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    write_report(report_path, summaries, details_by_mode, question_by_id)
    print(report_path)
    for summary in summaries:
        print(
            f"{summary['mode']}: "
            f"{summary['total']} / {summary['max_score']} = {summary['percent']} / 100"
        )
    return 0


def load_records(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def rescore_record(record, criteria):
    answer = normalize_text(record.get("final_answer", ""))
    matched = []
    missed = []
    for criterion in criteria:
        aliases = [normalize_text(alias) for alias in criterion.get("aliases", [])]
        hit_count = sum(1 for alias in aliases if alias and alias in answer)
        required_hits = 2 if len(aliases) >= 4 else 1
        if hit_count >= required_hits:
            matched.append(criterion["label"])
        else:
            missed.append(criterion["label"])
    return {
        "id": record["id"],
        "question": record["question"],
        "score": len(matched),
        "max_score": len(criteria),
        "matched": matched,
        "missed": missed,
        "final_answer": record.get("final_answer", ""),
    }


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", str(text)).lower()


def write_report(report_path: Path, summaries, details_by_mode, question_by_id) -> None:
    lines = [
        "# Direct30 Initial-Standard Rescore",
        "",
        f"- Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Questions: `{QUESTION_PATH.as_posix()}`",
        "",
        "## Scoring Mechanism",
        "",
        "This report re-scores the same direct30 raw answers using the earlier user10 scoring rule.",
        "",
        "- Each criterion is worth 1 point.",
        "- Criteria weights from the lenient direct30 setup are ignored.",
        "- If a criterion has 4 or more aliases, at least 2 aliases must appear in the Final Answer.",
        "- If a criterion has fewer than 4 aliases, at least 1 alias must appear.",
        "- Direct30 has 30 questions x 3 criteria, so max score is 90.",
        "- No model calls are re-run; this only re-scores existing raw answers.",
        "",
        "## Summary",
        "",
        "| Mode | Previous Lenient Score | Initial-Standard Rescore | Delta vs Previous % |",
        "| --- | ---: | ---: | ---: |",
    ]

    for summary in summaries:
        previous_percent = float(summary["previous_score"].split("=")[1].strip())
        delta = summary["percent"] - previous_percent
        lines.append(
            f"| {summary['mode']} | `{summary['previous_score']}` | "
            f"`{summary['total']} / {summary['max_score']} = {summary['percent']} / 100` | "
            f"`{delta:+.1f}` |"
        )

    lines.extend(["", "## Per-Question Scores", ""])
    for summary in summaries:
        mode = summary["mode"]
        lines.extend(
            [
                f"### {mode}",
                "",
                "| ID | Score | Missed Criteria |",
                "| --- | ---: | --- |",
            ]
        )
        for item in details_by_mode[mode]:
            missed = "; ".join(item["missed"]) if item["missed"] else "None"
            lines.append(f"| {item['id']} | {item['score']}/{item['max_score']} | {missed} |")
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
