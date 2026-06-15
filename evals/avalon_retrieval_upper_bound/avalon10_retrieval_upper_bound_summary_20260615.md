# Avalon10 Retrieval Upper Bound Summary - 2026-06-15

本次使用 GitHub 上最新 RAG 架構重新跑阿瓦隆資料集，目標是評估 retrieval 的理論上限。

評估方式：

- 不評分 LLM 最終回答。
- 只檢查 final retrieval context 是否包含回答每題所需 evidence。
- 若 context 已包含必要 evidence，假設 Answer Agent 完美時可答對。
- 因此分數代表 retrieval upper bound，不代表實際回答分數。

資料與 index：

```text
RAG_KB_DIR=data/avalon-game-records
RAG_INDEX_DIR=data/index_avalon
```

使用資料：

```text
data/avalon-game-records/avalon-api-game-record-1781013283232-formatted.txt
data/avalon-game-records/avalon-api-game-record-1781013283232.txt
```

## 結果比較

| 模式 | 分數 | 說明 | 報告 |
| --- | ---: | --- | --- |
| RRF parent context retrieval | 29/38 = 76.32% | 最新主 retrieval，不加 structured retrieval，不加 oracle | `avalon10_retrieval_upper_bound_report_20260615-163924.md` |
| RRF + structured result retrieval | 33/38 = 86.84% | 加入既有 event/result structured retrieval，Q9 從 0/4 修到 4/4 | `avalon10_retrieval_upper_bound_report_20260615-164203.md` |
| RRF + structured retrieval + exact round oracle | 38/38 = 100.00% | 評估若明確 `第N輪` metadata filter 做對，retrieval 理論上可達滿分 | `avalon10_retrieval_upper_bound_report_20260615-164414.md` |
| RRF parent context retrieval + strengthened metadata filter | 34/38 = 89.47% | 將 `第N輪 / 第N章 / Step N` 類 sequence filter 納入 BM25 / Dense 前的 Metadata Filter | `avalon10_retrieval_upper_bound_report_20260615-165814.md` |
| Strengthened metadata filter + structured result retrieval | 38/38 = 100.00% | Metadata Filter 解決明確輪次問題；structured retrieval 解決 Q9 result-only 問題 | `avalon10_retrieval_upper_bound_report_20260615-165824.md` |
| Current main flow after structured result retrieval integration | 38/38 = 100.00% | `find_result_constrained_chunks()` 已正式納入 `_rrf_parent_context_results()`，不需 eval-only 開關 | `avalon10_retrieval_upper_bound_report_20260615-170459.md` |

## 主要觀察

1. 補強前，主 RRF retrieval 的直接上限是 76.32%。
2. 補強 Metadata Filter 後，主 RRF retrieval 上限提高到 89.47%。
3. 將 structured result retrieval 正式納入主流程後，目前阿瓦隆 10 題 retrieval upper bound 達到 100%。
4. Query rewrite enabled / disabled 的結果相同，代表主要瓶頸不是 query rewrite，而是 metadata constraint / structured retrieval merge。

## 失分來源

### Q6 明確輪次問題

問題：

```text
第5輪的1、3任務結果是什麼？這對後續判斷有什麼影響？
```

補強前，RRF 主流程抓到第8輪為主，漏掉第5輪任務結果。

診斷：

- `第5輪` 單獨 keyword search 可以正確抓到第5輪。
- 完整問題進入 dense / RRF 後，被 `1、3 任務結果` 拉向第8輪。
- 這代表 retrieval 沒有把 `第5輪` 當作硬 metadata constraint。

修正：

- `_explicit_metadata_filters()` 現在會從問題抽取 `第N輪 / 第N章 / 第N節 / Step N / Chapter N`。
- `_metadata_filter_chunk_embedding_pairs()` 會在 BM25 / Dense 前用 title / parent_title / chapter / section / phase / step 做 hard filter。
- Q6 由 1/4 提升到 4/4。

### Q9 result-only 問題

問題：

```text
如果只看任務結果，4號和5號為什麼會被視為邪惡方？
```

RRF 主流程完全沒有抓到第2輪與第3輪失敗牌 evidence。

補強 Metadata Filter 後，Q9 仍為 0/4，因為問題沒有明確輪次，而是 `只看任務結果` constraint。

將 structured result retrieval 正式納入 `_rrf_parent_context_results()` 後，Q9 可達 4/4。

### Q5 reason evidence 問題

問題：

```text
為什麼後期大家會收斂到1、2、3這組隊伍？
```

這題不能只用統計欄位評估，因為有效 evidence 主要出現在發言與推理理由中，例如：

- 第三輪成功線
- 4、5 同車風險
- 收斂到 1、2、3
- 第四輪成功 / 最後一關

改用 reason-evidence criteria 後，在 oracle 模式可達 4/4。

## 下一步建議

1. 對 `為什麼 / 影響 / 收斂 / 原因` 類問題加入 reason evidence retrieval。
2. 保留 RRF parent context，但持續監控 structured / metadata evidence 前置插入是否造成其他資料集的 precision 下降。
