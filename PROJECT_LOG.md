# RAG Project Log

## 2026-06-02

正式建立 RAG 專案資料夾。

目前已確認：

- RAG 專案會先從流程確認開始，不急著選定最終主題。
- 初期可用強模型建立 baseline，後續再導入本機 / 開源小模型。
- embedding 主要用於資料 chunks 與使用者 input 的相似度檢索。
- 實際回答時，LLM 看到的是被檢索回來的原文 chunks，不是 embedding 本身。
- RAG 不應只靠 embedding，應搭配 keyword search 與 metadata filter。
- Ryan 的本機環境適合使用 Qwen 7B；14B 可測但會慢；32B 以上不建議。
- Multi-Agent 可以用角色分工，不一定要每個 agent 都載入獨立模型。
- 雲端部署是作品集目標之一，用來展示 AI 應用服務化與 API 部署能力。

目前方向：

- 先做本機 RAG MVP。
- 後續部署到雲端展示。
- 保留模型可切換架構。

## 2026-06-02 MVP 範本資料

第一版 RAG 範本資料已決定使用虛構員工手冊：

```text
data/raw/employee_handbook_v1.md
```

此文件刻意採用正式員工手冊語氣，但內部制度與數字設定非常不符合一般常識，例如凌晨 4:00 上班、晚上 20:00 下班、事假一年 90 天且給 1/3 薪、病假一年 300 天且給 2/3 薪、生日當天不可請假且有 200,000 元生日紅包等。

選擇此範本的原因：

- 不綁定保險、金融或特定產業，可作為泛用企業知識庫範例。
- 規則足夠具體，適合測試 RAG 是否真的根據文件回答。
- 內容不容易讓 LLM 只靠常識猜出答案。
- 適合測試來源引用、規則查詢、例外條件、數字檢索與無法確認內容標記。

後續 ingestion、chunking、query、citation 與 verifier 的 baseline 測試，先以此文件作為第一批資料來源。

## 2026-06-02 本機 Qwen RAG MVP

已建立第一版最小可執行 RAG 系統：

- `rag_demo/chunking.py`：讀取 Markdown 並依 `###` 小節切 chunk。
- `rag_demo/index_store.py`：將 chunks 儲存與讀取為 JSON index。
- `rag_demo/ingest.py`：建立 `data/index/chunks.json`。
- `rag_demo/retrieval.py`：以 keyword search 檢索相關 chunks。
- `rag_demo/embeddings.py`：使用 `sentence-transformers` 建立 query 與 chunk embeddings。
- `data/index/embeddings.npy`：本機 embedding matrix。
- `rag_demo/prompting.py`：建立要求根據來源回答的 prompt。
- `rag_demo/ollama_client.py`：呼叫本機 Ollama API。
- `rag_demo/query.py`：CLI 查詢入口。
- `rag_demo/web_app.py`：本機網站入口，使用 Python 標準庫啟動 Web UI。
- `rag_demo/query_rewriter.py`：使用 Qwen system prompt 先做語意理解，再產生向量檢索用查詢。
- `tests/test_rag_pipeline.py`：第一批單元測試。

已確認本機 Ollama 具有以下模型：

```text
qwen2.5:7b
ryan:latest
```

目前預設使用 `qwen2.5:7b`，也可透過 `--model ryan` 或 `RAG_MODEL=ryan` 切換。

已驗證指令：

```bash
python3 -m unittest discover -s tests
python3 -m rag_demo.ingest
python3 -m rag_demo.query '事假一年可以請幾天？事假期間薪水怎麼算？' --model qwen2.5:7b
python3 -m rag_demo.web_app --port 8766
```

最後一次 smoke test 結果：系統正確檢索 `employee_handbook_v1.md / 1.2 事假`，Qwen 回答事假每年最多 90 天，事假期間給付原薪資三分之一，並將無法確認欄位輸出為「無」。

2026-06-02 已升級 retrieval：

- 從 keyword-only baseline 改為 hybrid search。
- hybrid score 組合 keyword score 與 embedding cosine similarity。
- embedding model 預設為 `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`。
- 查詢輸出會顯示總分、keyword score、embedding score，方便觀察 retrieval 行為。
- 已針對「生病請假」與「身體不舒服需要休息」建立測試與實測，top source 會抓到 `1.3 病假`。
- 查詢流程新增 query rewrite：先用 Qwen 依 system prompt step by step 理解使用者問題，再產生比原始問題更適合 embedding 的「向量檢索用查詢」。
- chunks 新增 `parent_title` metadata，embedding 與 retrieval 會納入父層章節，例如 `4. 福利制度`。
- 已針對「公司有什麼福利嗎」實測，改寫後查詢為 `公司福利 生日福利 交通補助 三節獎金`，top 3 來源為生日福利、三節獎金、交通補助。
- 網站與 CLI 預設 `top_k` 從 2 調整為 3，避免 query rewrite 已提到的第三個重要來源未進入回答 context。
- 回答格式第 3 段改為「補充說明 / 無法確認或需要人工確認的部分」，允許模型開放式指出可能需要追加檢索或人工確認的方向，但仍要求不能把推測內容當成已確認答案。
- 回答 prompt 已改為任務單格式：先呈現使用者原始問題，再列出 retrieval chunks，最後列回答規則。retrieval chunks 會包含來源編號、文件、父層章節、章節與內容。
- 新回答規則要求模型逐一檢視每個檢索來源；若多個來源都直接回答問題，答案必須整合所有相關來源，不得只回答第一個來源。
- 「補助」查詢已擴展為福利類查詢，會優先檢索三節獎金、交通補助、生日福利等福利制度項目。

## 2026-06-02 泛用性調整

已移除為員工手冊硬寫的 retrieval 規則，例如病假、事假、福利制度、交通補助、生日福利、遠端工作、離職流程等專用同義詞與 boost。

目前 retrieval 泛用策略：

- query rewrite 仍會讀取當前 knowledge base 的候選章節標題。
- Qwen 產生「向量檢索用查詢」後，系統會做 sanitize。
- sanitize 只保留原始問題詞與候選章節中出現的詞，避免 Qwen 改寫時加入 knowledge base 外的幻想詞。
- keyword / hybrid metadata boost 改為通用 metadata overlap：若 query 詞與 `parent_title` 或 `title` 有重疊，就提高該 chunk 排名。

因此換 knowledge base 時，不需要修改 retrieval 程式裡的領域詞；只要重新 ingestion，候選章節會由新文件自動提供。

## 2026-06-02 Retrieval Verifier Agent

已新增 retrieval confidence check / verifier agent：

```text
使用者問題
→ query rewrite
→ hybrid retrieval
→ verifier agent 檢查問題與 retrieved chunks 是否相關
→ 若無關，直接回答：無正確來源資料
→ 若相關，才進入最後 Qwen 回答
```

新增檔案：

```text
rag_demo/retrieval_verifier.py
```

實測：

- `公司有規定最低學歷嗎`：retrieval chunks 只包含福利結算、遠端工作服裝、外部訪客與正式場合；verifier 判定 `is_related=false`，最終回答 `無正確來源資料`。
- `公司有哪些相關的補助？`：retrieval chunks 包含三節獎金、生日福利、交通補助；verifier 判定 `is_related=true`，進入最後回答。

2026-06-02 調整：

- 若 verifier 判定 retrieval chunks 與問題無關，不再只回 `無正確來源資料`。
- 新流程會回覆 `無法在資料中搜尋到，以下改用一般常識回答：`，再由 Qwen 產生明確標示非 knowledge base 來源的一般常識回答。
- 新增 `rag_demo/general_answer.py`，專門處理無相關來源時的一般常識 fallback prompt。

2026-06-02 query rewrite 漂移修正：

- 發現問題：`公司有規定最低錄取學歷嗎？謊報學歷會怎麼樣` 曾被 Qwen query rewriter 錯誤改寫成 `保密義務`。
- 修正方式：`sanitize_retrieval_query` 現在會檢查改寫後查詢是否保留原問題核心詞。
- 若改寫結果完全沒有保留原問題核心詞，即視為 query drift，改回使用原始問題做 retrieval。
- 實測後該問題不再轉成 `保密義務`，而是保留原問題，並由 verifier 判定 retrieved chunks 無關，再改用一般常識回答。

目前限制：

- 尚未導入 vector database。
- embedding matrix 先以本機 `embeddings.npy` 儲存。
- verifier 目前是獨立 agent call，但仍主要靠 prompt 約束與 JSON parser，尚未加入更嚴格的程式化判斷或人工標註評測集。

## 2026-06-02 目前流程整理與 Agent 隔離

已確認目前 RAG 流程不是把所有任務塞進同一個 prompt，而是使用同一個本機 `qwen2.5:7b` 模型服務，透過不同 prompt / system prompt 做序列式 agent 分工。

目前實際流程：

```text
knowledge base
→ chunking
→ chunks.json
→ embeddings.npy
→ 使用者輸入問題
→ Query Rewriter Agent
→ sanitize retrieval query
→ hybrid retrieval
→ Verifier Agent
→ 若相關：Answer Agent 根據 retrieval chunks 回答
→ 若無關：General Fallback Agent 標示無法在資料中搜尋到，改用一般常識回答
→ 輸出原始問題、向量檢索用查詢、檢索來源、verifier 結果與 Qwen 回答
```

Agent 分工：

- `rag_demo/query_rewriter.py`：Query Rewriter Agent。負責 step by step 語意理解與產生向量檢索用查詢，不回答問題。
- `rag_demo/retrieval_verifier.py`：Verifier Agent。負責驗證使用者問題和 retrieved chunks 的關聯性，輸出 `is_related`、`confidence`、`reason`。
- `rag_demo/prompting.py`：Answer Agent prompt。負責將原始問題與 retrieval chunks 組合成完整 prompt，要求模型只根據來源回答。
- `rag_demo/general_answer.py`：General Fallback prompt。當 knowledge base 沒有相關來源時，明確標示改用一般常識回答。
- `rag_demo/query.py`：主流程 orchestration。負責把 query rewrite、retrieval、verifier、answer / fallback 串起來。

目前架構定義：

```text
同模型，多角色，prompt 隔離，memory 不共享，序列執行
```

不是：

```text
多個 Qwen 7B instance 同時常駐
```

原因：

- Mac M4 / 16GB RAM 適合單一 7B 模型穩定執行。
- 同時常駐多個 7B 會增加 RAM 壓力與延遲，不一定比序列 agent 更快。
- 目前瓶頸主要是多次 Qwen generation，而不是 retrieval 本身。

後續可優化方向：

- 將 query rewrite 改成「規則式優先，必要時才呼叫 Qwen」。
- 將 verifier 改成「retrieval confidence check 優先，灰色地帶才呼叫 Qwen」。
- 保留 Qwen 7B 給最後 Answer Agent。
- 若未來硬體或雲端算力允許，再把前置 agent 換成小模型或獨立模型服務。

## 2026-06-02 文件更新

已將目前本機 RAG MVP 的實際流程、agent 分工、prompt 隔離、無相關來源 fallback、速度瓶頸與後續優化方向同步更新到：

```text
README.md
PROJECT_LOG.md
```

## 2026-06-04 Model Provider 切換

已新增 model provider / model spec 架構，讓同一套 RAG pipeline 可以切換不同回答模型與 API provider。

新增檔案：

```text
rag_demo/model_providers.py
```

目前支援 model spec：

```text
ollama:qwen2.5:7b
ollama:llama3.1:8b
ollama:gemma3:4b
openai:gpt-5.5
anthropic:claude-opus-4-1-20250805
```

舊格式如 `qwen2.5:7b` 仍可使用，系統會自動視為 `ollama:qwen2.5:7b`，避免破壞既有 CLI 與測試。

Provider 行為：

- `ollama:*`：呼叫本機 Ollama `/api/generate`。
- `openai:*`：呼叫 OpenAI Responses API，需要 `OPENAI_API_KEY`。
- `anthropic:*`：呼叫 Anthropic Messages API，需要 `ANTHROPIC_API_KEY`。

已調整：

- `rag_demo/query_rewriter.py` 改用 `ask_model()`。
- `rag_demo/retrieval_verifier.py` 改用 `ask_model()`。
- `rag_demo/query.py` 的 Answer Agent / General Fallback 改用 `ask_model()`。
- `rag_demo/web_app.py` 新增模型輸入欄位，可在網站上直接切換 model spec。
- 輸出標題由 `Qwen 回答` 改為 `模型回答`，避免模型切換後標示不正確。

目前限制：

- 現階段所有 agent 共用同一個 model spec。
- 尚未支援不同 agent 分別指定不同模型，例如 rewrite 用 Gemma、answer 用 OpenAI。
- Embedding model 與 LLM provider 是分開的；更換 embedding model 時仍需重新 ingestion。

已驗證：

```text
python3 -m unittest discover -s tests
Ran 28 tests
OK
```

## 2026-06-10 Knowledge Base 切換為阿瓦隆對局紀錄

已將目前 RAG knowledge base 從第一版虛構員工手冊切換為阿瓦隆對局紀錄。

目前主要資料來源：

```text
data/avalon-game-records/avalon-api-game-record-1781013283232-formatted.txt
```

原始紀錄仍保留：

```text
data/avalon-game-records/avalon-api-game-record-1781013283232.txt
```

已調整：

- `rag_demo/chunking.py` 新增 `chunk_avalon_record_text()`，依 `=== 第N輪 ===` 將阿瓦隆對局紀錄切成 chunks。
- `rag_demo/chunking.py` 新增 `load_knowledge_base_chunks()`，可讀取 Markdown 與阿瓦隆 formatted txt。
- `rag_demo/ingest.py` 目前改讀 `data/avalon-game-records`，並重建 `chunks.json` 與 `embeddings.npy`。
- `rag_demo/query.py` fallback loader 改讀阿瓦隆 knowledge base 目錄。
- `rag_demo/web_app.py` 網站文案與 sample questions 已改為阿瓦隆對局問題。
- `tests/test_rag_pipeline.py` 新增阿瓦隆對局紀錄 chunking 與 loader 測試。

目前 index 狀態：

```text
data/index/chunks.json      8 chunks
data/index/embeddings.npy   已重建
```

前幾個 chunk：

```text
第1輪
第2輪
第3輪
第4輪
第5輪
```

可測問題範例：

```text
誰是梅林？誰是邪惡方？
第1輪隊伍為什麼沒有通過？
哪幾輪任務出現失敗？
刺客最後刺殺了誰？
正義方最後如何收斂到成功隊伍？
```

已驗證：

```text
python3 -m unittest discover -s tests
Ran 30 tests
OK

python3 -m rag_demo.ingest
Index written: data/index/chunks.json
Embeddings written: data/index/embeddings.npy
```

## 2026-06-10 Performance Baseline

已記錄一次 demo 網站實測節點耗時，作為後續優化前後比較基準。

紀錄檔：

```text
docs/performance_log.md
```

本次總耗時：

```text
total: 77.68s
```

主要瓶頸：

```text
verifier: 29.04s
answer_generation: 30.06s
retrieval: 9.98s
query_rewrite: 8.60s
```

初步判斷：

- retrieval 慢點可能來自每次 query 重新載入 embedding model。
- verifier 與 answer generation 慢點來自本機 Qwen 7B 處理較長 retrieved chunks context。
- 下一步優先優化 embedding model cache、retrieval confidence rule、verifier context truncation 與 `max_context_chars`。

## 2026-06-10 Embedding Model Cache 優化

已完成第一個效能優化：快取 `sentence-transformers` embedding model。

變更：

- `rag_demo/embeddings.py` 新增 process-level `_EMBEDDING_MODEL_CACHE`。
- `embed_texts()` 現在透過 `_get_embedding_model()` 取得模型。
- 新增 `clear_embedding_model_cache()` 供測試使用。
- `tests/test_rag_pipeline.py` 新增 fake model factory 測試，確認同一個 model name 只建立一次。

實測：

```text
embed_query_1: 10.79s dim=384
embed_query_2: 0.01s dim=384
```

測試：

```text
python3 -m unittest discover -s tests
Ran 35 tests
OK
```

預期後續網站查詢：

- 第一次 query 仍會載入 embedding model。
- 同一個 server process 的第二次以後 query，retrieval 節點應明顯變快。

2026-06-10 demo 實測結果：

```text
load_index: 0.00s
query_rewrite: 8.32s
load_embeddings: 0.00s
retrieval: 0.26s
verifier: 28.35s
answer_generation: 29.95s
total: 66.88s
```

與 baseline 對比：

```text
retrieval: 9.98s → 0.26s，改善 9.72s
total: 77.68s → 66.88s，改善 10.80s
```

目前主要瓶頸已從 retrieval 轉移到：

```text
verifier: 28.35s
answer_generation: 29.95s
```

## 2026-06-10 Verifier Confidence Gate 優化

已完成第二個效能優化：Verifier Agent confidence gate 與 context truncation。

變更：

- `rag_demo/config.py` 新增 verifier gate 相關環境變數。
- `rag_demo/retrieval_verifier.py` 新增 `assess_retrieval_confidence()`。
- `auto_accept` 改為可選功能，避免 retrieval 高分但來源不足時誤放行。
- retrieval 結果明顯無關時，直接 `auto_reject`，跳過 LLM verifier。
- 預設流程下，非明顯無關的問題仍呼叫原本的 Verifier Agent。
- 真正呼叫 Verifier Agent 時，retrieval chunks 會先截斷，預設每個 chunk 只給前 `600` 字。

新增環境變數：

```text
RAG_VERIFIER_AUTO_ACCEPT_ENABLED
RAG_VERIFIER_AUTO_ACCEPT_SCORE
RAG_VERIFIER_AUTO_REJECT_SCORE
RAG_VERIFIER_MIN_KEYWORD_SCORE
RAG_VERIFIER_MIN_EMBEDDING_SCORE
RAG_VERIFIER_CONTEXT_CHARS
```

測試：

```text
python3 -m unittest discover -s tests
Ran 39 tests
OK
```

預期：

- 明顯無關問題可省掉 verifier call。
- 仍保留一般問題的 verifier，避免過度信任 retrieval 分數。

## 2026-06-10 Verifier Auto Accept 回退

使用者實測：

```text
load_index: 0.00s
query_rewrite: 10.28s
load_embeddings: 0.00s
retrieval: 9.70s
verifier: 0.00s
answer_generation: 32.56s
total: 52.54s
```

問題：

- `verifier: 0.00s` 代表 retrieval confidence gate 直接放行。
- 對阿瓦隆這類需要推理與反證的資料，retrieval 高分不等於 chunk 足以支持答案。
- 實測回答品質變差，因此不能預設跳過 Verifier Agent。

修正：

- `RAG_VERIFIER_AUTO_ACCEPT_ENABLED=false` 作為預設值。
- `auto_accept` 仍保留，但必須明確開啟。
- `auto_reject` 保留，用於明顯無關問題的快速 fallback。

## 2026-06-10 RAG Workflow 參數化優化

參考 Notion 筆記 `RAG workflow` 的文字與圖片重點，將現有 RAG pipeline 加入第一批可調參數。

Notion 筆記重點：

- Data Preprocessing 可調 `chunk_size` 與 `stride`。
- `chunk_size` 越大，每個 chunk 可保留更多上下文，但 retrieval 命中較粗，prompt 也較長。
- `chunk_size` 越小，命中較精準，但可能切斷跨段資訊。
- `stride` 越大，chunk 數量較少、速度較快。
- `stride` 越小，overlap 較多，較不容易漏掉跨 chunk 詞彙，但 ingestion / retrieval 會更久。
- Context window 不應把整份 knowledge base 塞給 LLM，應控制 top N chunks。
- Retrieval 可結合 BM25 / keyword 與 embedding similarity，再做 merge。
- Retrieval chunks 找出後，仍需要 verifier 檢查使用者問題與 chunks 是否相關。

已新增：

```text
rag_demo/config.py
docs/rag_tuning_parameters.md
```

已實作環境變數：

```text
RAG_TOP_K
RAG_CHUNK_SIZE
RAG_CHUNK_STRIDE
RAG_KEYWORD_WEIGHT
RAG_EMBEDDING_WEIGHT
RAG_METADATA_BOOST_MAX
```

已調整：

- `rag_demo/chunking.py`：阿瓦隆對局紀錄可依 `chunk_size / chunk_stride` 將長輪次切成多個 part。
- `rag_demo/retrieval.py`：`hybrid_search()` 支援可調 keyword / embedding 權重與 metadata boost 上限。
- `rag_demo/query.py`：讀取 `RagConfig`，將 retrieval 參數傳入 hybrid search。
- `rag_demo/web_app.py`：網站新增 `top_k` 欄位，demo 時可直接調整 context chunks 數量。
- `tests/test_rag_pipeline.py`：新增 chunk stride、config 與 retrieval weight 測試。

重建後 index 狀態：

```text
chunk_count = 22
原本阿瓦隆每輪 1 chunk，共 8 chunks
現在長輪次會切成第N輪 / part M
```

已驗證：

```text
python3 -m unittest discover -s tests
Ran 33 tests
OK

python3 -m rag_demo.ingest
Index written: data/index/chunks.json
Embeddings written: data/index/embeddings.npy
```
