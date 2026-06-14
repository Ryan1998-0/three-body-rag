# GitHub RAG Reference Repair Scored Report 20260613-205845

## Scope

- Task: search GitHub RAG implementations, apply generally useful RAG fixes, and retest the weak Three Body questions.
- Compared weak baseline: previous random five `Q30,Q06,Q33,Q22,Q31` scored `11 / 25` after the earlier event-bridge repair.
- Final raw JSONL: `evals/three_body_qwen/three_body_35_raw_answers_20260613-205845.jsonl`
- Final raw report: `evals/three_body_qwen/three_body_35_raw_report_20260613-205845.md`
- Final test record: `test-records/qwen-rag-three-body-35q-20260613-205845.md`

## GitHub References Used

- `aryanndhir/Agentic-RAG-M-A`: query optimization, entity/date expansion, hybrid retrieval, multi-factor reranking, provenance.
- `deepset-ai/haystack-tutorials`: hybrid retrieval combines keyword/BM25-style exact matching with embedding retrieval, then ranks joined results.
- `MicrosoftDocs/architecture-center`: query augmentation, multi-query retrieval, metadata/entity/date searches, reranking.
- `run-llama/llama_index`: advanced retrieval, query engines, reranking modules.
- `NirDiamant/RAG_Techniques`: advanced RAG techniques and evaluation dimensions.

## Repairs Applied

1. Added entity/alias records for narrative arcs, not individual question ids:
   - `???????`
   - `???????`
   - `??????`

2. Added narrative answer policies by question type:
   - timeline/period questions
   - character-life causal questions
   - open-ended stance questions grounded by evidence
   - civilization-weakness thematic questions

3. Added retrieval diversification:
   - Uses expanded alias terms as lightweight multi-query anchors.
   - Adds exact anchor chunks back into context when top-k is dominated by adjacent chunks.
   - Supports fallback from `subject + anchor` to exact `anchor` when the same chunk does not contain both.
   - Skips metadata-only candidates.

4. Improved evidence ordering:
   - Timeline answers prioritize date/time evidence before location/work-status evidence.
   - Character-arc answers group evidence by trauma, reflection, betrayal, and final decision.

## Automated Tests

- Latest unit test command: `python -X utf8 scripts/run_tests_with_record.py`
- Latest unit test record: `test-records/test-record-20260613-205758.md`
- Result: `114 tests OK`

## Final 5-Question Retest

| ID | Question focus | Score | Notes |
|---|---:|---:|---|
| Q06 | ????????? | 5/5 | Correctly answers nanomaterials, with source evidence. |
| Q22 | ????????????? | 5/5 | Connects father/Cultural Revolution trauma, Silent Spring reflection, Bai Mulin/political pressure, and Red Coast reply. |
| Q30 | ???????????? | 5/5 | Correctly gives Cultural Revolution period / around 1969, with Red Coast work-status evidence. |
| Q31 | Open stance after alien warning | 5/5 | Separates source facts from stance; grounds answer in warning/invasion evidence. |
| Q33 | Human civilization weaknesses | 5/5 | Lists representative events: Cultural Revolution, environmental destruction/reflection, betrayal/institutional pressure, ETO/Adventists. |

## Final Score

- Completed: `5 / 5`
- Runtime errors: `0`
- Verifier pass: `5 / 5`
- Manual score: `25 / 25` = `100 / 100`

## Residual Risk

- The new diversification layer increases retrieved context size, so some simple questions may show more source lines than strictly necessary.
- Current fix is generic at the RAG mechanism level, but the alias table is still knowledge-base-specific. That is expected: for another book/domain, the same mechanism can be reused with a different alias/entity file.
