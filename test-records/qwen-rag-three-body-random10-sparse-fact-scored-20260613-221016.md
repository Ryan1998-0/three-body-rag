# Qwen RAG Three Body Random 10 Sparse-Fact Scored Test Record 20260613-221016

- Command: `python -X utf8 evals/three_body_qwen/run_eval_35.py`
- Random seed: `2026061322`
- Selected IDs: `Q02,Q04,Q08,Q09,Q20,Q21,Q26,Q27,Q30,Q34`
- Model: `qwen2.5:7b`
- Top K: `5`
- Raw JSONL: `evals/three_body_qwen/three_body_35_raw_answers_20260613-221016.jsonl`
- Raw report: `evals/three_body_qwen/three_body_35_raw_report_20260613-221016.md`
- Scored report: `evals/three_body_qwen/three_body_random10_sparse_fact_repair_scored_report_20260613-221016.md`
- Completed: `10 / 10`
- Runtime errors: `0`
- Manual score: `48 / 50` = `96 / 100`

## Notes

- The repair target was at least 60/100.
- This run passed the target with a conservative manual score of 96/100.
