# Qwen RAG Three Body User10 Chunk Size Comparison Test Record

- Date: 2026-06-14
- Model: `qwen2.5:7b`
- Top K: `5`
- Question file: `evals/three_body_qwen/questions_user10_20260614.json`
- Purpose: sequentially rebuild the RAG index with three chunk settings and compare answer quality.

## Commands

For each run:

```powershell
$env:RAG_CHUNK_SIZE='<chunk_size>'
$env:RAG_CHUNK_STRIDE='<chunk_stride>'
python -m rag_demo.ingest
$env:RAG_EVAL_QUESTIONS_FILE='evals/three_body_qwen/questions_user10_20260614.json'
$env:RAG_EVAL_MODEL='qwen2.5:7b'
$env:RAG_EVAL_TOP_K='5'
python -X utf8 evals\three_body_qwen\run_eval_35.py
```

## Results

| Setting | Completed | Errors | Elapsed | Raw JSONL | Manual score |
|---|---:|---:|---:|---|---:|
| `1200/600` | 10/10 | 0 | 90.650s | `evals/three_body_qwen/three_body_35_raw_answers_20260614-125913.jsonl` | 40/50 |
| `900/450` | 10/10 | 0 | 96.668s | `evals/three_body_qwen/three_body_35_raw_answers_20260614-130129.jsonl` | 38/50 |
| `700/350` | 10/10 | 0 | 172.226s | `evals/three_body_qwen/three_body_35_raw_answers_20260614-130418.jsonl` | 30/50 |

## Artifacts

- Comparison report: `evals/three_body_qwen/three_body_user10_chunk_size_comparison_20260614.md`
- Final answer extract: `evals/three_body_qwen/three_body_user10_chunk_size_answer_extract_20260614.md`
- Raw run records:
  - `test-records/qwen-rag-three-body-35q-20260614-125913.md`
  - `test-records/qwen-rag-three-body-35q-20260614-130129.md`
  - `test-records/qwen-rag-three-body-35q-20260614-130418.md`

## Notes

- Best setting in this batch: `1200/600`.
- Baseline from previous `1800/900` run: `35/50 = 70/100`.
- `1200/600` improved to `40/50 = 80/100`.
- The raw markdown reports have partial Chinese mojibake in headings, but raw JSONL answer outputs are valid UTF-8 and were used for manual scoring.
- Dependency issue fixed before testing: `transformers` was adjusted to `4.57.6` after `sentence-transformers` failed to import due to `huggingface_hub.is_offline_mode` mismatch.
- Final local index state: rebuilt to `1200/600` after comparison.
