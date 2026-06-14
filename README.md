# Ryan RAG Project

建立日期：2026-06-02  
狀態：本機 RAG MVP 已可執行 / 持續優化中

## 專案目標

建立一個可展示、可部署、可持續優化的 RAG 專案，作為 Ryan 的 AI / 金融科技 / 資料科學作品集之一。

此專案目標不是單純做聊天機器人，而是建立一套能夠：

- 讀取文件與知識資料
- 切分 chunk
- 建立 embedding
- 進行檢索
- 根據來源生成回答
- 標記無法驗證內容
- 記錄查詢與回答品質
- 未來可部署到雲端展示

的完整 AI 應用流程。

## 目前決策

### 1. 模型策略

先用強模型建立 baseline，再用小模型接手優化。

- 開發初期：使用強模型驗證 RAG 流程是否正確。
- 成本優化期：導入本機或開源小模型，例如 Qwen。
- 展示期：保留模型可切換能力，支援 API 模型與本機 / 開源模型。

原因：

- 一開始最重要的是確認 RAG pipeline 正確，不要被小模型能力不足干擾判斷。
- 強模型可作為上限 baseline。
- 小模型可用於成本優化、工具調用、分類、摘要與輕量任務。

### 2. Embedding 策略

RAG 需要將兩邊轉成 embedding：

- 資料庫內容：文件清理後切成 chunks，每個 chunk 轉成 embedding 並存入向量資料庫。
- 使用者 input：使用者問題轉成 query embedding，用來比對資料庫中的 chunk embeddings。

但回答時，LLM 看的不是 embedding，而是檢索回來的原文 chunk。

建議採用：

- embedding search
- keyword search
- metadata filter

組成 hybrid search，避免只靠向量搜尋漏掉精準資訊，例如姓名、案號、日期、維修單號、錯誤碼。

### 3. 第一版技術組合

MVP 建議：

- Python
- sentence-transformers 或 OpenAI embedding API
- ChromaDB / Qdrant / Supabase pgvector
- OpenAI / Gemini API 作為初期回答模型
- 後續可替換為 Qwen 本機或雲端開源模型

若以最快 Demo 為目標：

- OpenAI text-embedding-3-small
- ChromaDB
- GPT / Gemini 作為回答模型

若以本機開源方向為目標：

- Qwen 7B 作為主要本機模型
- 小模型負責分類、搜尋 query 產生、工具路由

### 4. Multi-Agent 分工想法

使用多 agent 分工，但不一定要同時載入多個模型。可以讓多個 agent 共用同一個模型服務，用不同 prompt、角色與工具權限來分工。

建議分工：

- Router Agent：判斷問題類型、是否需要搜尋、要派給誰，可用規則或小模型。
- Search Agent：產生搜尋 query、調用搜尋工具、整理搜尋結果，可用 1.5B / 3B 小模型或規則流程。
- Summary Agent：壓縮搜尋結果與文件內容，可用 3B / 7B。
- Answer Agent：根據檢索內容產生最後回答，建議用 7B 或強模型。
- Verifier Agent：檢查回答是否根據來源、是否有 hallucination，重要任務可用強模型。

本機 Mac M4 16GB 的實際建議：

- 最佳甜蜜點：Qwen 7B。
- 可挑戰上限：Qwen 14B Q4 量化版，但會慢。
- 不建議：32B 以上。
- 可以有 3~4 個 agent，但建議共用模型並排隊執行，不要同時讓 3~4 個 7B 長時間推理。

### 5. 雲端部署展示方向

Ryan 想部署到雲端的理由：

- 不只是展示 AI Demo。
- 也要展示雲端部署、API 串接與服務化能力。

建議架構：

```text
Frontend: Vercel
Backend API: FastAPI on Render / Railway / Fly.io
Vector DB: Qdrant Cloud / Supabase pgvector / Chroma
Model Provider: OpenAI / Gemini / Hugging Face / Local open-source model
Logs: Supabase / SQLite / JSON logs
```

作品集可呈現為：

```text
Cloud-native RAG Demo:
可部署、可追蹤、可切換模型的 AI 知識助理
```

### 6. 小模型工具調用

小模型可以調用搜尋工具，但最好不要讓小模型完全自由行動。

建議流程：

```text
使用者問題
→ 小模型判斷是否需要搜尋
→ 輸出結構化 JSON
→ 程式呼叫搜尋 API
→ 搜尋結果回傳給小模型
→ 小模型摘要或回答
```

小模型適合：

- 判斷是否需要搜尋
- 產生搜尋關鍵字
- 分類任務
- 初步摘要
- 工具路由

不建議一開始讓小模型處理過度自由、多步驟、長 context 的複雜 agent 任務。

## RAG 基本流程

```text
資料來源
→ 資料清理
→ 切 chunk
→ 加 metadata
→ 建立 embedding index
→ 使用者問題轉 embedding
→ hybrid search
→ rerank
→ 組成 context
→ LLM 回答
→ 驗證與引用來源
→ 記錄 log 與錯誤案例
```

## 第一版 MVP 範圍

先做小而完整的版本：

1. 讀取一批本機 Markdown / PDF / 作業文件。
2. 清理文字。
3. 切 chunk。
4. 建立 embedding。
5. 存入向量資料庫。
6. 使用者輸入問題。
7. 檢索相關 chunk。
8. 回答時附來源。
9. 標記：
   - 資料中明確有的內容
   - AI 推論的內容
   - 無法確認的內容

## 目前本機 RAG MVP

第一版已建立最小可執行流程：

```text
data/raw/*
→ rag_demo.ingest
→ data/index/chunks.json
→ data/index/embeddings.npy
→ rag_demo.query / rag_demo.web_app
→ Query Rewriter Agent
→ hybrid search
→ Verifier Agent
→ Answer Agent / General Fallback
→ 回答附檢索來源
```

目前版本使用 hybrid search：

```text
keyword search + embedding cosine similarity
```

現階段尚未導入 vector database，embedding matrix 先以本機 `embeddings.npy` 儲存。這樣可以先確認 RAG 流程、chunking、citation、embedding retrieval 與本機 Qwen 回答是否能跑通。

目前預設回答模型是本機 Ollama 的 `qwen2.5:7b`。現行架構是「同一個 7B 模型，多個 agent 角色」，每個 agent 透過獨立 prompt / system prompt 執行，沒有把所有任務塞進同一個 prompt，也沒有共用 conversation memory。

目前 RAG core 預設讀取泛用 knowledge base 目錄：

```text
data/raw/*
```

也可以用環境變數切換資料來源，例如使用阿瓦隆 evaluation dataset：

```bash
RAG_KB_DIR=data/avalon-game-records python3 -m rag_demo.ingest
```

泛用 loader 支援 Markdown、一般 `.txt`，以及 `=== Section ===` 這類 sectioned text。事件型資料可使用 `chunk_sectioned_record_text()`，適合對局紀錄、事故處理、客服案件、審核流程、會議決議等分段紀錄。阿瓦隆對局紀錄只是目前 demo / evaluation 資料，不是核心 pipeline 的假設。

之後跑測試請使用：

```bash
python scripts/run_tests_with_record.py
```

測試結果會自動寫入 `test-records/`。

### Model Provider 切換

目前已新增 model provider / model spec 架構，讓 RAG pipeline 可以切換不同回答模型。

支援格式：

```text
ollama:qwen2.5:7b
ollama:llama3.1:8b
ollama:gemma3:4b
openai:gpt-5.5
anthropic:claude-opus-4-1-20250805
```

若使用舊格式：

```text
qwen2.5:7b
```

系統會自動視為：

```text
ollama:qwen2.5:7b
```

目前 provider 支援：

- `ollama:*`：呼叫本機 Ollama `/api/generate`。
- `openai:*`：呼叫 OpenAI Responses API，需要設定 `OPENAI_API_KEY`。
- `anthropic:*`：呼叫 Anthropic Messages API，需要設定 `ANTHROPIC_API_KEY`。

CLI 範例：

```bash
python3 -m rag_demo.query '請根據目前 knowledge base 回答重點內容有哪些？' --model ollama:qwen2.5:7b
python3 -m rag_demo.query '哪些章節提到失敗、異常或風險？' --model ollama:llama3.1:8b
python3 -m rag_demo.query '資料中有哪些來源可以支持這個結論？' --model ollama:gemma3:4b
python3 -m rag_demo.query '這個問題能不能從資料中確認？' --model openai:gpt-5.5
python3 -m rag_demo.query '請整理相關來源並回答使用者問題。' --model anthropic:claude-opus-4-1-20250805
```

網站表單也已新增模型輸入欄位，可以直接輸入 model spec。

注意：這裡切換的是回答 / agent 用的 LLM。Embedding model 是另一件事；如果更換 embedding model，必須重新執行 `rag_demo.ingest` 建立新的 `embeddings.npy`。

### 可調參數

目前已依 Notion `RAG workflow` 筆記加入第一批可調參數：

```text
RAG_TOP_K
RAG_CHUNK_SIZE
RAG_CHUNK_STRIDE
RAG_KEYWORD_WEIGHT
RAG_EMBEDDING_WEIGHT
RAG_METADATA_BOOST_MAX
```

詳細說明見：

```text
docs/rag_tuning_parameters.md
```

### 安裝依賴

```bash
python3 -m pip install -r requirements.txt
```

### 建立 index

```bash
python3 -m rag_demo.ingest
```

此指令預設讀取 `data/raw/*`，並輸出：

```text
data/index/chunks.json
data/index/embeddings.npy
```

若要改用其他 knowledge base：

```bash
RAG_KB_DIR=data/avalon-game-records python3 -m rag_demo.ingest
```

可調整 chunk size / stride 後重建 index：

```bash
RAG_CHUNK_SIZE=1800 RAG_CHUNK_STRIDE=900 python3 -m rag_demo.ingest
```

### 使用 Qwen 查詢

```bash
python3 -m rag_demo.query '請根據目前 knowledge base 回答重點內容有哪些？'
```

預設使用：

```text
ollama:qwen2.5:7b
```

也可以指定模型：

```bash
python3 -m rag_demo.query '第1輪隊伍為什麼沒有通過？' --model ollama:qwen2.5:7b
```

或用環境變數切換：

```bash
RAG_MODEL=ollama:qwen2.5:7b python3 -m rag_demo.query '哪幾輪任務出現失敗？'
```

也可以調整 retrieval 權重：

```bash
RAG_TOP_K=4 RAG_KEYWORD_WEIGHT=0.45 RAG_EMBEDDING_WEIGHT=0.55 \
python3 -m rag_demo.query '第1輪隊伍為什麼沒有通過？' --model ollama:qwen2.5:7b
```

### 啟動本機網站

```bash
python3 -m rag_demo.web_app --port 8766
```

開啟：

```text
http://127.0.0.1:8766
```

網站會讀取目前的 JSON index，送出問題後呼叫本機 Ollama `qwen2.5:7b` 回答。
如果已建立 `data/index/embeddings.npy`，網站查詢會使用 hybrid search。

目前 query 流程：

```text
使用者原始問題
→ Query Rewriter Agent
   - 根據 system prompt 做 step by step 語意理解
   - 產生「向量檢索用查詢」
   - sanitize，避免 query drift 到無關章節
→ Retrieval
   - 對 chunks 做 keyword + embedding hybrid search
   - 顯示 score / keyword_score / embedding_score
→ Verifier Agent
   - 驗證原始問題和 retrieval chunks 是否真的相關
   - 若無關，走一般常識 fallback
→ Prompt Formatting
   - 將原始問題與 retrieval chunks 組合成完整 prompt
→ Answer Agent
   - 只根據 retrieval chunks 回答
   - 可列來源，但不強制固定 1/2/3 格式
→ Output
   - 顯示原始問題、向量檢索用查詢、檢索來源、Verifier 結果、Qwen 回答
```

### Agent 分工與 prompt 隔離

目前使用同一個 `qwen2.5:7b` 模型服務，但任務已切成獨立 agent call：

```text
Query Rewriter Agent
→ retrieval query 改寫，不回答使用者問題

Verifier Agent
→ 判斷問題和 retrieved chunks 是否相關，不回答使用者問題

Answer Agent
→ 只根據 retrieval chunks 回答

General Fallback Agent
→ 當 verifier 判斷 knowledge base 沒有相關來源時，明確標示改用一般常識回答
```

這是：

```text
同模型，多角色，prompt 隔離，memory 不共享，序列執行
```

不是：

```text
多個 Qwen 7B instance 同時常駐
```

在 Mac M4 / 16GB RAM 上，這比同時載入多個 7B 更穩定。若未來要提升速度，可考慮讓 query rewrite / verifier 改由規則或更小模型處理，讓 Qwen 7B 專心做最後回答。

目前所有 agent 會共用同一個 model spec。未來可再升級為：

```text
rewrite_model = ollama:gemma3:4b
verifier_model = ollama:qwen2.5:7b
answer_model = openai:gpt-5.5
fallback_model = anthropic:claude-opus-4-1-20250805
```

### 無相關來源處理

若使用者問題和 knowledge base 無關，例如資料中沒有提到某個不存在的對象或外部規則細節，流程會：

```text
retrieval 找到低相關 chunks
→ Verifier Agent 判斷 is_related=false
→ 不把低相關 chunks 硬塞給 Answer Agent
→ 回答「無法在資料中搜尋到，以下改用一般常識回答」
```

這可以避免模型把相似但無關的 chunks 誤當成答案來源。

### 執行測試

```bash
python3 -m unittest discover -s tests
```

目前測試涵蓋：

- Markdown chunking
- keyword retrieval ranking
- prompt source grounding
- index JSON round trip
- query rewrite prompt
- query drift sanitize
- hybrid retrieval
- verifier prompt / parser
- general answer fallback
- `/ask` refresh path
- model provider parsing
- OpenAI / Anthropic API payload shape
- website model input

## 待辦清單

- [x] 決定第一批資料來源。
- [x] 建立資料夾結構。
- [ ] 選擇 embedding model。
- [ ] 選擇 vector database。
- [x] 寫 ingestion script。
- [x] 寫 query script。
- [x] 設計回答格式。
- [x] 加入來源引用。
- [x] 加入簡單 verifier。
- [ ] 建立測試問題集。
- [ ] 記錄 baseline 結果。
- [ ] 規劃雲端部署架構。

## 下一步建議

先建立最小資料集，不要一開始做太大。

建議第一個實作目標：

```text
本機文件 RAG MVP
→ 可以讀資料
→ 可以查資料
→ 可以回答並附來源
→ 可以說明哪些內容無法驗證
```

完成後再擴充到：

- 作業輔助 RAG
- 個人履歷 / 自我介紹 RAG
- 金融文件 / 理賠文件 RAG
- 可部署雲端 Demo
