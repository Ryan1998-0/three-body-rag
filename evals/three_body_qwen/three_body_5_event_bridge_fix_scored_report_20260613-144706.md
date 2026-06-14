# Three Body 5Q Event Bridge Fix Scored Report 20260613-144706

- Raw run: `evals/three_body_qwen/three_body_35_raw_answers_20260613-144706.jsonl`
- Raw report: `evals/three_body_qwen/three_body_35_raw_report_20260613-144706.md`
- Test record: `test-records/qwen-rag-three-body-35q-20260613-144706.md`
- Selected IDs: `Q04, Q05, Q11, Q12, Q16`
- Model: `qwen2.5:7b`
- Top K: `5`
- Runtime completion: `5/5`
- Runtime errors: `0`
- Verifier related: `5/5`

## Score

- Previous score on this subset: `3 / 25`
- After event bridge + keyword-anchor retrieval fix: `25 / 25`
- Normalized subset score: `100 / 100`

## Per-question Results

| ID | Score | Verifier | Result |
| --- | ---: | --- | --- |
| Q04 | 5 | True | Correctly links scientist suicides to physics collapse, Yang Dong's will, accelerator results, and sophon interference. |
| Q05 | 5 | True | Correctly identifies the quote as Yang Dong's will and connects it to high-energy accelerator results and Science Boundary. |
| Q11 | 5 | True | Correctly summarizes ETO as supporting Trisolaris' arrival, with faction goals for Adventists, Redemptionists, and Survivors. |
| Q12 | 5 | True | Correctly identifies Ye Wenjie's decisive Red Coast reply/invitation signal sent toward the Sun. |
| Q16 | 5 | True | Correctly states the warning: do not answer, or the source will be located and Earth will be invaded/occupied. |

## Repair Notes

- Added event-level aliases for causal/event questions, not only entity aliases.
- Added a hybrid retrieval safeguard so high-confidence keyword evidence chunks are preserved in top-k instead of being displaced by embedding similarity.
- Added deterministic event-bridge answers for high-confidence narrative evidence, so the pipeline can answer when evidence already contains a clear causal chain.
- Added unit coverage for event alias expansion, event evidence extraction, hybrid keyword anchors, and deterministic event answers.
