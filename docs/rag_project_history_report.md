# Three Body RAG Project History Report

日期：2026-06-16

本報告整理《三體》RAG 專案從 MVP、評測、Retrieval 調校，到 V2 Graph Retrieval 增量改造的完整歷程。重點放在 Retrieval Pipeline、評分機制變化、優化數據，以及後續可用於消防法規 RAG 的驗收方法。

## 1. 專案目標

最初目標不是只做一個聊天機器人，而是建立一個可展示、可驗證、可持續優化的 RAG 系統：

- 可讀取本機知識庫與小說文本。
- 可切 chunk、建立 index、建立 embeddings。
- 可用 BM25 / Dense / keyword variants 做 retrieval。
- 可把 retrieval 結果交給本機 Qwen QA Agent 回答。
- 可用題庫、標準答案與評分報告追蹤品質。
- 可拆分 Retrieval 問題與 QA Agent 問題，避免把錯誤原因混在一起。

## 2. 架構演進

### 2.1 MVP Baseline

第一版可執行流程：

```text
data/raw/*
-> rag_demo.ingest
-> data/index/chunks.json
-> data/index/embeddings.npy
-> rag_demo.query / rag_demo.web_app
-> Query Rewriter Agent
-> hybrid search
-> Verifier Agent
-> Answer Agent
-> 回答附檢索來源
```

這一版的價值是讓 ingestion、chunking、embedding、retrieval、QA、source citation 能先跑通。

### 2.2 Retrieval Variants

後續加入多種 retrieval mode 做比較：

- embedding retrieval
- keyword-only retrieval
- hybrid rerank
- Sparse + Dense 實驗方向
- BM25(original question) + Dense(original question)
- RRF merge
- Parent Chunk Expansion

其中最重要的決策是：BM25 / Dense Retrieval 使用原始問題，而不是 rewrite 後的問題。

原因是 Query Rewrite 會改善部分語意表達，但也可能刪掉人物名、派別名、物件名等高召回關鍵詞。後來把 Query Rewrite 定位成輔助訊號，用於 metadata、rerank 或 graph expansion，而不是取代原始問題。

### 2.3 Validated Main Retrieval Workflow

已驗證主流程：

```text
Question
↓
Query Rewrite
↓
Metadata Filter
↓
BM25(original question) + Dense(original question)
↓
RRF Merge
↓
Reranker
↓
Parent Chunk Expansion
↓
Top 8 Context
↓
LLM
```

### 2.4 V2 Graph Retrieval Incremental Upgrade

在不重做現有架構的前提下，加入 Graph Retrieval 能力：

```text
Question
↓
Query Rewrite
↓
Entity Extraction
↓
Metadata Filter
↓
Query Classifier
↓
Graph Retrieval + BM25(original question) + Dense(original question)
↓
Graph / Vector Merge
↓
Reranker
↓
Parent Chunk Expansion
↓
Top 8 Context
↓
LLM
```

已新增元件：

- `rag_demo.graph_entities`
- `rag_demo.query_classifier`
- `rag_demo.graph_store`
- `rag_demo.graph_retrieval`
- `data/graph/three_body_graph.json`
- Graph supporting chunks 與 RRF parent-context retrieval merge

V2 目前是本地 JSON graph 版本，尚未導入 Neo4j、LLM-assisted relation extraction 或 temporal graph。這是刻意的增量改造：先驗證人物、組織、派別、多跳關係題是否受益，再決定是否升級 Graph DB。

## 3. 主要優化項目

| 階段 | 優化 | 解決問題 | 結果 |
| --- | --- | --- | --- |
| MVP | chunking + embeddings + local Qwen | 建立可跑的 RAG baseline | 可本機問答與引用來源 |
| Retrieval variants | embedding / keyword-only / hybrid rerank | 找出哪種 retrieval 對小說文本有效 | keyword-only 與 hybrid 在 Direct30 明顯優於純 embedding |
| Query Rewrite 調整 | BM25/Dense 改用 original question | rewrite 造成人物名、派別名流失 | Retrieval recall 更穩定 |
| F16 類型修正 | 提高人物名 + 答案選項同 chunk 權重 | 人物 + 派別判定容易被泛化內容蓋過 | 申玉菲派別題改善 |
| RRF Merge | 合併 BM25 / Dense 候選 | 提高候選召回 | 保留 lexical precision 與 semantic recall |
| Parent Chunk Expansion | 命中 chunk 後補相鄰 chunk | 答案跨 chunk 或上下文不足 | First20 retrieval upper bound 達 100/100 |
| Metadata Filter | 明確章節 / sequence filter | 特定章節或回合題被其他相似段落干擾 | 提升特定範圍查詢穩定性 |
| Graph Retrieval V2 | Entity / Relation / supporting chunks | 人物關係、組織派別、多跳題只靠 vector 不穩 | 弱開放題 retrieval ceiling 明顯提升 |

## 4. 評分機制演進

### 4.1 初期答案評分

初期使用標準答案與 alias rule 做自動評分。這種方式可重現，但容易過嚴，例如：

- 正確答案是「國立台灣大學」，回答「台大」也應該算對。
- 問題問的是意思，回答不一定要逐字命中 alias。

### 4.2 語意寬鬆評分

後來改成「意思對就可以，表達不完整不扣分」：

- 同義詞、簡稱、等價表達算正確。
- 不因回答短、不漂亮、沒有裝飾性細節扣分。
- 只扣真正語意錯、答非所問、反向回答。

First20 closed semantic rescore：

| 評分方式 | 分數 |
| --- | ---: |
| deterministic alias report | `76 / 100` |
| semantic lenient manual review | `85 / 100` |
| 差異 | `+9` |

### 4.3 Retrieval Upper Bound 評分

為了區分 Retrieval 和 QA Agent 的責任，新增 retrieval upper-bound 測試：

- 不看 LLM 最終回答。
- 只看 Top contexts 是否包含標準答案所需 evidence。
- 如果 Retrieval Upper Bound 高但 QA 分數低，問題多半是 QA Agent 沒用好 evidence。
- 如果 Retrieval Upper Bound 低，才是 retrieval pipeline 需要優化。

### 4.4 Direct30 Failure Diagnosis

Direct30 用 3 criteria scoring 診斷錯誤來源：

- Retrieval ceiling：Top5 context 中理論上可回答多少 criteria。
- Answer score：QA Agent 實際答中多少 criteria。
- QA underused evidence：context 有，但 QA 沒答出。
- Retrieval miss Top5：知識庫有，但 Top5 沒撈到。

這讓我們能明確分辨：

```text
Retrieval 做不好
vs
QA Agent 回答不好
```

## 5. 優化數據

### 5.1 Direct30 Retrieval Mode Comparison

| Mode | Final Answer Score | Top5 Evidence Estimate | Full / Partial / None Evidence |
| --- | ---: | ---: | ---: |
| embedding | `104 / 150 = 69.3%` | `131 / 150 = 87.3%` | `22 / 8 / 0` |
| keyword_only | `116 / 150 = 77.3%` | `141 / 150 = 94.0%` | `25 / 5 / 0` |
| hybrid_rerank | `124 / 150 = 82.7%` | `140 / 150 = 93.3%` | `25 / 4 / 1` |

觀察：

- 純 embedding 對小說中的人名、專有名詞、派別、物件查詢不夠穩。
- keyword-only 的 evidence estimate 很高，表示小說 RAG 中 lexical matching 很重要。
- hybrid_rerank 的最終答案分數最高，表示 retrieval + rerank 對 QA Agent 更友善。

### 5.2 Direct30 Failure Cause Diagnosis

| Mode | Answer Score | Retrieval Ceiling | Retrieval Miss Top5 |
| --- | ---: | ---: | ---: |
| 原本 keyword query + embedding retrieval | `46 / 90 = 51.1%` | `68 / 90 = 75.6%` | `18` |
| 純 keyword retrieval | `52 / 90 = 57.8%` | `76 / 90 = 84.4%` | `14` |
| hybrid rerank 實驗版 | `60 / 90 = 66.7%` | `77 / 90 = 85.6%` | `10` |
| 已切換後的主流程重跑 | `56 / 90 = 62.2%` | `77 / 90 = 85.6%` | `10` |

觀察：

- 原本流程 retrieval ceiling 只有 `75.6%`。
- keyword-only 把 retrieval ceiling 拉到 `84.4%`。
- hybrid rerank / 主流程達到 `85.6%`。
- Retrieval miss Top5 從 `18` 降到 `10`。

### 5.3 First20 Closed Retrieval Upper Bound

在主流程改成 BM25(original question) + Dense(original question)、RRF、Parent Chunk Expansion、Top 8 Context 後：

| 測試 | Retrieval Upper Bound |
| --- | ---: |
| First20 closed | `100 / 100` |
| First20 V2 graph smoke rerun | `100 / 100` |

這代表 First20 這批封閉題，Retrieval 已經能提供完整作答 evidence。後續若 QA Agent 失分，主要就不是 Retrieval 問題。

### 5.4 Bad Open Questions Retrieval Upper Bound

最後挑出之前表現不好的 12 題開放式 Direct30 題目，用當前 V2 retrieval 架構只測 retrieval upper bound。

| 指標 | 舊版 | 目前 |
| --- | ---: | ---: |
| 3pt retrieval ceiling, same weak open set | `27 / 36 = 75.0%` | `34 / 36 = 94.4%` |
| 5pt evidence, known subset | `38 / 45 = 84.4%` | `41 / 45 = 91.1%` |
| Current 5pt upper bound, full selected set | - | `56 / 60 = 93.3%` |

剩餘未滿分：

- `D30Q07`：缺「物理學從來就沒有存在過」這個精確 evidence，現在 `3/5`。
- `D30Q24`：抓到古箏行動、審判日號、三體信息，但缺 `ETO / 地球三體組織資料` criterion，現在 `3/5`。

觀察：

- 弱開放題的 retrieval ceiling 從 `75.0%` 提升到 `94.4%`。
- 剩餘問題是少數精確 evidence 沒進 Top 8，不是整體 retrieval pipeline 崩壞。
- Relation / organization 類問題開始受益於 graph context。

## 6. 目前結論

目前《三體》RAG 專案已達到可收尾狀態：

- 第一集封閉題 retrieval upper bound：`100 / 100`。
- 之前弱開放題 retrieval upper bound：`56 / 60 = 93.3%`。
- Direct30 主流程 retrieval ceiling：`77 / 90 = 85.6%`。
- Direct30 Top5 retrieval miss 從 `18` 降到 `10`。
- 評分標準已從過嚴 alias matching 調整為語意正確導向。
- 已能分辨 retrieval failure 與 QA Agent underuse evidence。
- 已完成 V2 Graph Retrieval 增量版，沒有破壞原本 BM25 + Dense 主線。

## 7. 消防法規 RAG 最後驗收建議

消防法規和小說 RAG 不同，精確性與可引用性更重要。建議最後驗收時照這個順序：

1. 先測 Retrieval Upper Bound，不先看 LLM 回答。
2. 題目要包含：
   - 法條定義題
   - 罰則題
   - 期限 / 數字題
   - 適用條件題
   - 例外條款題
   - 多條文交叉題
3. 評分時分成：
   - Retrieval 是否找到正確法條
   - Context 是否包含完整條件
   - LLM 是否正確引用與解釋
4. 對消防法規，不能只用「意思差不多」；數字、期限、條號、適用條件必須精確。
5. 如果 Retrieval Upper Bound 已高，但回答錯，優化 QA prompt / citation discipline。
6. 如果 Retrieval Upper Bound 不高，優先優化：
   - 法條 metadata
   - 條號 normalization
   - parent section expansion
   - exact keyword / BM25
   - reranker

建議消防法規最終驗收門檻：

| 指標 | 建議門檻 |
| --- | ---: |
| Retrieval Upper Bound | `>= 95%` |
| 正確條號命中率 | `>= 95%` |
| 數字 / 期限正確率 | `>= 98%` |
| LLM final answer score | `>= 90%` |
| 無來源回答率 | `0%` |

## 8. 後續可選優化

短期不一定需要做，但如果要繼續提升：

- 對剩餘 miss 題加入 query-specific diagnostic。
- 對 Graph JSON 加入更多 entity / relation。
- 引入 cross-encoder reranker。
- 對法規資料加條號、章節、施行日期、適用對象 metadata。
- 對消防法規建立「條號 graph」或「條文引用 graph」。

目前建議先保留現有架構，拿消防法規做最後一次 domain transfer 測試；如果法規測試也穩，就可以把這個專案定位為一個完整的 Retrieval-first RAG case study。
