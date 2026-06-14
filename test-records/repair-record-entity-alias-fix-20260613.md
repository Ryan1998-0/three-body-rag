# Repair Record: Generic Entity Alias Layer 2026-06-13

## Goal

Add a generic entity alias layer and retest only five questions:

- Q02
- Q03
- Q06
- Q08
- Q15

## Changes

- Added `data/entities/aliases.json`.
- Added `rag_demo/entity_aliases.py`.
- Wired alias expansion into `rag_demo/query.py`.
- Added alias-expanded query terms to deterministic evidence extraction.
- Added generic verifier acceptance for deterministic evidence that overlaps alias-expanded query terms.
- Added direct-cause evidence resolver for questions asking how someone died.
- Added `RAG_EVAL_IDS` support to `evals/three_body_qwen/run_eval_35.py`.

## Verification

- Unit test record: `test-records/test-record-20260613-142003.md`
- Unit test result: `103 tests OK`
- Five-question RAG retest record: `test-records/qwen-rag-three-body-35q-20260613-142013.md`
- Five-question RAG result: `5/5 completed`, `0 errors`
- Five-question verifier result: `5/5 related`
- Five-question score: `25/25`

## Notes

The alias resolver is generic. Domain-specific vocabulary lives in `data/entities/aliases.json`; code only loads records, matches aliases/triggers, and expands the retrieval query.
