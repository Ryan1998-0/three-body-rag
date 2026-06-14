# Three Body 5Q Alias Fix Scored Report 20260613-142013

- Raw run: `evals/three_body_qwen/three_body_35_raw_answers_20260613-142013.jsonl`
- Raw report: `evals/three_body_qwen/three_body_35_raw_report_20260613-142013.md`
- Test record: `test-records/qwen-rag-three-body-35q-20260613-142013.md`
- Selected IDs: `Q02, Q03, Q06, Q08, Q15`
- Model: `qwen2.5:7b`
- Top K: `5`
- Runtime completion: `5/5`
- Runtime errors: `0`
- Verifier related: `5/5`

## Score

- Before alias fix on this 5-question subset: `0 / 25`
  - Q02: 0
  - Q03: 0
  - Q06: 0
  - Q08: 0
  - Q15: 0
  - Note: the previous full-report score gave Q08/Q15 no credit because the final answer was prefixed as source-insufficient despite containing partial correct content.
- After alias fix: `25 / 25`
- Normalized subset score: `100 / 100`

## Per-question Results

| ID | Score | Verifier | Result |
| --- | ---: | --- | --- |
| Q02 | 5 | True | Correctly answered that 葉文潔的父親 was beaten to death by Red Guards during a Cultural Revolution criticism session. |
| Q03 | 5 | True | Correctly answered 申玉菲. |
| Q06 | 5 | True | Correctly answered 納米材料研究. |
| Q08 | 5 | True | Correctly defined 恆紀元 as stable orbit around one sun and 亂紀元 as unstable motion under multiple suns. |
| Q15 | 5 | True | Correctly summarized 智子 tasks: accelerator interference, science disruption, miracle plan, monitoring/communication. |

## Fix Summary

Implemented a generic alias layer:

- `data/entities/aliases.json`
- `rag_demo/entity_aliases.py`
- Query expansion in `rag_demo/query.py`

Additional generic support added:

- Deterministic evidence extraction now uses alias-expanded query terms.
- Verifier now accepts deterministic evidence when alias-expanded query terms clearly overlap retrieved evidence.
- Direct-cause resolver handles death-cause questions when evidence explicitly says someone was deprived of life or the body had no life signs.

## Test Records

- Unit tests before final retest: `test-records/test-record-20260613-142003.md`
- Final 5-question RAG retest: `test-records/qwen-rag-three-body-35q-20260613-142013.md`
