# Three Body RAG

這是一個 Retrieval-first 的 RAG 專案，用來測試與優化 V2 檢索架構。核心技術包含 BM25、Dense Retrieval、RRF、Reranker、Parent Chunk Expansion 與 Graph Retrieval。

## 工作流

```text
問題
↓
查詢改寫（Query Rewrite）
↓
實體抽取（Entity Extraction）
↓
Metadata Filter
↓
問題分類器（Query Classifier）
↓
Graph Retrieval + BM25（原始問題）+ Dense（原始問題）
↓
Graph / Vector Merge
↓
Reranker
↓
Parent Chunk Expansion
↓
Top 8 Context
↓
LLM / QA Agent
```

## 架構重點

- BM25 和 Dense Retrieval 都使用原始問題。
- Query Rewrite 只作為輔助訊號，不取代原始問題。
- Graph Retrieval 用來補強人物、組織、派別、事件與多跳問題的關係證據。
- Graph 結果會先轉回 supporting chunks，再和 vector candidates 合併。
- RRF 用來合併 BM25 與 Dense 的 ranked lists。
- Reranker 會重排合併後的候選 chunks。
- Parent Chunk Expansion 會補同一段落附近的 chunks。
- 最後使用 Top 8 Context 交給 LLM / QA Agent 回答。

每一步詳細說明：

- [V2 Retrieval Workflow Steps](docs/v2_workflow_steps.md)

GraphRAG 增量優化路線：

- [GraphRAG Incremental Upgrade Roadmap](docs/graphrag_incremental_roadmap.md)

## 如何使用

安裝依賴：

```bash
python3 -m pip install -r requirements.txt
```

從 `data/raw/*` 建立 index：

```bash
python3 -m rag_demo.ingest
```

提問：

```bash
python3 -m rag_demo.query '申玉菲在地球三體組織中屬於哪一派？'
```

指定模型：

```bash
python3 -m rag_demo.query '古箏行動的核心做法是什麼？' --model ollama:qwen2.5:7b
```

啟動本機網站：

```bash
python3 -m rag_demo.web_app --port 8766
```

開啟：

```text
http://127.0.0.1:8766
```

執行測試：

```bash
python3 -m unittest discover -s tests
```

## 測試結果

### 指標說明

| 指標 | 代表意思 |
| --- | --- |
| QA 語意評分 | 評估 QA Agent 最後回答是否語意正確；同義詞、簡稱、等價表達都算對。 |
| Retrieval Upper Bound | 不看 LLM 回答，只看 retrieved contexts 是否包含標準答案所需 evidence。 |
| Top5 Evidence Estimate | 估算 Top 5 retrieved chunks 是否足以支撐標準答案。 |
| Retrieval Ceiling | 用 criteria / alias rule 計算 retrieval 理論最高可得分，用來判斷問題是否出在 retrieval。 |
| 弱開放題 Upper Bound | 針對過去表現不好的開放式題目，重新測目前架構的 retrieval 上限。 |
| Unit tests | 程式層級測試，確認 ingestion、retrieval、graph、query pipeline 等功能沒有破壞。 |

### 結果摘要

| 評測 | 目的 | 結果 |
| --- | --- | ---: |
| First20 封閉題 QA 語意評分 | 測 QA Agent 最終回答品質 | `85 / 100` |
| First20 Retrieval Upper Bound | 測封閉題 retrieval 是否找到完整 evidence | `100 / 100` |
| Direct30 hybrid rerank 最終回答分數 | 測開放題 QA Agent 回答品質 | `124 / 150 = 82.7%` |
| Direct30 hybrid rerank Top5 Evidence Estimate | 測開放題 Top5 chunks evidence 覆蓋率 | `140 / 150 = 93.3%` |
| Direct30 diagnosis Retrieval Ceiling | 診斷 retrieval 理論上限 | `77 / 90 = 85.6%` |
| 弱開放題 current 5pt Upper Bound | 測過去弱題在目前架構下的 retrieval 上限 | `56 / 60 = 93.3%` |
| 弱開放題 current 3pt Ceiling | 用 3 criteria 口徑和舊版比較 | `34 / 36 = 94.4%` |
| Unit tests | 確認程式功能正常 | `149 tests OK` |

評測檔案與模擬問答輸出：

- [Simulated Questions and Answers](docs/simulated_questions_and_answers.md)

## 模型 Provider

支援的 model spec 範例：

```text
ollama:qwen2.5:7b
ollama:llama3.1:8b
ollama:gemma3:4b
openai:gpt-5.5
anthropic:claude-opus-4-1-20250805
```

Model provider 控制的是 LLM / Agent 使用的模型。如果更換 embedding model，需要重新執行 `rag_demo.ingest` 建立新的 index。
