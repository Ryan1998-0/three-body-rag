# Qwen RAG Three Body 15Q Scored Test Record 20260613-210339

- Command: `python -X utf8 evals/three_body_qwen/run_eval_35.py`
- Selected IDs: `Q01,Q04,Q05,Q07,Q09,Q10,Q11,Q12,Q13,Q14,Q16,Q17,Q18,Q19,Q20`
- Model: `qwen2.5:7b`
- Top K: `5`
- Raw JSONL: `evals/three_body_qwen/three_body_35_raw_answers_20260613-210339.jsonl`
- Raw report: `evals/three_body_qwen/three_body_35_raw_report_20260613-210339.md`
- Scored report: `evals/three_body_qwen/three_body_15_retest_scored_report_20260613-210339.md`
- Completed: `15 / 15`
- Runtime errors: `0`
- Verifier marked related: `9 / 15`
- Manual score: `37 / 75` = `49.3 / 100`

## Notes

- This retest shows the repaired RAG architecture is stronger on Ye Wenjie / Red Coast / ETO / sophon-threat questions.
- Remaining failures are concentrated in sparse factual retrieval and question-focus drift.
