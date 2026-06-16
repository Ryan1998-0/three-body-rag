# Simulated Questions and Answers

本文件只保留目前 README 對應的 Current25 V2 評測檔案。README 只顯示 workflow、使用方式與測試結果摘要；完整題目、LLM 回答與逐題評分放在這裡連結。

## Current25 V2 Evaluation

| File | Description |
| --- | --- |
| [questions_current25_v2_20260616.json](../evals/three_body_qwen/questions_current25_v2_20260616.json) | 第一集 Current25 題庫：10 題標準答案題、10 題弱開放題、5 題純開放題 |
| [current25_v2_raw_answers_20260616-100016.jsonl](../evals/three_body_qwen/current25_v2_raw_answers_20260616-100016.jsonl) | LLM 原始回答、retrieved contexts 與 scoring trace |
| [current25_v2_scored_report_20260616-100016.md](../evals/three_body_qwen/current25_v2_scored_report_20260616-100016.md) | Current25 寬鬆 QA、嚴謹 QA 與 Retrieval Upper Bound 詳細報告 |

## Evaluation Summary

| 題型 | 題數 | QA 寬鬆 | QA 嚴謹 | Retrieval Upper Bound |
| --- | ---: | ---: | ---: | ---: |
| 標準答案題 | 10 | `38 / 50` | `41 / 50` | `47 / 50` |
| 弱開放題 | 10 | `36 / 50` | `25 / 50` | `50 / 50` |
| 純開放題 | 5 | `10 / 25` | `8 / 25` | `25 / 25` |
| 合計 | 25 | `84 / 125 = 67.2%` | `74 / 125 = 59.2%` | `122 / 125 = 97.6%` |
