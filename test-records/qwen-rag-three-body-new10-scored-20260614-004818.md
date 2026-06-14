# Qwen RAG Three Body New 10 Scored Test Record 20260614-004818

- Command: `python -X utf8 evals/three_body_qwen/run_eval_35.py`
- Question file: `evals/three_body_qwen/questions_new10_20260614.json`
- Model: `qwen2.5:7b`
- Top K: `5`
- Raw JSONL: `evals/three_body_qwen/three_body_35_raw_answers_20260614-004818.jsonl`
- Raw report: `evals/three_body_qwen/three_body_35_raw_report_20260614-004818.md`
- Scored report: `evals/three_body_qwen/three_body_new10_scored_report_20260614-004818.md`
- Completed: `10 / 10`
- Runtime errors: `0`
- Manual score: `29 / 50` = `58 / 100`

## Notes

- These are newly created questions, not a subset of the original 35-question set.
- The result shows the current pipeline still needs better generic handling for analogy, failure-cause, action-purpose, and character-viewpoint questions.
