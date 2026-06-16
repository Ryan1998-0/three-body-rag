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
| QA 語意評分（寬鬆） | 評估 LLM 最終回答是否語意正確；同義詞、簡稱、等價表達都算對。 |
| QA 語意評分（嚴謹） | 評估 LLM 是否保留標準答案中的關鍵詞、因果、限制條件或核心表述。 |
| Retrieval Upper Bound | 不看 LLM 回答，只看 Top 8 Context 是否包含標準答案所需 evidence。 |

### Current25 V2 評測

這組評測只保留 25 題：10 題標準答案題、10 題弱開放題、5 題純開放題。評分包含 LLM 最終回答與 Retrieval Upper Bound。

| 題型 | 題數 | QA 寬鬆 | QA 嚴謹 | Retrieval Upper Bound |
| --- | ---: | ---: | ---: | ---: |
| 標準答案題 | 10 | `38 / 50` | `41 / 50` | `47 / 50` |
| 弱開放題 | 10 | `36 / 50` | `25 / 50` | `50 / 50` |
| 純開放題 | 5 | `10 / 25` | `8 / 25` | `25 / 25` |
| 合計 | 25 | `84 / 125 = 67.2%` | `74 / 125 = 59.2%` | `122 / 125 = 97.6%` |

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
