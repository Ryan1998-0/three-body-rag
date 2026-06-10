# RAG Performance Log

## 2026-06-10 Avalon RAG Baseline Timing

使用者於 demo 網站實測後回報本次節點耗時。

### 環境與流程

- Knowledge base：阿瓦隆對局紀錄
- Index 狀態：`22 chunks`
- Demo URL：`http://127.0.0.1:8766/ask`
- Pipeline：Query Rewriter Agent → Hybrid Retrieval → Verifier Agent → Answer Agent
- 模型：本機 Ollama 模型，當前 demo 預設為 `ollama:qwen2.5:7b`

### 節點耗時

```text
load_index: 0.00s
query_rewrite: 8.60s
load_embeddings: 0.00s
retrieval: 9.98s
verifier: 29.04s
answer_generation: 30.06s
total: 77.68s
```

### 初步觀察

- `load_index` 與 `load_embeddings` 幾乎不是瓶頸。
- `retrieval` 約 10 秒，推測主要原因是每次 query 時 `embed_query()` 重新載入 `sentence-transformers` model。
- `verifier` 與 `answer_generation` 是最大瓶頸，兩者都會吃 retrieved chunks context。
- 阿瓦隆對局紀錄的 chunk 內容較長，即使已切成 `22 chunks`，`top_k=3` 時仍可能送入較長 context。

### 後續優化候選

1. 快取 embedding model，避免每次 query 重載 sentence-transformers。
2. 加入 retrieval confidence rule，明顯相關或明顯無關時跳過 Verifier Agent。
3. 限制 verifier context，只提供標題、score 與 chunk 前段摘要。
4. 加入 `max_context_chars`，限制 Answer Agent prompt 長度。
5. Query rewrite 改成可關閉或規則式優先，減少一次 LLM call。

## 2026-06-10 Embedding Model Cache

已新增 process-level embedding model cache，避免每次 `embed_query()` 都重新建立 `SentenceTransformer`。

變更檔案：

```text
rag_demo/embeddings.py
tests/test_rag_pipeline.py
```

快取驗證：

```text
embed_query_1: 10.79s dim=384
embed_query_2: 0.01s dim=384
```

預期影響：

- 第一次查詢仍需載入 embedding model。
- 同一個 web server process 後續查詢會重用已載入的 embedding model。
- 原本 baseline 中 `retrieval: 9.98s` 的主要載入成本，後續查詢應可大幅下降。

測試：

```text
python3 -m unittest discover -s tests
Ran 35 tests
OK
```

### Demo 實測結果

使用者於同一個 demo 網站流程再次實測，確認 embedding model cache 已反映在 retrieval 節點。

```text
load_index: 0.00s
query_rewrite: 8.32s
load_embeddings: 0.00s
retrieval: 0.26s
verifier: 28.35s
answer_generation: 29.95s
total: 66.88s
```

### 優化前後對比

| 節點 | 優化前 | 優化後 | 改善 |
| --- | ---: | ---: | ---: |
| `retrieval` | `9.98s` | `0.26s` | `-9.72s` |
| `total` | `77.68s` | `66.88s` | `-10.80s` |

結論：

- `retrieval` 節點已從約 10 秒下降到 0.26 秒。
- 整體查詢時間下降 10.80 秒。
- 目前主要瓶頸已轉移到 `verifier` 與 `answer_generation`。
- 下一步優化應優先處理 Verifier Agent，例如 retrieval confidence rule、verifier context truncation 或灰色地帶才呼叫 verifier。

## 2026-06-10 Verifier Confidence Gate

已新增 Verifier Agent 優化，避免每次 retrieval 後都呼叫本機 Qwen 7B verifier。

變更檔案：

```text
rag_demo/config.py
rag_demo/retrieval_verifier.py
tests/test_rag_pipeline.py
docs/rag_tuning_parameters.md
```

新增機制：

1. `assess_retrieval_confidence()` 會先看 top chunk 的 `score`、`keyword_score`、`embedding_score`。
2. `auto_accept` 已改為可選功能，預設關閉，避免高分但不足以回答的 chunk 被誤放行。
3. 明顯無關時直接回傳 `is_related=false`，reason 會標示 `auto_reject`。
4. 預設流程下，非明顯無關的問題仍會真正呼叫 Verifier Agent。
5. 真正呼叫 Verifier Agent 時，context 會截斷為每個 chunk 前 `RAG_VERIFIER_CONTEXT_CHARS` 字元，預設 `600`。

新增環境變數：

```text
RAG_VERIFIER_AUTO_ACCEPT_ENABLED=false
RAG_VERIFIER_AUTO_ACCEPT_SCORE=0.52
RAG_VERIFIER_AUTO_REJECT_SCORE=0.15
RAG_VERIFIER_MIN_KEYWORD_SCORE=8
RAG_VERIFIER_MIN_EMBEDDING_SCORE=0.35
RAG_VERIFIER_CONTEXT_CHARS=600
```

預期影響：

- 預設只對明顯無關問題使用 `auto_reject`，可避免不必要的 verifier call。
- 對於可能相關的問題，仍保留 Verifier Agent 作為安全檢查，避免 retrieval 高分但答案沒有來源支持。
- 即使進入 Verifier Agent，也會因 context truncation 減少 prompt 長度。

測試：

```text
python3 -m unittest discover -s tests
Ran 39 tests
OK
```

## 2026-06-10 Verifier Auto Accept 回退

使用者實測發現 `auto_accept` 會讓 Verifier Agent 花費 `0.00s`，但回答品質下降。案例中模型根據相近 chunk 產生「刺客投反對票、未直接殺害玩家」等回答，代表 retrieval 高分不等於來源足以支持答案。

修正：

- `RAG_VERIFIER_AUTO_ACCEPT_ENABLED` 預設改為 `false`。
- 強命中 retrieval 預設仍會進入 Verifier Agent。
- 若未來只追求 demo 速度，可明確設定 `RAG_VERIFIER_AUTO_ACCEPT_ENABLED=true` 再開啟快速放行。
