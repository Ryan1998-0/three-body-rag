# Three Body 5Q Alias Fix Follow-up Scored Report 20260613-142248

- Raw run: `evals/three_body_qwen/three_body_35_raw_answers_20260613-142248.jsonl`
- Raw report: `evals/three_body_qwen/three_body_35_raw_report_20260613-142248.md`
- Test record: `test-records/qwen-rag-three-body-35q-20260613-142248.md`
- Selected IDs: `Q04, Q05, Q11, Q12, Q16`
- Model: `qwen2.5:7b`
- Top K: `5`
- Runtime completion: `5/5`
- Runtime errors: `0`
- Verifier related: `1/5`

## Score

- Before alias fix on this 5-question subset: `0 / 25`
- After current alias fix: `3 / 25`
- Normalized subset score: `12 / 100`

## Per-question Results

| ID | Score | Verifier | Result |
| --- | ---: | --- | --- |
| Q04 | 0 | False | Still source-insufficient. It did not retrieve/accept evidence linking scientist suicides to disrupted physics, sophons, and scientific despair. |
| Q05 | 0 | False | Still source-insufficient. It did not retrieve/accept the Yang Dong / failed physics experiment background behind "物理學不存在了". |
| Q11 | 3 | True | Partially correct. It identified the ETO/降臨派 goal of using alien power to destroy humanity, but over-narrowed ETO into the降臨派 and missed broader faction complexity. |
| Q12 | 0 | False | Still source-insufficient. It did not retrieve/accept evidence that Ye Wenjie sent/replied to the cosmic signal through Red Coast. |
| Q16 | 0 | False | Still source-insufficient. It did not retrieve/accept the warning message: do not answer, or your world will be located/conquered. |

## Diagnosis

The generic alias layer worked for direct entity/term aliases in the previous subset, but this follow-up subset needs event-level aliases and causal bridge terms.

Next alias/data additions should cover:

- `科學家自殺` -> `楊冬`, `物理學不存在`, `實驗結果`, `智子`, `高能加速器`, `科學信念崩塌`
- `物理學不存在了` -> `楊冬`, `丁儀`, `三台新的高能加速器`, `實驗結果`, `無規律`
- `紅岸重要決定` -> `葉文潔`, `回覆`, `再次發送`, `太陽`, `紅岸之六`
- `第一次收到外星文明回覆` -> `不要回答`, `監聽員`, `警告`, `坐標`, `入侵`, `征服`

This suggests the next repair should be an event-alias layer or an event query expansion layer, not only entity aliases.
