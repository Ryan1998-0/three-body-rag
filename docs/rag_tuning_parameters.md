# RAG Tuning Parameters

更新日期：2026-06-10

本文件整理目前 RAG pipeline 可調參數，參考 Notion 筆記 `RAG workflow` 的重點：

- Data Preprocessing：`chunk_size`、`chunk_stride`
- Retrieval：BM25 / keyword search 與 embedding similarity 的 hybrid merge
- Context Window：放入 LLM 的 top N chunks
- Instruction Formatting：使用者問題 + retrieval chunks + 回答規則
- Verifier：檢查使用者問題與 retrieved chunks 是否相關

## 目前已實作參數

| 參數 | 環境變數 | 預設值 | 作用 | 什麼時候調大 | 什麼時候調小 |
| --- | --- | ---: | --- | --- | --- |
| `top_k` | `RAG_TOP_K` | `3` | 最後放入 LLM context 的 chunks 數量 | 回答漏掉重要片段 | prompt 太長、速度太慢、回答變散 |
| `chunk_size` | `RAG_CHUNK_SIZE` | `1800` | ingestion 時每個 chunk 最大字元數 | 需要保留較完整上下文 | retrieval 命中太粗、LLM prompt 太長 |
| `chunk_stride` | `RAG_CHUNK_STRIDE` | `900` | 長文本切 chunk 時每次往前移動的字元數 | 想減少 chunk 數量、加快 ingestion / retrieval | 想增加 overlap，避免答案跨 chunk 被切斷 |
| `keyword_weight` | `RAG_KEYWORD_WEIGHT` | `0.3` | hybrid score 中 keyword/BM25 類分數權重 | 問題常含精確詞、座位號、任務輪次、人名 | 語意問法較多，關鍵字不穩 |
| `embedding_weight` | `RAG_EMBEDDING_WEIGHT` | `0.7` | hybrid score 中 embedding similarity 權重 | 使用者常用語意改寫提問 | embedding 抓到語意相近但錯誤的 chunk |
| `metadata_boost_max` | `RAG_METADATA_BOOST_MAX` | `0.18` | title / parent_title 命中時最多加分 | 問題常直接問第幾輪或章節名 | metadata 讓不相關章節過度升分 |
| `verifier_auto_accept_enabled` | `RAG_VERIFIER_AUTO_ACCEPT_ENABLED` | `false` | 是否允許高分 retrieval 直接跳過 LLM verifier | demo 只追求速度且題型很穩定 | 問題需要推理、反證或來源嚴格驗證 |
| `verifier_auto_accept_score` | `RAG_VERIFIER_AUTO_ACCEPT_SCORE` | `0.52` | 啟用 auto accept 後，top chunk 分數高於此門檻且有強 keyword/embedding 訊號時跳過 LLM verifier | verifier 太慢且 retrieval 分數穩定 | verifier 誤放行不相關 chunks |
| `verifier_auto_reject_score` | `RAG_VERIFIER_AUTO_REJECT_SCORE` | `0.15` | top chunk 分數過低且無 keyword / embedding 訊號時，直接 fallback | 無關問題很多 | fallback 太容易被觸發 |
| `verifier_min_keyword_score` | `RAG_VERIFIER_MIN_KEYWORD_SCORE` | `8` | auto accept 需要的最低 keyword 訊號 | 精確詞很可靠 | keyword 容易誤命中 |
| `verifier_min_embedding_score` | `RAG_VERIFIER_MIN_EMBEDDING_SCORE` | `0.35` | auto accept 需要的最低 embedding 訊號 | 語意檢索很可靠 | embedding 容易抓到相似但錯誤 chunks |
| `verifier_context_chars` | `RAG_VERIFIER_CONTEXT_CHARS` | `600` | 真正呼叫 Verifier Agent 時，每個 chunk 提供的最多字元數 | verifier 判斷需要更多上下文 | verifier 太慢 |

## 使用方式

### 調整 ingestion chunking

修改 `chunk_size` 或 `chunk_stride` 後，需要重新建立 index：

```bash
RAG_CHUNK_SIZE=1600 RAG_CHUNK_STRIDE=800 python3 -m rag_demo.ingest
```

### 調整 query retrieval

調整 `top_k`、keyword / embedding 權重，不一定要重新 ingestion：

```bash
RAG_TOP_K=4 RAG_KEYWORD_WEIGHT=0.45 RAG_EMBEDDING_WEIGHT=0.55 \
python3 -m rag_demo.query '誰是梅林？誰是邪惡方？' --model ollama:qwen2.5:7b
```

網站目前可直接調整：

```text
model
top_k
```

其他參數先透過環境變數調整。

## 阿瓦隆對局紀錄的建議起始值

目前阿瓦隆對局紀錄比員工手冊長，且問題常需要對照「輪次、隊伍、票型、任務結果、角色身份」。建議先用：

```text
RAG_CHUNK_SIZE=1800
RAG_CHUNK_STRIDE=900
RAG_TOP_K=3
RAG_KEYWORD_WEIGHT=0.35
RAG_EMBEDDING_WEIGHT=0.65
RAG_METADATA_BOOST_MAX=0.18
RAG_VERIFIER_AUTO_ACCEPT_ENABLED=false
RAG_VERIFIER_AUTO_ACCEPT_SCORE=0.52
RAG_VERIFIER_AUTO_REJECT_SCORE=0.15
RAG_VERIFIER_CONTEXT_CHARS=600
```

若問的是精確輪次，例如「第1輪隊伍為什麼沒過」，可以提高 keyword 權重：

```text
RAG_KEYWORD_WEIGHT=0.55
RAG_EMBEDDING_WEIGHT=0.45
```

若問的是語意分析，例如「正義方如何收斂到最後成功隊伍」，可以提高 embedding 權重：

```text
RAG_KEYWORD_WEIGHT=0.25
RAG_EMBEDDING_WEIGHT=0.75
```

阿瓦隆對局紀錄常有「表面相關但不足以回答」的情境，例如 chunk 提到最後任務，卻未必能證明刺客是否成功刺殺。因此目前不建議預設開啟 `RAG_VERIFIER_AUTO_ACCEPT_ENABLED`。保守流程是：retrieval 找資料後，仍讓 Verifier Agent 判斷來源是否足以支持回答。

## 後續可新增參數

尚未實作，但適合下一階段加入：

| 參數 | 用途 |
| --- | --- |
| `rewrite_enabled` | 是否啟用 Query Rewriter Agent |
| `verifier_enabled` | 是否啟用 Verifier Agent |
| `rerank_enabled` | 是否在 hybrid retrieval 後再加 reranker |
| `max_context_chars` | 限制送入 LLM 的 context 總字元數 |
| `answer_temperature` | 控制回答模型創造性 |
| `num_ctx` | Ollama context window 大小 |
| `agent_models` | rewrite / verifier / answer / fallback 各自指定模型 |
