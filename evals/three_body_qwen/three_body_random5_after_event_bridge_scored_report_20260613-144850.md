# Three Body Random 5Q After Event Bridge Scored Report 20260613-144850

- Raw run: `evals/three_body_qwen/three_body_35_raw_answers_20260613-144850.jsonl`
- Raw report: `evals/three_body_qwen/three_body_35_raw_report_20260613-144850.md`
- Test record: `test-records/qwen-rag-three-body-35q-20260613-144850.md`
- Random seed: `20260613`
- Excluded IDs: `Q04, Q05, Q11, Q12, Q16`
- Sampled IDs: `Q30, Q06, Q33, Q22, Q31`
- Model: `qwen2.5:7b`
- Top K: `5`
- Runtime completion: `5/5`
- Runtime errors: `0`
- Verifier related: `4/5`

## Score

- Random subset score: `11 / 25`
- Normalized subset score: `44 / 100`

## Per-question Results

| ID | Score | Verifier | Result |
| --- | ---: | --- | --- |
| Q06 | 5 | True | Correctly answered that Wang Miao researches nanomaterials. |
| Q22 | 0 | True | Failed to answer the causal question; it returned source-insufficient despite retrieving Red Coast and Ye Wenjie experience context. |
| Q30 | 0 | False | Failed to answer the timing question about when Ye Wenjie was transferred to Red Coast. |
| Q31 | 2 | True | Retrieved the warning/reply evidence, but did not answer the open stance question of whether the respondent would send again and why. |
| Q33 | 4 | True | Gave a grounded answer about ETO and elite betrayal as human-civilization weakness, but the answer was narrow for an open multi-event question. |

## Diagnosis

- The event-bridge repair generalized well to fact/event questions with explicit evidence.
- The remaining weak spots are different:
  - timeline questions need a better date/period extraction layer;
  - life-experience causal questions need a character timeline or biography summary layer;
  - open-ended opinion questions need a mode that separates source-grounded facts from the user's requested judgment.
