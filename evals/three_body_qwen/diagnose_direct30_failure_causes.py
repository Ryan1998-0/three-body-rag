from datetime import datetime
from pathlib import Path
import json
import re


EVAL_DIR = Path(__file__).resolve().parent
ROOT = EVAL_DIR.parents[1]
QUESTION_PATH = EVAL_DIR / "questions_direct30_lenient_20260615.json"
CHUNK_PATH = ROOT / "data/index/chunks.json"
RUNS = [
    {
        "mode": "原本 keyword query + embedding retrieval",
        "raw_path": EVAL_DIR / "three_agent_direct30_lenient_raw_answers_20260615-005520.jsonl",
        "initial_score": "46 / 90 = 51.1",
    },
    {
        "mode": "純 keyword retrieval",
        "raw_path": EVAL_DIR / "three_agent_direct30_keyword_only_raw_answers_20260615-010646.jsonl",
        "initial_score": "52 / 90 = 57.8",
    },
    {
        "mode": "hybrid rerank 實驗版",
        "raw_path": EVAL_DIR / "three_agent_direct30_hybrid_rerank_raw_answers_20260615-011430.jsonl",
        "initial_score": "60 / 90 = 66.7",
    },
    {
        "mode": "已切換後的主流程重跑",
        "raw_path": EVAL_DIR / "three_agent_direct30_lenient_raw_answers_20260615-012237.jsonl",
        "initial_score": "56 / 90 = 62.2",
    },
]


def main() -> int:
    questions = json.loads(QUESTION_PATH.read_text(encoding="utf-8"))
    chunks = json.loads(CHUNK_PATH.read_text(encoding="utf-8"))
    chunks_by_title = {chunk["title"]: chunk for chunk in chunks}
    full_kb_text = "\n".join(chunk_text(chunk) for chunk in chunks)
    question_by_id = {item["id"]: item for item in questions}

    summaries = []
    details = {}
    for run in RUNS:
        records = load_records(run["raw_path"])
        diagnosis = [
            diagnose_record(record, question_by_id[record["id"]], chunks_by_title, full_kb_text)
            for record in records
        ]
        summary = summarize_run(run, diagnosis)
        summaries.append(summary)
        details[run["mode"]] = diagnosis

    report_path = EVAL_DIR / f"direct30_failure_cause_diagnosis_{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    write_report(report_path, summaries, details)
    print(report_path)
    for summary in summaries:
        print(
            summary["mode"],
            "answer", f"{summary['answer_score']}/90",
            "retrieval_ceiling", f"{summary['retrieval_ceiling']}/90",
            "qa_underused", summary["qa_underused_evidence"],
            "retrieval_miss", summary["retrieval_miss"],
            "rubric_or_alias_gap", summary["rubric_or_alias_gap"],
        )
    return 0


def load_records(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def diagnose_record(record, question, chunks_by_title, full_kb_text: str):
    titles = parse_retrieved_titles(record.get("answer_output", ""))
    retrieved_chunks = [chunks_by_title[title] for title in titles if title in chunks_by_title]
    retrieved_text = "\n".join(chunk_text(chunk) for chunk in retrieved_chunks)
    answer_text = record.get("final_answer", "")

    criteria_details = []
    for criterion in question["criteria"]:
        answer_hit, answer_hits, required_hits = criterion_match(answer_text, criterion)
        retrieval_hit, retrieval_hits, _ = criterion_match(retrieved_text, criterion)
        kb_hit, kb_hits, _ = criterion_match(full_kb_text, criterion)

        if answer_hit and retrieval_hit:
            cause = "answered_with_retrieved_evidence"
        elif answer_hit and not retrieval_hit:
            cause = "answer_hit_without_top5_alias_evidence"
        elif retrieval_hit:
            cause = "qa_underused_retrieved_evidence"
        elif kb_hit:
            cause = "retrieval_miss_top5"
        else:
            cause = "rubric_or_alias_gap"

        criteria_details.append(
            {
                "label": criterion["label"],
                "cause": cause,
                "answer_hit": answer_hit,
                "retrieval_hit": retrieval_hit,
                "kb_hit": kb_hit,
                "answer_alias_hits": answer_hits,
                "retrieval_alias_hits": retrieval_hits,
                "kb_alias_hits": kb_hits,
                "required_hits": required_hits,
            }
        )

    return {
        "id": record["id"],
        "question": record["question"],
        "titles": titles,
        "answer_score": sum(1 for item in criteria_details if item["answer_hit"]),
        "retrieval_ceiling": sum(1 for item in criteria_details if item["retrieval_hit"]),
        "criteria": criteria_details,
    }


def summarize_run(run, diagnosis):
    all_criteria = [criterion for record in diagnosis for criterion in record["criteria"]]
    summary = {
        **run,
        "criteria_count": len(all_criteria),
        "answer_score": sum(1 for criterion in all_criteria if criterion["answer_hit"]),
        "retrieval_ceiling": sum(1 for criterion in all_criteria if criterion["retrieval_hit"]),
        "answered_with_retrieved_evidence": count_cause(all_criteria, "answered_with_retrieved_evidence"),
        "answer_hit_without_top5_alias_evidence": count_cause(all_criteria, "answer_hit_without_top5_alias_evidence"),
        "qa_underused_evidence": count_cause(all_criteria, "qa_underused_retrieved_evidence"),
        "retrieval_miss": count_cause(all_criteria, "retrieval_miss_top5"),
        "rubric_or_alias_gap": count_cause(all_criteria, "rubric_or_alias_gap"),
    }
    summary["answer_percent"] = round(summary["answer_score"] / summary["criteria_count"] * 100, 1)
    summary["retrieval_ceiling_percent"] = round(summary["retrieval_ceiling"] / summary["criteria_count"] * 100, 1)
    return summary


def count_cause(criteria, cause: str) -> int:
    return sum(1 for criterion in criteria if criterion["cause"] == cause)


def parse_retrieved_titles(answer_output: str):
    titles = []
    for line in str(answer_output).splitlines():
        if not re.match(r"^\d+\.\s+", line) or " / score=" not in line:
            continue
        before_score = line.split(" / score=", 1)[0]
        after_number = before_score.split(". ", 1)[1]
        parts = after_number.split(" / ")
        if len(parts) >= 2:
            titles.append(" / ".join(parts[1:]))
    return titles


def criterion_match(text: str, criterion):
    normalized = normalize_text(text)
    aliases = [alias for alias in criterion.get("aliases", []) if str(alias).strip()]
    hits = [alias for alias in aliases if normalize_text(alias) in normalized]
    required_hits = 2 if len(aliases) >= 4 else 1
    return len(hits) >= required_hits, hits, required_hits


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", str(text)).lower()


def chunk_text(chunk) -> str:
    return f"{chunk.get('parent_title', '')}\n{chunk.get('title', '')}\n{chunk.get('content', '')}"


def write_report(report_path: Path, summaries, details) -> None:
    lines = [
        "# Direct30 Failure Cause Diagnosis",
        "",
        f"- Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Questions: `{QUESTION_PATH.as_posix()}`",
        f"- Chunks: `{CHUNK_PATH.as_posix()}`",
        "",
        "## Method",
        "",
        "This report diagnoses whether misses are more likely caused by retrieval or QA/model behavior.",
        "",
        "- Scoring uses the initial user10 rule: each criterion is 1 point; criteria with 4+ aliases require at least 2 alias hits.",
        "- Retrieval ceiling applies the same alias rule to the Top5 retrieved chunks.",
        "- If Top5 has the criterion but Final Answer misses it, the cause is `qa_underused_retrieved_evidence`.",
        "- If Top5 misses it but the full KB has aliases for it, the cause is `retrieval_miss_top5`.",
        "- If neither Top5 nor full KB matches by aliases, the cause is `rubric_or_alias_gap`.",
        "- Alias checks are a reproducible proxy, not a substitute for manual semantic review.",
        "",
        "## Summary",
        "",
        "| Mode | Answer Score | Retrieval Ceiling | Answered With Retrieved Evidence | QA Underused Retrieved Evidence | Retrieval Miss Top5 | Rubric/Alias Gap | Answer Hit Without Top5 Alias Evidence |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for summary in summaries:
        lines.append(
            f"| {summary['mode']} | "
            f"`{summary['answer_score']} / {summary['criteria_count']} = {summary['answer_percent']}` | "
            f"`{summary['retrieval_ceiling']} / {summary['criteria_count']} = {summary['retrieval_ceiling_percent']}` | "
            f"{summary['answered_with_retrieved_evidence']} | "
            f"{summary['qa_underused_evidence']} | "
            f"{summary['retrieval_miss']} | "
            f"{summary['rubric_or_alias_gap']} | "
            f"{summary['answer_hit_without_top5_alias_evidence']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `Retrieval Ceiling - Answer Score` is the recoverable QA/model gap under this alias rubric.",
            "- `Retrieval Miss Top5` is the clearest retrieval failure bucket.",
            "- `Rubric/Alias Gap` should be manually inspected because aliases may be too strict or the criterion may require inference rather than exact wording.",
            "",
            "## Miss Details",
            "",
        ]
    )

    for summary in summaries:
        mode = summary["mode"]
        lines.extend([f"### {mode}", ""])
        for record in details[mode]:
            misses = [
                criterion
                for criterion in record["criteria"]
                if criterion["cause"] in {
                    "qa_underused_retrieved_evidence",
                    "retrieval_miss_top5",
                    "rubric_or_alias_gap",
                }
            ]
            if not misses:
                continue
            lines.append(
                f"- `{record['id']}` answer `{record['answer_score']}/3`, "
                f"retrieval ceiling `{record['retrieval_ceiling']}/3`: {record['question']}"
            )
            for criterion in misses:
                lines.append(
                    f"  - `{criterion['cause']}`: {criterion['label']} "
                    f"(answer hits={criterion['answer_alias_hits']}, "
                    f"retrieval hits={criterion['retrieval_alias_hits']}, "
                    f"kb hits={criterion['kb_alias_hits'][:5]}, "
                    f"required={criterion['required_hits']})"
                )
            lines.append(f"  - Top5: {' | '.join(record['titles'])}")
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
