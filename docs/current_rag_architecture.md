# Current RAG Architecture

更新日期：2026-06-04

## 視覺化架構圖

```mermaid
flowchart TD
    A["Knowledge Base<br/>data/avalon-game-records/*formatted.txt"] --> B["Chunking<br/>依阿瓦隆輪次切 chunks"]
    B --> C["chunks.json<br/>儲存 chunk + metadata"]
    B --> D["embeddings.npy<br/>儲存 chunk embeddings"]

    U["User Question"] --> QR["Query Rewriter Agent<br/>LLM call<br/>語意理解 + 產生 retrieval query"]
    QR --> S["Sanitize Query<br/>避免 query drift"]
    S --> R["Hybrid Retrieval<br/>keyword search + embedding similarity"]

    C --> R
    D --> R

    R --> RC["Retrieved Chunks<br/>top_k chunks + score"]
    RC --> V["Verifier Agent<br/>LLM call<br/>判斷問題與 chunks 是否相關"]

    V -->|is_related = true| P["Prompt Formatting<br/>原始問題 + retrieval chunks + 回答規則"]
    P --> A1["Answer Agent<br/>LLM call<br/>只根據來源回答"]
    A1 --> O["Output<br/>模型回答 + 來源 + verifier 結果"]

    V -->|is_related = false| G["General Fallback Agent<br/>LLM call<br/>標示無法在資料中搜尋到<br/>改用一般常識回答"]
    G --> O

    M["Model Provider Layer<br/>ask_model()"] --> QR
    M --> V
    M --> A1
    M --> G

    MP["可切換模型<br/>ollama:qwen2.5:7b<br/>ollama:llama3.1:8b<br/>ollama:gemma3:4b<br/>openai:gpt-5.5<br/>anthropic:claude-opus..."] --> M
```

## 簡化流程

```text
Knowledge Base
→ Chunking
→ Embedding Index
→ User Question
→ Query Rewrite
→ Hybrid Retrieval
→ Verifier
→ Answer / General Fallback
→ Output
```

## 目前架構重點

- 同一套 RAG pipeline 可切換不同 model provider。
- Query Rewriter Agent、Verifier Agent、Answer Agent 與 General Fallback Agent 分別使用獨立 prompt。
- 現階段各 agent 共用同一個 model spec，尚未拆成每個 agent 各自指定模型。
- Retrieval 與 Generation 分離；LLM 最後看到的是 retrieval chunks，不是 embedding。
- 無相關來源時會明確標示「無法在資料中搜尋到」，再改用一般常識回答。
