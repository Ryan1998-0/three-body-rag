# Colab RAG Agent Architecture Integration + New10 Retest

- Time: 2026-06-14 12:30
- Reference: `https://colab.research.google.com/drive/1CvaUtmTKUCrvuXwvjsa-45eehyEGBaKt`
- Model: `qwen2.5:7b`
- Question file: `evals/three_body_qwen/questions_new10_20260614.json`
- Raw answers: `evals/three_body_qwen/three_body_35_raw_answers_20260614-123026.jsonl`
- Raw report: `evals/three_body_qwen/three_body_35_raw_report_20260614-123026.md`

## Colab architecture notes

The referenced Colab notebook is an RAG + agents scaffold:

- Environment setup: mount Drive, install local LLM/search dependencies, load model.
- LLM utility: `generate_response(model, messages)` wraps chat completion.
- Search tool: keyword search and web page fetching helpers.
- Agent class: `LLMAgent(role_description, task_description)` separates role from task.
- Agent roles: question extraction, keyword extraction, QA.
- Pipeline: `pipeline(question)` is intended to call multiple agents and retrieval steps.
- Batch answering: per-question output files are saved so interrupted runs can resume.

Important design idea adopted here: do not treat retrieval as one query. Add an intermediate planning layer that extracts the question focus, intent, and multiple query variants before answer generation.

## Implemented changes

1. Added `rag_demo/retrieval_planner.py`.
   - Builds a deterministic agent-style `RetrievalPlan`.
   - Extracts focus terms from unspaced Traditional Chinese questions.
   - Infers intent labels such as `cause`, `method`, `failure_reason`, `explanation`, `comparison`, and `purpose`.
   - Produces multiple query variants and one evidence query.

2. Updated `rag_demo/query.py`.
   - Keeps the original primary retrieval behavior.
   - Adds supplemental retrieval from planner query variants.
   - Merges supplemental chunks without replacing the primary ranking.
   - Uses the planner evidence query for deterministic evidence extraction.
   - Adds `planned_retrieval` timing.

3. Updated `rag_demo/context_summary.py` and `rag_demo/retrieval_verifier.py`.
   - Both now use the same focus-term extraction logic.
   - This fixes a verifier failure mode where unspaced Chinese questions were treated as one long unusable term.

4. Added tests.
   - Retrieval planner focus extraction.
   - Failure-reason query variants.
   - Purpose and comparison intent variants.
   - Verifier evidence overlap for unspaced Chinese questions.

## Test results

Unit tests:

- `118/118 OK`
- Record: `test-records/test-record-20260614-123016.md`

New10 RAG eval:

- Completed: `10/10`
- Runtime errors: `0`
- Record: `test-records/qwen-rag-three-body-35q-20260614-123026.md`

## Manual scoring

| ID | Score | Notes |
| --- | ---: | --- |
| NQ01 | 3/5 | Retrieved the 台球/丁儀 evidence and gave the correct general idea, but still wrapped it in an unnecessary "無法確認" framing and added noise. |
| NQ02 | 5/5 | Correctly answered 魏成's evolutionary-algorithm style reasoning and massive-computation framing. |
| NQ03 | 4/5 | Correctly identified the three-sun explanation and why 墨子's model failed; minor overstatement about lack of observation. |
| NQ04 | 0/5 | Failed final answer; retrieved some relevant sources but answered "無法確認". |
| NQ05 | 3/5 | Captured that 飛刃 was used to seize/preserve information, but answer focused too much on fixing wire/pillar details. |
| NQ06 | 2/5 | Partially identified important 三體 information on 審判日號, but misstated it as a "三體問題 solution" and was too indirect. |
| NQ07 | 5/5 | Correctly listed sophon miracles: film/retina text, CMB flicker, unfolding around Earth. |
| NQ08 | 4/5 | Correctly mentioned location/invasion risk; included extra monitor-station reasoning. |
| NQ09 | 5/5 | Correctly answered signal weakens with distance and space interference. |
| NQ10 | 0/5 | Failed final answer; retrieved 大史 chunks but did not form the viewpoint comparison. |

Total: `31 / 50 = 62 / 100`

## Observed improvement

Previous New10 score was about `58 / 100`. After adopting the Colab-style planning layer and fixing verifier focus terms, this run reached `62 / 100`.

Main improvement:

- Retrieval now pulls in missing supplemental chunks, for example NQ01 includes `5.台 球`.
- Verifier no longer blocks all unspaced Chinese evidence-overlap cases.
- Runtime improved from about `130s` to about `88s` for the 10-question batch.

Remaining generic issues:

- Final answer generation still over-trusts the verifier failure framing.
- Event-consequence questions need better extraction of "event -> result" spans.
- Viewpoint-comparison questions need evidence pairing, not only broad chunk retrieval.
- Retrieval can now bring in too many supplemental chunks, so a reranker/noise filter should be added before answer generation.
