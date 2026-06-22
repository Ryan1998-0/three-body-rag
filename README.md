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

### 評測歷程

原本的 `Reader 300` 題庫主要用讀者式簡單題測 retrieval，上限很高，但題型相對單一。後續重新設計 `Mixed 200`，把問題改成混合型，包含直接題、弱開放題、長句描述題與使用者視角改寫題，更接近真實提問。

`Reader 300` 和 `Mixed 200` 的差異：

| 題庫 | 目的 | 題型特徵 | 適合觀察 |
| --- | --- | --- | --- |
| Reader 300 | 檢查基本事實檢索是否穩定 | 讀者式簡單題，較接近原文措辭，答案多為明確人物、事件或名詞 | 基礎 retrieval 是否接近滿分 |
| Mixed 200 | 模擬真實使用者提問 | 混合直接題、弱開放題、長句、短搜尋句、遠離原文措辭與新手問法 | 檢索詞表是否能補足用詞落差 |

| 測試集 | 題數 | 評估項目 | 結果 | 題庫 | 報告 |
| --- | ---: | --- | ---: | --- | --- |
| 三體三部曲 Reader 300 | 300 | Retrieval Upper Bound | `98.7%` | [JSON](evals/three_body_trilogy/questions_trilogy_300_reader.json) / [Markdown](evals/three_body_trilogy/questions_trilogy_300_reader.md) | [Report](evals/three_body_trilogy/trilogy_300_reader_retrieval_upper_bound_report_20260618-115821.md) |
| 三體三部曲 Mixed 200 原版 | 200 | Retrieval Upper Bound | `73.6%` | [JSON](evals/three_body_trilogy/questions_trilogy_mixed200_20260620-045105.json) / [Markdown](evals/three_body_trilogy/questions_trilogy_mixed200_20260620-045105.md) | [Report](evals/three_body_trilogy/mixed200_retrieval_upper_bound_report_20260620-045105.md) |
| 三體三部曲 Mixed 200 附檢索詞表 | 200 | Retrieval Upper Bound | `87.6%` | [JSON](evals/three_body_trilogy/questions_trilogy_mixed200_20260620-052704.json) / [Markdown](evals/three_body_trilogy/questions_trilogy_mixed200_20260620-052704.md) | [Report](evals/three_body_trilogy/mixed200_retrieval_upper_bound_report_20260620-052704.md) |

### Mixed 200 題型

`Mixed 200` 由 50 個三體三部曲事實點產生，每個事實點設計 4 種問法：

| 維度 | 類型 |
| --- | --- |
| Answer Style | `factoid` / `open_ended` |
| Prompt Style | `direct` / `with_premise` |
| Length Style | `concise_natural` / `verbose_natural` / `short_search_query` / `long_search_query` |
| Phrasing | `document_similar` / `document_distant` |
| User Level | `expert` / `novice` |

這批題目刻意加入 `document_distant` 與 `long_search_query`，例如使用者不直接說「星環集團」，而是問「第三部裡商業組織如何成為逃亡技術研發平台」。這類問題可以測出 retrieval 是否能把使用者說法對齊到 knowledge base 原文詞彙。

### 檢索詞表方式

附檢索詞表版本加入 KB-aware vocabulary alignment：

1. 由三體三部曲內容整理 profile 詞表：[aliases.json](profiles/three_body_trilogy/entities/aliases.json)。
2. 詞表包含 `canonical`、`aliases`、`related_terms`、`triggers`。
3. BM25 與 Dense 仍使用原始問題，但在查詢前用 profile 詞表補齊原文主詞。
4. 補詞只存在 knowledge base profile，不寫死在核心 pipeline；更換 knowledge base 時可替換詞表。

範例：

```text
原始問題：
如果問第三部裡商業組織如何成為逃亡技術研發平台，應該查哪個集團？

詞表補齊：
星環集團、維德、程心、光速飛船、曲率驅動
```

加入檢索詞表前後重點數據：

| 指標 | 原版 | 附檢索詞表 |
| --- | ---: | ---: |
| 總分 | `73.6%` | `87.6%` |
| 滿分題 | `105/200` | `141/200` |
| Open-ended | `64.4%` | `85.0%` |
| Long query | `57.6%` | `89.6%` |

### QA Agent 1000 題比較

這組測試把 `Reader 300` 與 `Mixed 200` 分別用「原版」和「附檢索詞表」各跑一次，總共 1000 次 QA Agent 問答。Retrieval Upper Bound 是主要觀察指標；QA 分數只用來輔助判斷 LLM 是否善用已檢索到的 context。

| 測試集 | 題數 | Retrieval Upper Bound | QA Agent | 報告 |
| --- | ---: | ---: | ---: | --- |
| Reader 300 原版 | 300 | `1480/1500 = 98.7%` | `1260/1500 = 84.0%` | [Report](evals/three_body_trilogy/qa_agent_comparison/qa_agent_comparison_report_full-20260620-135227.md) |
| Reader 300 附檢索詞表 | 300 | `1480/1500 = 98.7%` | `1245/1500 = 83.0%` | [Report](evals/three_body_trilogy/qa_agent_comparison/qa_agent_comparison_report_full-20260620-135227.md) |
| Mixed 200 原版 | 200 | `736/1000 = 73.6%` | `572/1000 = 57.2%` | [Report](evals/three_body_trilogy/qa_agent_comparison/qa_agent_comparison_report_full-20260620-135227.md) |
| Mixed 200 附檢索詞表 | 200 | `876/1000 = 87.6%` | `616/1000 = 61.6%` | [Report](evals/three_body_trilogy/qa_agent_comparison/qa_agent_comparison_report_full-20260620-135227.md) |

結論：`Reader 300` 因為題目簡單且接近原文，原版本來就接近 retrieval 滿分；`Mixed 200` 更接近真實使用者問題，加入檢索詞表後 Retrieval Upper Bound 從 `73.6%` 提升到 `87.6%`，提升 `14.0` 個百分點。

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
