# Simulated Questions and Answers

本文件整理目前已推上 GitHub 的模擬問題、QA Agent 回答、評分報告與 retrieval upper-bound 報告。README 只保留連結，不展開這些大型 raw / report 內容。

## Closed Questions

| File | Description |
| --- | --- |
| [questions_first20_closed_20260615.json](../evals/three_body_qwen/questions_first20_closed_20260615.json) | 第一集封閉式 20 題題庫 |
| [first20_closed_raw_answers_20260615-104328.jsonl](../evals/three_body_qwen/first20_closed_raw_answers_20260615-104328.jsonl) | First20 QA Agent 原始回答 |
| [first20_closed_scored_report_20260615-112525_final.md](../evals/three_body_qwen/first20_closed_scored_report_20260615-112525_final.md) | First20 deterministic scored report |
| [first20_closed_semantic_rescore_20260615.md](../evals/three_body_qwen/first20_closed_semantic_rescore_20260615.md) | First20 語意寬鬆重評報告 |
| [first20_retrieval_upper_bound_report_20260615-162647.md](../evals/three_body_qwen/first20_retrieval_upper_bound_report_20260615-162647.md) | First20 retrieval upper-bound 最終報告 |

## Open Questions

| File | Description |
| --- | --- |
| [questions_direct30_lenient_20260615.json](../evals/three_body_qwen/questions_direct30_lenient_20260615.json) | 第一集開放式 Direct30 題庫 |
| [three_agent_direct30_hybrid_rerank_raw_answers_20260615-011430.jsonl](../evals/three_body_qwen/three_agent_direct30_hybrid_rerank_raw_answers_20260615-011430.jsonl) | Direct30 hybrid rerank 原始回答 |
| [three_agent_direct30_hybrid_rerank_scored_report_20260615-011430.md](../evals/three_body_qwen/three_agent_direct30_hybrid_rerank_scored_report_20260615-011430.md) | Direct30 hybrid rerank QA scored report |
| [direct30_retrieval_mode_comparison_with_hybrid_20260615-011430.md](../evals/three_body_qwen/direct30_retrieval_mode_comparison_with_hybrid_20260615-011430.md) | embedding / keyword-only / hybrid rerank 比較 |
| [direct30_failure_cause_diagnosis_20260615-074407.md](../evals/three_body_qwen/direct30_failure_cause_diagnosis_20260615-074407.md) | Retrieval vs QA failure diagnosis |
| [direct30_bad_open_retrieval_upper_bound_report_20260616-011403.md](../evals/three_body_qwen/direct30_bad_open_retrieval_upper_bound_report_20260616-011403.md) | 弱開放題 current V2 retrieval upper-bound 報告 |

## Raw Context Records

以下檔案包含完整 retrieved context、QA output 或 scoring trace，適合 debug，不適合放進 README：

```text
evals/three_body_qwen/*raw_answers*.jsonl
evals/three_body_qwen/*retrieval_upper_bound_raw*.jsonl
evals/three_body_qwen/*scored_report*.md
```

## Evaluation Summary

| Evaluation | Result |
| --- | ---: |
| First20 closed semantic score | `85 / 100` |
| First20 retrieval upper bound | `100 / 100` |
| Direct30 hybrid rerank final answer score | `124 / 150 = 82.7%` |
| Direct30 hybrid rerank Top5 evidence estimate | `140 / 150 = 93.3%` |
| Direct30 diagnosis retrieval ceiling | `77 / 90 = 85.6%` |
| Bad open-question current 5pt upper bound | `56 / 60 = 93.3%` |
| Bad open-question current 3pt ceiling | `34 / 36 = 94.4%` |
