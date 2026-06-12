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

## 2026-06-11 回答品質測試暫停點

本輪繼續測試阿瓦隆 RAG 回答品質，測試問題：

```text
哪幾輪任務出現失敗？
```

目前觀察：

1. 初始測試中，retrieval 把第8輪 `0 失敗` 排在真正 `任務：失敗` 前面，導致 Verifier 誤判為無關並 fallback。
2. Verifier context 原本只保留 chunk 前段，可能漏掉每輪尾端的 `本輪統計 / 任務結果`。
3. 已將 Verifier context 截斷改為 head + tail。
4. 已在 retrieval 加入 failure / success polarity scoring：
   - 問題包含 `失敗` 時，`任務：失敗` 加分。
   - `失敗牌 0 張`、`0失敗`、`無失敗` 等否定失敗的內容扣分。
5. 修正後 retrieval 與 verifier 已改善：

```text
檢索來源：
1. 第2輪 / part 3
2. 第3輪 / part 1
3. 第2輪 / part 2
4. 第3輪 / part 3

Verifier Agent:
is_related=True
confidence=0.9
reason=retrieval chunks 提供了第2輪和第3輪任務失敗的相關資訊，直接支持回答問題。
```

目前剩餘問題：

- Answer Agent 仍只回答第3輪，漏掉第2輪。
- 判斷原因是 answer prompt 將完整 chunk 直接放入，Qwen 7B 可能漏讀多來源中段或尾段重點。

下一步暫停在：

```text
test_render_retrieved_context_surfaces_key_excerpts_before_full_content
```

## 2026-06-11 Context Summary Agent

已在 retrieval 與 Answer Agent 之間加入新的 `Context Summary Agent`。

新流程：

```text
User Question
→ Query Rewriter
→ Hybrid Retrieval
→ Evidence-aware Verifier
→ Context Summary Agent
→ Answer Prompt
→ Answer Agent
```

新增檔案：

```text
rag_demo/context_summary.py
```

調整檔案：

```text
rag_demo/query.py
rag_demo/prompting.py
tests/test_rag_pipeline.py
```

Context Summary Agent 任務：

- 接收使用者提問與 retrieved chunks。
- 先整理 `直接 evidence`、`輔助資訊`、`不足或衝突`。
- 不輸出最終答案。
- 不新增來源沒有的資訊。
- 將彙整結果放入 Answer Prompt 的 `## 彙整資料` 區塊。

Answer Prompt 調整：

- `build_answer_prompt()` 支援 `context_summary`。
- `render_retrieved_context()` 會在完整 chunk 前列出 `關鍵摘錄`。
- 已通過原本刻意保留的紅燈測試：

```text
test_render_retrieved_context_surfaces_key_excerpts_before_full_content
```

測試：

```text
python3 -m unittest discover -s tests
Ran 51 tests
OK
```

第一題實測：

```text
問題：這場對局每位玩家的角色分別是什麼？

Verifier Agent:
is_related=True
confidence=0.9

context_summary: 64.58s
answer_generation: 59.84s
total: 171.49s
```

品質觀察：

- Verifier 仍能正確放行。
- Summary Agent 能整理部分角色資訊。
- 但 Summary Agent / Answer Agent 仍會把具體角色改寫成陣營，例如把 `梅林` 回成 `正義方`。
- 新增一個 Qwen 7B Summary Agent 後，總耗時顯著增加。

下一步建議：

- 不要完全依賴 Qwen 做 summary。
- 將 Summary Agent 改成更 deterministic 的 Evidence Extraction，先用規則 / structured extraction 抽出候選 evidence。
- 對 `A / B`、表格列、key-value、列表等格式，要求直接照抄，不做語意歸類。
- Summary Agent 可以保留，但應優先吃 deterministic evidence，而不是直接摘要整段 chunk。

此測試已先寫好且目前故意失敗，目標是讓 `rag_demo/prompting.py` 在每個來源完整內容前加上「關鍵摘錄」，把 `任務：失敗` 等命中句先浮出來，降低 Answer Agent 漏讀來源的機率。

## 2026-06-11 阿瓦隆 RAG 回答品質評估

已用桌遊專家視角設計 10 個阿瓦隆對局問題，並用目前本機 RAG 流程逐題測試回答品質。

評估文件：

```text
docs/answer_quality_eval_2026-06-11.md
```

評分標準：

- Retrieval：3 分
- Grounding：3 分
- Correctness：3 分
- Clarity：1 分
- 每題滿分 10 分

10 題平均分數：

```text
5.44 / 10
```

主要觀察：

1. Verifier false negative 是目前最大問題之一。多題已抓到正確 chunk，但 Verifier 判定不相關並導致 fallback。
2. Query Rewriter 有時會 over-expand，把太多輪次與數字塞進 retrieval query，污染 keyword score。
3. Answer Agent 在多來源題目中會漏讀部分來源，例如只回答第3輪，漏掉第2輪。
4. General fallback 邊界太寬，曾把阿瓦隆刺殺問題回答成現實歷史刺殺，這是高風險 hallucination。
5. 數字語意會混淆，例如 `6號玩家` 被 retrieval 誤連到 `第6輪`。

下一步優先修正：

1. 在 Answer prompt 中加入每個 chunk 的「關鍵摘錄」。
2. 收緊 General fallback：若問題仍屬於 knowledge base 主題，但來源不足，不要改用一般常識。
3. 改善 Verifier prompt，降低 direct evidence 被誤判不相關的機率。
4. 限制 Query Rewriter 過度展開。
5. 區分輪次數字與玩家座位數字。

## 2026-06-11 Evidence-aware Verifier 優化

已將 Verifier 從單純判斷 `is_related`，升級為 evidence-aware verifier。

核心調整：

- Verifier system prompt 改為「驗證 retrieval chunks 是否包含足夠 evidence 回答使用者問題」。
- Verifier prompt 要求模型先找 evidence，再判斷 `is_answerable`。
- 新 JSON schema：

```json
{
  "is_answerable": true,
  "confidence": 0.0,
  "evidence_spans": ["直接支持答案的原文片段"],
  "missing_info": [],
  "reason": "簡短原因"
}
```

- Parser 保留向下相容：舊的 `is_related` JSON 仍可解析。
- `render_verifier_context()` 新增通用 `evidence 候選` 區塊。
- `extract_evidence_candidates()` 會抽取短標題、括號標籤、條列、Markdown 表格列、key-value 行等結構化 evidence。

這是泛用優化，不是為阿瓦隆硬寫規則。目標是讓 Verifier 能辨識：

- 標題
- metadata
- 表格列
- 列表
- key-value 行
- 角色標籤 / 代號標籤
- 結構化欄位

第一題回歸測試：

```text
問題：這場對局每位玩家的角色分別是什麼？

優化前：
Verifier Agent:
is_related=False
reason=retrieval chunks 主要內容為阿瓦隆遊戲對局紀錄，未提及玩家角色分配。

優化後：
Verifier Agent:
is_related=True
confidence=0.9
reason=提供了每位玩家的角色資訊，可以回答問題。
```

目前剩餘問題：

- Verifier 已能放行第一題。
- Answer Agent 仍未完整使用 evidence，將 `API AI 2 / 派西維爾` 回答成「好人」，將 `API AI 4 / 莫德雷德` 回答成「邪惡方」。
- 下一步仍是實作 Answer prompt 的「關鍵摘錄」機制，也就是目前故意保留的紅燈測試：

```text
test_render_retrieved_context_surfaces_key_excerpts_before_full_content
```

## 2026-06-11 移除主流程 Summary Agent，改用 deterministic evidence

背景：

- Context Summary Agent 能改善部分 answer prompt 長度，但在本機 Qwen 7B 上速度成本很高。
- 實測中 `context_summary` 曾花費約 50-60 秒。
- Summary Agent 也曾漏掉結構化 evidence，導致 Answer Agent 只回答部分角色。

本次調整：

- 主流程不再呼叫 Qwen Summary Agent。
- retrieval 後改由程式執行 deterministic evidence extraction。
- `【A / B】`、key-value、列表、表格列等結構化 evidence 由程式抽取。
- `【A / B】` 這類身份 / 角色 / 對照 label 會排在 evidence 最前面。
- Answer Prompt 有 `context_summary` 時不再放入完整 retrieval chunks，只放程式整理後的 evidence。
- Summary Agent 相關函式保留在 `rag_demo/context_summary.py`，但不作為 demo 主流程預設節點。

第一題回歸測試：

```text
問題：這場對局每位玩家的角色分別是什麼？

節點耗時：
- load_index: 0.00s
- query_rewrite: 6.06s
- load_embeddings: 0.00s
- retrieval: 10.94s
- verifier: 27.83s
- deterministic_evidence: 0.00s
- answer_generation: 11.67s
- total: 56.51s

模型回答：
- API AI 1：梅林
- API AI 2：派西維爾
- API AI 3：忠臣
- API AI 4：莫德雷德
- API AI 5：刺客
```

品質判斷：

- 通過。
- deterministic evidence 完整抽出五位玩家角色。
- 移除 Summary Agent 後，總耗時約從 121.97s 降到 56.51s。
- 目前最大耗時仍是 Verifier Agent 與 Answer Generation。

## 2026-06-11 deterministic evidence before Verifier

背景：

- 第二題「第一個任務失敗是第幾輪？隊伍是誰？誰出了失敗牌？」前一版失敗原因是 Verifier false negative。
- Retrieval 已抓到第2輪正確 chunk，但 Verifier 判定 `is_related=False`，導致流程直接 fallback。
- 因為 deterministic evidence extraction 原本在 Verifier 後面，所以 Verifier 誤殺時完全用不到。

本次調整：

- 將 deterministic evidence extraction 移到 Verifier 前面。
- Verifier prompt 新增 `deterministic evidence` 區塊。
- Verifier 會先看程式抽出的 evidence，再看原始 retrieval chunks。
- 即使 Verifier 判定失敗，輸出也會顯示 deterministic evidence，方便 debug。

第二題回歸測試：

```text
問題：第一個任務失敗是第幾輪？隊伍是誰？誰出了失敗牌？

優化前：
Verifier Agent:
is_related=False
reason=retrieval chunks 中沒有提供足夠的資訊來回答問題。

優化後：
Verifier Agent:
is_related=True
confidence=0.9
reason=找到了莫德雷德在第3輪出失敗牌的 evidence，以及相關投票資訊。
```

新的問題：

- Verifier 不再 false negative，但 Answer Agent 仍混淆第2輪與第3輪。
- deterministic evidence 目前依 retrieval 排序，第3輪排在第2輪前面。
- 題目問「第一個」時，需要新增 chronology-aware evidence ordering，讓第2輪 evidence 排在第3輪前面。

本次測試分數：

```text
Retrieval: 2.5 / 3
Grounding: 1.0 / 3
Correctness: 1.0 / 3
Clarity: 0.4 / 1
Total: 4.9 / 10
```

結論：

- deterministic evidence before Verifier 有效改善 Verifier false negative。
- 下一步應處理 chronological ordering / first-event reasoning，而不是再加入 Summary Agent。

## 2026-06-12 Chronology-aware deterministic evidence

背景：

- 第二題在 `deterministic evidence before Verifier` 後，Verifier 可放行，但 Answer Agent 仍混淆第2輪與第3輪。
- 原因是 retrieval 排名將第3輪放在第2輪前面。
- 題目問「第一個任務失敗」，需要按照事件時間排序，而不是只按照 retrieval score 排序。

本次調整：

- `build_deterministic_context_summary()` 支援傳入使用者問題。
- `extract_deterministic_evidence()` 變成 query-aware：
  - 若問題包含 `第一個`、`第一次`、`最早`、`最先`、`首次`，會根據 chunk title 中的 `第N輪` 做 chronology-aware ordering。
  - 若問題包含任務 / 隊伍 / 出任務 / 失敗牌 / 成功牌，任務結果欄位會排在角色標籤前面。
  - dedup 改為排序後再執行，避免較晚輪次先佔走同一句 evidence，例如 `任務：失敗，邪惡方得分`。

另外新增 deterministic verifier gate：

- 若 deterministic evidence 已同時包含：
  - `任務：失敗`
  - `出任務者`
  - `失敗牌`
- 則 Verifier 直接 auto-accept，不再呼叫 Qwen Verifier。

第二題回歸測試：

```text
問題：第一個任務失敗是第幾輪？隊伍是誰？誰出了失敗牌？

Verifier Agent:
is_related=True
confidence=0.95
reason=deterministic_evidence: task result fields directly support the answer

節點耗時：
- query_rewrite: 7.20s
- retrieval: 10.84s
- deterministic_evidence: 0.00s
- verifier: 0.00s
- answer_generation: 11.74s
- total: 29.78s

模型回答：
第一個失敗任務發生在第2輪。
隊伍是 API AI 2 和 API AI 4。
API AI 4 出了失敗牌。
```

新評分：

```text
Retrieval: 2.5 / 3
Grounding: 3.0 / 3
Correctness: 3.0 / 3
Clarity: 0.9 / 1
Total: 9.4 / 10
```

結論：

- 第二題由 4.9 / 10 提升到 9.4 / 10。
- Verifier 耗時由約 32-39 秒降為 0 秒。
- 這是泛用優化：對「第一個 / 最早」與結構化任務結果欄位都有效。

## 2026-06-12 泛用性檢查與 evidence policy 抽象化

使用者要求先檢查目前優化是否為阿瓦隆客製化，再進行泛用優化。

檢查結果：

- 文件、測試資料、demo UI 中出現阿瓦隆名詞是可接受的，因為目前 knowledge base 是阿瓦隆對局紀錄。
- 核心邏輯中不應直接依賴阿瓦隆角色或固定答案。
- 本次發現的偏資料集規則主要有：
  - deterministic evidence ordering 使用 `第N輪`。
  - evidence priority 使用 `任務 / 出任務者 / 失敗牌 / 投票 / 贊成 / 反對`。
  - Verifier gate 使用 `任務：失敗 + 出任務者 + 失敗牌`。
  - retrieval polarity scoring 使用 `任務：成功 / 任務：失敗 / 失敗牌 0 張`。

本次泛用化：

- 新增 `rag_demo/evidence_policy.py`。
- 將 evidence 規則抽象成：
  - `temporal_order`：是否需要時間 / 序列排序。
  - `event_or_result_question`：是否在問事件結果 / 狀態。
  - `asks_participant`：是否在問人員 / 成員 / 負責者 / 隊伍。
  - `asks_outcome_detail`：是否在問失敗、成功、原因、責任、明細。
  - `asks_vote`：是否在問投票、支持、反對。
- `sequence_number()` 不只支援 `第N輪`，也支援：
  - `第N章`
  - `第N節`
  - `第N步`
  - `Phase N`
  - `Step N`
  - `Chapter N`
- Verifier deterministic gate 改為檢查「結構化事件欄位是否足以回答」，不再只看固定阿瓦隆欄位。
- Retrieval polarity scoring 改為泛用 outcome polarity：
  - `結果：失敗`
  - `狀態：失敗`
  - `判定：成功`
  - `處理狀態：成功`
- 新增 evidence role filter：
  - 如果問題沒有問投票 / 支持 / 反對，就不把 `投票 / 贊成 / 反對` 放進 Answer evidence。
  - 這避免模型把投票者誤當成隊伍成員或負責人。

第二題回歸：

```text
問題：第一個任務失敗是第幾輪？隊伍是誰？誰出了失敗牌？

回答：
第一個任務失敗是第2輪。
隊伍是 API AI 2 和 API AI 4。
API AI 4 出了失敗牌。

節點耗時：
- deterministic_evidence: 0.00s
- verifier: 0.00s
- total: 30.45s
```

測試：

```text
python3 -m unittest discover -s tests
Ran 65 tests
OK
```

結論：

- 目前優化已從阿瓦隆欄位規則提升為泛用 evidence policy。
- 後續仍可針對 Q3 / Q9 的 Query Rewriter over-expansion 與 evidence retrieval 策略做泛用改善。

## 2026-06-12 Entity existence / number disambiguation

本輪開始優化 Q3 / Q9 / Q10，先處理最泛用、最明確的 Q10。

問題：

```text
這場對局有6號玩家參與嗎？
```

舊問題：

- Retrieval 會被 `第6輪` 影響。
- Verifier 判定無關後進入 fallback。
- 回答沒有根據來源中的玩家 entity evidence。

本次調整：

- 新增 `rag_demo/entity_resolution.py`。
- 新增 `parse_entity_existence_query()`：
  - 可解析 `N號X` 這類 entity existence 問題。
  - 例如 `6號玩家`、`3號客戶`、`2號設備`。
- 新增 `extract_entity_numbers()`：
  - 從 deterministic evidence 的 entity label 抽出 entity number。
  - 會忽略來源標籤中的 section / sequence number，例如 `第6輪`。
- 新增 `answer_entity_existence()`：
  - 若 evidence 已足夠確認 entity 集合，直接回答是否存在。
  - 不再呼叫 Verifier / Answer Agent / general fallback。

Q10 回歸測試：

```text
Verifier Agent:
is_related=True
confidence=0.95
reason=entity_resolution: structured entity evidence answered existence question

節點耗時：
- deterministic_evidence: 0.00s
- entity_resolution: 0.00s
- total: 22.97s

模型回答：
無法從來源確認有6號玩家參與。
目前來源中的玩家編號只有：1、2、3、4、5。
```

新評分：

```text
Retrieval: 1.5 / 3
Grounding: 3.0 / 3
Correctness: 3.0 / 3
Clarity: 1.0 / 1
Total: 8.5 / 10
```

結論：

- Q10 從 3.5 / 10 提升到 8.5 / 10。
- 這是泛用優化，可處理 `N號玩家`、`N號客戶`、`N號設備` 與章節 / 輪次數字混淆問題。
- 下一步建議處理 Q3 的 `event_list retrieval`，避免 Query Rewriter over-expansion。

## 2026-06-12 Event-list retrieval

本輪繼續優化 Q3。

問題：

```text
哪幾輪任務出現失敗？各是哪位玩家出失敗牌？
```

舊問題：

- Query Rewriter 仍會 over-expand，例如加入 `第1輪至第8輪 / part 1 4`。
- 一般 top-k hybrid retrieval 會被污染，抓到非核心 chunks。
- Q3 需要的是「列出所有符合條件的事件」，不是只找最相似的幾個 chunks。

本次調整：

- 新增 `rag_demo/event_list_retrieval.py`。
- 新增 `find_event_list_chunks()`：
  - 若問題符合 `event_list + event_or_result_question`，掃描全部 chunks。
  - 只匹配真正 result/status 欄位，例如 `狀態：失敗`、`任務：失敗`、`結果：異常`。
  - 不再把 `失敗牌 0 張`、`失敗項目 0 個` 這類 detail row 誤判為失敗事件。
- 新增 `merge_event_list_chunks()`：
  - 將 structured event matches 放在一般 retrieval results 前面。
  - 保留原 retrieval results 作為補充。
- `query.py` 在 hybrid retrieval 後新增 `event_list_retrieval` 節點。

Q3 回歸測試：

```text
問題：哪幾輪任務出現失敗？各是哪位玩家出失敗牌？

檢索來源前段：
1. 第2輪 / part 2
2. 第2輪 / part 3
3. 第3輪 / part 3

Verifier Agent:
is_related=True
confidence=0.95
reason=deterministic_evidence: structured event fields directly support the answer

節點耗時：
- event_list_retrieval: 0.00s
- deterministic_evidence: 0.00s
- verifier: 0.00s
- total: 28.06s

模型回答：
第二輪和第三輪任務出現失敗。
- 第二輪：API AI 4
- 第三輪：API AI 5
```

新評分：

```text
Retrieval: 2.8 / 3
Grounding: 3.0 / 3
Correctness: 3.0 / 3
Clarity: 0.9 / 1
Total: 9.7 / 10
```

結論：

- Q3 從 1.5 / 10 提升到 9.7 / 10。
- Query Rewriter 仍會 over-expand，但 event-list retrieval 能補救這類「列出所有符合條件事件」的問題。
- 這是泛用優化，可用於事件紀錄、客服案件、流程狀態、任務結果、錯誤清單等資料。

## 2026-06-12 Constraint-aware result evidence filtering

本輪繼續優化 Q9。

問題：

```text
如果只看任務結果，4號和5號為什麼會被視為邪惡方？
```

舊問題：

- 使用者明確限制「只看任務結果」，但 retrieval / answer 仍混入投票、角色標籤、私下思考與一般發言。
- 一般 hybrid retrieval 會抓到第1輪投票、第4輪發言、第5輪發言、第8輪發言等非核心 chunks。
- Answer Agent 可能用非任務結果的資料補理由，違反問題限制。

本次調整：

- `EvidencePolicy` 新增 `result_only`：
  - 偵測 `只看任務結果`、`只根據事件結果`、`only use result` 等 constraint。
  - 在 result-only 模式下，只保留 result / participant / outcome-detail 類結構化 evidence。
  - 排除角色標籤、一般敘述、思考內容與非必要投票欄位。
- `event_list_retrieval.py` 新增 `find_result_constrained_chunks()`：
  - 當問題明確要求只看結果時，掃描全部 chunks 中的結構化結果欄位。
  - 若問題有 `4號`、`5號` 這類 target entity，優先保留結果 evidence 中提到 target 的 chunks。
  - 若問題 scope 是 `任務結果`，則優先匹配任務、隊伍、成功牌、失敗牌等 task-result 欄位。
- `query.py` 調整 retrieval merge：
  - 若 result-only constrained retrieval 已命中，後續 summary / answer 只使用 constrained chunks。
  - 不再把一般 vector retrieval 的雜訊合併進 answer prompt。

Q9 回歸測試：

```text
檢索來源：
1. 第2輪 / part 3
2. 第3輪 / part 3

Verifier Agent:
is_related=True
confidence=0.95
reason=deterministic_evidence: structured event fields directly support the answer

彙整資料重點：
- 第2輪：任務失敗，出任務者 API AI 2、API AI 4，失敗牌 API AI 4
- 第3輪：任務失敗，出任務者 API AI 1、API AI 3、API AI 5，失敗牌 API AI 5

節點耗時：
- query_rewrite: 8.69s
- retrieval: 8.79s
- event_list_retrieval: 0.00s
- deterministic_evidence: 0.00s
- verifier: 0.00s
- answer_generation: 12.98s
- total: 30.47s
```

新回答摘要：

```text
4號在第2輪任務中出了失敗牌，導致任務失敗，邪惡方得分。
5號在第3輪任務中出了失敗牌，導致任務失敗。
因此若只看任務結果，4號和5號會被視為邪惡方。
```

新評分：

```text
Retrieval: 3.0 / 3
Grounding: 3.0 / 3
Correctness: 2.8 / 3
Clarity: 0.9 / 1
Total: 9.7 / 10
```

結論：

- Q9 從 2.8 / 10 提升到 9.7 / 10。
- 這是泛用優化，不依賴阿瓦隆角色表；可套用到任務紀錄、事件紀錄、案件結果、流程狀態與測試報告。
- 後續可把 constraint 擴充成更多 evidence scopes，例如 `只看投票結果`、`只看錯誤紀錄`、`只看 metadata`。

## 2026-06-12 Current architecture 10 題重測

使用目前最新架構重新測試 10 題阿瓦隆 RAG 問題。

詳細紀錄：

```text
docs/answer_quality_eval_2026-06-12_current_architecture.md
```

測試模型：

```text
ollama:qwen2.5:7b
```

總分：

```text
平均 7.32 / 10
```

逐題分數：

| 題號 | 分數 |
| --- | ---: |
| Q1 | 9.9 |
| Q2 | 9.8 |
| Q3 | 9.7 |
| Q4 | 3.6 |
| Q5 | 8.1 |
| Q6 | 3.6 |
| Q7 | 3.6 |
| Q8 | 6.4 |
| Q9 | 9.7 |
| Q10 | 8.8 |

已明顯改善：

- Q1 角色抽取已可完整回答五位玩家角色。
- Q2 第一個失敗任務可正確回答第2輪、隊伍與失敗牌。
- Q3 event-list retrieval 可找出所有任務失敗輪次。
- Q9 result-only constraint 可限制答案只使用任務結果 evidence。
- Q10 entity existence 可正確判斷沒有 6 號玩家。

本輪發現的主要退化：

- `entity_resolution` 過度觸發。
- Q4 / Q6 / Q7 中的 `第1輪`、`第5輪`、`第6輪` 被誤判為 entity existence 類問題。
- 導致流程直接跳過 Answer Agent，輸出類似 `可以確認有1號第參與` 的錯誤答案。

下一步優先修正：

1. `parse_entity_existence_query()` 只應在問題明確包含 `N號玩家 / N號客戶 / N號設備` 等 entity phrase 時觸發。
2. 明確排除 `第N輪 / 第N章 / 第N節 / 第N步`。
3. entity resolution 只處理 `有沒有 / 是否有 / 參與嗎 / 存在嗎` 等 existence 問題。
4. Q8 需要新增 action-result distinction，避免把 `刺殺座位 5` 誤推論成 `刺殺成功`。

## 2026-06-12 Entity parser 與 action-result 修正

本輪修正 current architecture 10 題重測中發現的兩個明確問題。

### 1. Entity resolution 過度觸發

根因：

- `parse_entity_existence_query()` 中原本有過寬 fallback regex：

```text
文字 + 數字
```

- 這會把 `第1輪` 解析成：

```text
entity_type = 第
target_number = 1
target_label = 1號第
```

- 因此 Q4 / Q6 / Q7 被誤判為 entity existence 問題，流程直接跳過 Answer Agent。

修正：

- 移除過寬 fallback。
- 只保留明確 entity phrase，例如 `6號玩家`。
- 英文只接受明確 `player 6 / customer 3 / device 2` 類型。
- 排除 `第 / 輪 / 章 / 節 / 步 / 天 / 次 / 回合 / 階段` 等 sequence 詞。

回歸：

- Q4 不再被誤判，已可正確回答第1輪投票：
  - 2 贊成，3 反對。
  - 贊成：API AI 1、API AI 2。
  - 反對：API AI 3、API AI 4、API AI 5。
- Q6 / Q7 不再被 entity_resolution 截胡。
- Q10 `6號玩家` 仍維持正確回答。

### 2. Action-result distinction

根因：

- Q8 來源只明確寫出：

```text
刺殺：刺殺座位 5
```

- 但 Answer Agent 把其他任務成功欄位誤推論成 `刺殺成功`。

修正：

- 新增 `rag_demo/action_result_resolution.py`。
- 新增 `answer_action_result()`：
  - 若問題問某動作是否成功。
  - 且 evidence 只確認動作發生，沒有明確寫出該動作成功。
  - 則由 deterministic layer 直接回答，不交給 Answer Agent 推論。

Q8 修後實測：

```text
Verifier Agent:
is_related=True
confidence=0.95
reason=action_result_resolution: action evidence found but success result is not explicit

模型回答：
來源可確認刺殺：刺殺座位 5。但無法從來源確認刺殺是否成功。
```

測試：

```text
python3 -m unittest discover -s tests
Ran 78 tests
OK
```

剩餘問題：

- Q6 / Q7 雖然不再回答錯題，但「為什麼 / 影響」類問題仍回答偏短。
- 下一步可做泛用 `reason evidence extraction`，讓系統在 deterministic structured evidence 外，額外抽取短因果句、發言理由與決策依據。

## 2026-06-12 修正後 10 題重測

修正 `entity_resolution` 與 `action_result_resolution` 後，重新完整測試 10 題。

詳細紀錄：

```text
docs/answer_quality_eval_2026-06-12_current_architecture.md
```

平均分數：

```text
8.51 / 10
```

逐題分數：

| 題號 | 分數 |
| --- | ---: |
| Q1 | 9.4 |
| Q2 | 9.8 |
| Q3 | 9.7 |
| Q4 | 9.5 |
| Q5 | 5.1 |
| Q6 | 8.3 |
| Q7 | 7.1 |
| Q8 | 9.9 |
| Q9 | 7.5 |
| Q10 | 8.8 |

已確認修復：

- Q4：不再被 `entity_resolution` 誤攔，能正確回答第1輪投票結果。
- Q8：不再把 `刺殺座位 5` 誤推論成刺殺成功。
- Q10：仍可正確回答沒有 6 號玩家。

新觀察：

- Q5 這次明顯波動，Query Rewriter 將「後期大家為什麼收斂到 1、2、3」偏向第3輪，導致 retrieval / answer 沒有抓完整後期脈絡。
- Q9 retrieval 正確抓到第2輪、第3輪，但 Answer Agent 只回答 4 號，漏掉 5 號。

下一步泛用優化方向：

1. `target completeness check`：
   - 問題同時問多個 target，例如 `4號和5號`。
   - 系統應檢查答案是否覆蓋所有 target。
   - 若 deterministic evidence 已有每個 target 的資料，可直接產生結構化回答。
2. `reason evidence extraction`：
   - 當問題包含 `為什麼 / 影響 / 原因 / 收斂` 時，不只抽 key-value，也抽短因果句、決策理由與發言理由。
3. Query Rewriter 對抽象原因題需要降溫，避免過度改寫到局部輪次。

## 2026-06-12 Generic RAG core audit and refactor

使用者要求檢查並移除核心流程中為目前阿瓦隆 knowledge base 客製化的部分，讓整份 RAG 專案以泛用架構為核心。

檢查結果：

- 阿瓦隆資料、10 題測試與評估文件可以保留，作為 demo / evaluation set。
- 核心 pipeline 不應綁定阿瓦隆資料夾、阿瓦隆 UI 文案或固定 `API AI / 玩家 / 任務牌 / 失敗牌` 類 matching。

本次調整：

- `rag_demo/config.py`
  - 新增 `resolve_project_path()`。
  - 支援 `RAG_KB_DIR` 切換 knowledge base 目錄。
  - 支援 `RAG_INDEX_DIR` 切換 index / embeddings 目錄。
- `rag_demo/ingest.py`
  - 不再直接寫死 `data/avalon-game-records`。
  - 預設仍使用目前 demo data，但可由環境變數切換。
- `rag_demo/query.py`
  - 查詢流程同樣改用 `RAG_KB_DIR` 與 `RAG_INDEX_DIR`。
- `rag_demo/chunking.py`
  - 新增 generic `chunk_sectioned_text()`。
  - `chunk_avalon_record_text()` 只保留為 demo wrapper，底層使用 generic section parser。
  - `load_knowledge_base_chunks()` 可讀一般 `.txt`，若有 `=== Section ===` 格式則切 section，否則用 plain text chunk。
- `rag_demo/event_list_retrieval.py`
  - result-only retrieval 不再依賴固定 `API AI / 玩家`。
  - 支援 generic numbered labels，例如 `Agent 4`、`Service 5`、`player 3`、`4號`。
  - `X 結果` scope 由使用者問題抽取，不再固定 `任務結果` 對應阿瓦隆欄位。
- `rag_demo/evidence_policy.py`
  - result/outcome aliases 補入英文 `result / status / outcome / failed / completed / error`。
- `rag_demo/web_app.py`
  - UI label 從 `阿瓦隆對局問題` 改成 `Knowledge base question`。
  - sample questions 改成泛用 knowledge base 問題。

新增測試：

- generic sectioned text chunking。
- `RAG_KB_DIR` path override。
- generic numbered target matching。
- web UI 不再顯示阿瓦隆專用文案。

設計結論：

- 阿瓦隆現在只是目前 demo knowledge base，不再是核心 pipeline 的假設。
- 後續如果換成員工手冊、客服紀錄、小說、研究筆記或流程紀錄，核心 ingestion / query / retrieval 流程都能沿用。

## 2026-06-12 泛用核心重構後 10 題重測

完成 generic RAG core refactor 後，使用目前泛用架構重新測試 10 題阿瓦隆 evaluation questions。阿瓦隆在本輪只作為測試資料集，執行時用環境變數指定：

```text
RAG_KB_DIR=data/avalon-game-records python3 -m rag_demo.query "<question>" --model ollama:qwen2.5:7b --top-k 4
```

詳細紀錄：

```text
docs/answer_quality_eval_2026-06-12_current_architecture.md
```

逐題分數：

| 題號 | 分數 |
| --- | ---: |
| Q1 | 9.9 |
| Q2 | 9.8 |
| Q3 | 9.7 |
| Q4 | 9.3 |
| Q5 | 1.9 |
| Q6 | 8.2 |
| Q7 | 7.1 |
| Q8 | 9.9 |
| Q9 | 9.8 |
| Q10 | 8.8 |

平均分數：

```text
8.44 / 10
```

本輪結論：

- 泛用核心重構沒有破壞主要 deterministic evidence 能力。
- Q1 / Q2 / Q3 / Q8 / Q9 / Q10 表現穩定，能處理角色、任務結果、動作結果區分、多 target 與 entity existence 題。
- Q5 是目前最大弱點：抽象原因題被 Query Rewriter 改寫偏移，retrieval 沒抓到足夠後期脈絡，Verifier 判定不相關後進入 general fallback。
- Q6 / Q7 回答可用但偏短，代表「為什麼 / 影響 / 原因」類問題需要比 key-value evidence 更豐富的 reason evidence。

下一步泛用優化方向：

1. `reason evidence extraction`：對 `為什麼 / 影響 / 原因 / 收斂` 類問題抽取短因果句、決策理由句、時間線脈絡。
2. `in-domain fallback guard`：如果問題仍屬於當前 knowledge base 主題，只是 retrieval 不足，應回答「資料不足以確認」，不要直接改用一般常識。
3. `Query Rewriter guardrail`：避免將抽象原因題過度改寫成局部 keyword，造成 retrieval 偏移。
