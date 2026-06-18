# RAG Project

Retrieval-first RAG 架構範例。核心目標是把檢索流程拆清楚，讓 knowledge base 可以替換，而不是把特定資料集寫死在程式裡。

## Workflow

```text
Question
↓
Query Rewrite
↓
Metadata Filter
↓
Entity Extraction
↓
Query Classifier
↓
Graph Retrieval + BM25(original question) + Dense(original question)
↓
RRF Merge
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

架構定義在 `rag_demo/rag_architecture.py`。

## Node 功能

| Node | 功能 |
| --- | --- |
| Question | 保留使用者原始問題，避免專名在改寫時遺失。 |
| Query Rewrite | 產生輔助查詢，不取代原始問題。 |
| Metadata Filter | 依文件、章節、類型等 metadata 縮小搜尋空間。 |
| Entity Extraction | 抽取人物、組織、地點、事件與概念。 |
| Query Classifier | 判斷 Content / Relation / Hybrid 問題。 |
| Graph Retrieval | 處理人物關係、組織關係與多跳查詢。 |
| BM25 | 用原始問題做關鍵字檢索，補強專名與精確詞。 |
| Dense Retrieval | 用原始問題做語意檢索，補強同義與長句查詢。 |
| RRF Merge | 合併 BM25 與 Dense 排名，提高 recall。 |
| Graph / Vector Merge | 合併 graph context 與 vector candidates 並去重。 |
| Reranker | 重排候選 chunks，提高 precision。 |
| Parent Chunk Expansion | 補回相鄰 chunks，避免答案被 chunk 邊界切斷。 |
| Top 8 Context | 控制交給 LLM 的 context 數量。 |
| LLM / QA Agent | 只根據檢索內容回答。 |

## 使用方法

安裝依賴：

```bash
python3 -m pip install -r requirements.txt
```

建立 knowledge base profile：

```text
profiles/<profile_name>/
  raw/
  index/
  entities/aliases.json
  graph/graph.json
```

將文件放入：

```text
profiles/<profile_name>/raw/
```

建立 index：

```bash
export RAG_PROFILE=<profile_name>
python3 -m rag_demo.ingest
```

提問：

```bash
export RAG_PROFILE=<profile_name>
python3 -m rag_demo.query '你的問題'
```

指定模型：

```bash
python3 -m rag_demo.query '你的問題' --model ollama:qwen2.5:7b
```

啟動本機網站：

```bash
python3 -m rag_demo.web_app --port 8766
```

開啟：

```text
http://127.0.0.1:8766
```

## 測試結果

| 測試集 | 題數 | 題型 | 評估項目 | 結果 | 題庫 | 報告 |
| --- | ---: | --- | --- | ---: | --- | --- |
| 三體三部曲 Reader 300 | 300 | 簡單題 | Retrieval Upper Bound | `1480 / 1500 = 98.7%` | [JSON](evals/three_body_trilogy/questions_trilogy_300_reader.json) / [Markdown](evals/three_body_trilogy/questions_trilogy_300_reader.md) | [Report](evals/three_body_trilogy/trilogy_300_reader_retrieval_upper_bound_report_20260618-115821.md) |
| GitHub Current25 V2 | 25 | 標準答案題 / 弱開放題 / 純開放題 | Retrieval Upper Bound | `122 / 125 = 97.6%` | [JSON](evals/three_body_qwen/questions_current25_v2_20260616.json) | [Report](evals/three_body_qwen/github_current25_retrieval_upper_bound_report_20260618-120454.md) |

## Knowledge Base 設定

`RAG_PROFILE` 會自動讀取：

```text
profiles/<profile_name>/raw/
profiles/<profile_name>/index/
profiles/<profile_name>/entities/aliases.json
profiles/<profile_name>/graph/graph.json
```

也可以用環境變數覆蓋：

```bash
export RAG_KB_DIR=/path/to/raw
export RAG_INDEX_DIR=/path/to/index
export RAG_ENTITY_ALIASES=/path/to/aliases.json
export RAG_GRAPH_PATH=/path/to/graph.json
```

詳細設定見 `docs/knowledge_base_interface.md`。

## 原則

- BM25 與 Dense 使用原始問題。
- Query Rewrite 只作為輔助訊號。
- Retrieval 先求 recall，再用 reranker 提升 precision。
- Graph 只補關係型與多跳問題，不重寫整套 RAG。
- Knowledge base 透過 profile 切換，核心程式不綁定特定資料集。
