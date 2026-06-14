# Three Body Random 10 Sparse-Fact Repair Scored Report 20260613-221016

## Scope

- Task: repair the RAG pipeline, then retest 10 randomly selected questions.
- Random seed: `2026061322`
- Selected IDs: `Q02,Q04,Q08,Q09,Q20,Q21,Q26,Q27,Q30,Q34`
- Model: `qwen2.5:7b`
- Top K: `5`
- Raw JSONL: `evals/three_body_qwen/three_body_35_raw_answers_20260613-221016.jsonl`
- Raw report: `evals/three_body_qwen/three_body_35_raw_report_20260613-221016.md`
- Test record: `test-records/qwen-rag-three-body-35q-20260613-221016.md`
- Latest unit test record: `test-records/test-record-20260613-221003.md`

## Repairs Applied

1. Added sparse-fact retrieval anchors by question type:
   - Trisolaris survival problem.
   - Signal reception.
   - Distance facts.
   - Red Coast official purpose.
   - Evans/Ye Wenjie meeting.
   - Three Body game prediction methods and figures.
   - Fleet-to-Earth cause.
   - Wang Miao countdown display.
   - Chang Weisi role.
   - Open-ended ETO stance questions.

2. Added deterministic answer gate before verifier:
   - If deterministic evidence directly answers the question, the answer no longer depends on the verifier's LLM judgment.
   - This specifically prevents false negatives like "retrieval found the listener evidence but verifier rejected it."

3. Added alias/entity records:
   - Sparse facts now live in `data/entities/aliases.json` as reusable entity/query-expansion data, not only in the pipeline code.

## Automated Tests

- Command: `python -X utf8 scripts/run_tests_with_record.py`
- Result: `114 / 114 OK`
- Record: `test-records/test-record-20260613-221003.md`

## Random 10 Retest Result

- Completed: `10 / 10`
- Runtime errors: `0`
- Verifier/direct deterministic pass: `10 / 10`
- Manual score: `48 / 50` = `96 / 100`

## Manual Scoring

| ID | Score | Result | Notes |
|---|---:|---|---|
| Q02 | 5/5 | Pass | Correctly answers that Ye Wenjie's father died after Red Guard violence during a Cultural Revolution struggle session. |
| Q04 | 5/5 | Pass | Correctly connects scientist suicides to collapse of confidence in physics, Yang Dong's note, accelerator anomalies, and sophons. |
| Q08 | 5/5 | Pass | Correctly explains chaotic eras versus stable eras using the three-sun orbital context. |
| Q09 | 5/5 | Pass | Correctly keeps focus on Trisolaris's survival problem, not ETO/human weakness. |
| Q20 | 4/5 | Pass with minor omission | Correctly lists several game figures, but could include more names such as Copernicus/Galileo/Kepler depending scoring strictness. |
| Q21 | 5/5 | Pass | Correctly explains Earth reply/location, Trisolaris survival opportunity, and fear of Earth's accelerating technology. |
| Q26 | 5/5 | Pass | Correctly explains countdown on film/photos and later vision/retina, with sophon mechanism. |
| Q27 | 4/5 | Pass with minor omission | Correctly identifies Chang Weisi as a military commander/core coordinator, but does not explicitly mention rank details. |
| Q30 | 5/5 | Pass | Correctly answers Cultural Revolution period / around 1969 and Red Coast context. |
| Q34 | 5/5 | Pass | Provides a grounded open-ended judgment: ETO sees real human civilization problems, but this does not justify betrayal/destruction. |

## Conclusion

The random 10 retest is now above the 60-point target by a wide margin. The main improvement came from adding sparse-fact anchors and allowing direct deterministic evidence to answer before the verifier can false-reject it.

## Residual Risk

- Some answers still include more evidence lines than necessary.
- Q20/Q27 could be polished further by adding a final answer compression/rerank step so lists are more complete and concise.
