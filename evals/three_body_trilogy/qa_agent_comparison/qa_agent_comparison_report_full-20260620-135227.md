# QA Agent Comparison

- Run ID: `full-20260620-135227`
- Model: `ollama:qwen2.5:7b`
- Raw JSONL: `evals/three_body_trilogy/qa_agent_comparison/qa_agent_comparison_raw_full-20260620-135227.jsonl`
- Elapsed Seconds This Session: `101312.21`

本報告比較 `Reader 300` 與 `Mixed 200` 在原版檢索與附檢索詞表檢索下的差異。主要觀察指標是 Retrieval Upper Bound；QA Score 僅作為 QA Agent 是否善用 context 的參考。

`Reader 300` 是讀者式簡單題，題目更接近原文措辭，適合檢查基本 fact retrieval。`Mixed 200` 是混合型真實提問測試，包含直接題、弱開放題、長句、短搜尋句、遠離原文措辭與新手問法，較能測出檢索詞表是否補足用詞落差。

## Summary

| Variant | Questions Done | QA Score | QA % | Retrieval Upper Bound | Retrieval % | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Mixed 200 原版 | 200 | `572/1000` | `57.2%` | `736/1000` | `73.6%` | 5 |
| Mixed 200 附檢索詞表 | 200 | `616/1000` | `61.6%` | `876/1000` | `87.6%` | 13 |
| Reader 300 原版 | 300 | `1260/1500` | `84.0%` | `1480/1500` | `98.7%` | 2 |
| Reader 300 附檢索詞表 | 300 | `1245/1500` | `83.0%` | `1480/1500` | `98.7%` | 2 |

## Delta

| Pair | QA Delta | Retrieval Delta |
| --- | ---: | ---: |
| Reader 300 原版 -> Reader 300 附檢索詞表 | `-1.0 pp` | `0.0 pp` |
| Mixed 200 原版 -> Mixed 200 附檢索詞表 | `4.4 pp` | `14.0 pp` |

## Error Records

- `Reader 300 原版` `TB1-009`: timeout: timed out
- `Reader 300 原版` `TB3-015`: timeout: timed out
- `Reader 300 附檢索詞表` `TB3-015`: timeout: timed out
- `Reader 300 附檢索詞表` `TB3-071`: timeout: timed out
- `Mixed 200 原版` `MIX-TB1-08-V3`: timeout: timed out
- `Mixed 200 原版` `MIX-TB1-10-V1`: timeout: timed out
- `Mixed 200 原版` `MIX-TB1-10-V3`: timeout: timed out
- `Mixed 200 原版` `MIX-TB2-02-V4`: timeout: timed out
- `Mixed 200 原版` `MIX-TB3-01-V2`: timeout: timed out
- `Mixed 200 附檢索詞表` `MIX-TB1-02-V1`: timeout: timed out
- `Mixed 200 附檢索詞表` `MIX-TB1-10-V2`: timeout: timed out
- `Mixed 200 附檢索詞表` `MIX-TB2-01-V2`: timeout: timed out
- `Mixed 200 附檢索詞表` `MIX-TB2-02-V4`: timeout: timed out
- `Mixed 200 附檢索詞表` `MIX-TB3-02-V2`: timeout: timed out
- `Mixed 200 附檢索詞表` `MIX-TB1-12-V4`: timeout: timed out
- `Mixed 200 附檢索詞表` `MIX-TB2-12-V2`: timeout: timed out
- `Mixed 200 附檢索詞表` `MIX-TB2-12-V3`: timeout: timed out
- `Mixed 200 附檢索詞表` `MIX-TB2-12-V4`: timeout: timed out
- `Mixed 200 附檢索詞表` `MIX-TB2-13-V1`: timeout: timed out
- `Mixed 200 附檢索詞表` `MIX-TB2-13-V2`: timeout: timed out
- `Mixed 200 附檢索詞表` `MIX-TB2-13-V3`: timeout: timed out
- `Mixed 200 附檢索詞表` `MIX-TB2-13-V4`: timeout: timed out
