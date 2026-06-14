# Qwen RAG Three Body New10 Colab-Architecture Retest

- Time: 2026-06-14 12:30
- Reference Colab: `https://colab.research.google.com/drive/1CvaUtmTKUCrvuXwvjsa-45eehyEGBaKt`
- Model: `qwen2.5:7b`
- Question file: `evals/three_body_qwen/questions_new10_20260614.json`
- Raw answers: `evals/three_body_qwen/three_body_35_raw_answers_20260614-123026.jsonl`
- Raw report: `evals/three_body_qwen/three_body_35_raw_report_20260614-123026.md`
- Scored report: `evals/three_body_qwen/three_body_new10_colab_arch_scored_report_20260614-123026.md`

## Changes under test

- Added `rag_demo/retrieval_planner.py`.
- Integrated planner query variants into `rag_demo/query.py`.
- Added focus-term extraction to `rag_demo/context_summary.py`.
- Added focus-term extraction to `rag_demo/retrieval_verifier.py`.
- Added planner and verifier regression tests.

## Unit tests

- Result: `118/118 OK`
- Record: `test-records/test-record-20260614-123016.md`

## RAG eval

- Completed: `10/10`
- Runtime errors: `0`
- Total elapsed: about `88s`

## Manual score

- NQ01: 3/5
- NQ02: 5/5
- NQ03: 4/5
- NQ04: 0/5
- NQ05: 3/5
- NQ06: 2/5
- NQ07: 5/5
- NQ08: 4/5
- NQ09: 5/5
- NQ10: 0/5

Total: `31 / 50 = 62 / 100`

## Notes

The Colab-style planning layer improved retrieval coverage and reduced verifier false negatives for unspaced Chinese questions. Remaining failures are mostly answer-generation and evidence-selection problems, especially event consequence and viewpoint comparison questions.
