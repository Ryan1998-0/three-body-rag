# Qwen RAG Three Body 35Q Test Record 20260613-144850

- Command: `python.exe -X utf8 evals/three_body_qwen/run_eval_35.py`
- Model: `qwen2.5:7b`
- Top K: `5`
- Question file: `evals\three_body_qwen\questions_35_20260613.json`
- Selected IDs: `Q30, Q06, Q33, Q22, Q31`
- Raw JSONL: `evals\three_body_qwen\three_body_35_raw_answers_20260613-144850.jsonl`
- Raw report: `evals\three_body_qwen\three_body_35_raw_report_20260613-144850.md`
- Completed: `5/5`
- Errors: `0`
- Total elapsed: `63.444s`

## Notes

- This run records raw RAG/Qwen outputs for review.
- Manual answer scoring is intentionally not included in this runner.

## Manual Scoring

- Scored report: `evals\three_body_qwen\three_body_random5_after_event_bridge_scored_report_20260613-144850.md`
- Random seed: `20260613`
- Excluded IDs: `Q04, Q05, Q11, Q12, Q16`
- Sampled IDs: `Q30, Q06, Q33, Q22, Q31`
- Score: `11 / 25`
- Normalized subset score: `44 / 100`
- Verifier related: `4 / 5`
