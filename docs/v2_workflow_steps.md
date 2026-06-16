# V2 Retrieval Workflow Steps

本文件補充 README 中 V2 Workflow 的每一步用途、輸入、輸出與目前實作位置。

## 1. Question

輸入使用者原始問題。

重點：

- 原始問題會保留給 BM25 與 Dense Retrieval。
- 不讓 Query Rewrite 取代原始問題，避免人物名、派別名、物件名流失。

主要實作：

- `rag_demo.query`

## 2. Query Rewrite

目的：產生輔助查詢語句，幫助 metadata、rerank 或 graph expansion。

輸入：

- 原始問題
- section titles

輸出：

- rewritten query

注意：

- Rewrite 不作為 BM25 / Dense 主查詢。
- 若 rewrite 變得太泛，例如只剩 `三體`，主 retrieval 仍以原始問題為準。

主要實作：

- `rag_demo.query_rewriter`
- `rag_demo.query._bm25_dense_retrieval_query`

## 3. Entity Extraction

目的：從 query 或 chunk 中抽取人物、組織、地點、事件、概念與物件。

輸入：

- 原始問題
- graph alias records
- chunk text / metadata

輸出：

- normalized entities

主要實作：

- `rag_demo.graph_entities.extract_query_entities`
- `rag_demo.graph_entities.extract_chunk_entities`

## 4. Metadata Filter

目的：先縮小搜尋範圍，避免明確章節、回合或 section 題被相似內容干擾。

輸入：

- 原始問題或輔助 query
- chunks metadata

輸出：

- filtered chunks
- filtered embeddings

目前支援：

- `book`
- `volume`
- `document_type`
- `author`
- `department`
- `chapter`
- sequence-like labels, such as `第5輪`, `第3章`, `step 2`

主要實作：

- `rag_demo.query._explicit_metadata_filters`
- `rag_demo.query._metadata_filter_chunk_embedding_pairs`

## 5. Query Classifier

目的：判斷問題應該主要走 content retrieval、relation retrieval，或 hybrid retrieval。

分類：

| Type | Example | Route |
| --- | --- | --- |
| Content Query | 黑暗森林理論是什麼？ | BM25 + Dense |
| Relation Query | 哪些人屬於 ETO？ | Graph Retrieval |
| Hybrid Query | 葉文潔為什麼建立 ETO？ | Graph + BM25/Dense |

主要實作：

- `rag_demo.query_classifier.classify_query`

## 6. BM25 Original Question

目的：保留精準詞彙召回能力，特別是人名、派別名、物件名、章節詞。

輸入：

- original question
- filtered chunks

輸出：

- BM25 ranked candidates

主要實作：

- `rag_demo.retrieval.keyword_search`
- `rag_demo.query._rrf_parent_context_results`

## 7. Dense Original Question

目的：補足語意相近但字面不完全一致的內容。

輸入：

- original question
- embedding matrix
- filtered chunks

輸出：

- dense ranked candidates

主要實作：

- `rag_demo.embeddings`
- `rag_demo.retrieval.embedding_search`
- `rag_demo.query._rrf_parent_context_results`

## 8. Graph Retrieval

目的：補強人物關係、組織關係、派別、事件與多跳查詢。

輸入：

- original question
- extracted entities
- graph JSON
- chunks

輸出：

- graph supporting chunks
- graph trace

目前 graph 儲存在：

- `data/graph/three_body_graph.json`

主要實作：

- `rag_demo.graph_store`
- `rag_demo.graph_retrieval.retrieve_graph_context`

## 9. RRF Merge

目的：融合 BM25 和 Dense 的 ranked lists，不直接比較兩者 raw score。

輸入：

- BM25 candidates
- Dense candidates

輸出：

- RRF merged candidates

主要實作：

- `rag_demo.query._rrf_merge_ranked_results`

## 10. Graph / Vector Merge

目的：把 graph supporting chunks 和 vector candidates 合併，讓 relation evidence 進入同一個 ranking surface。

輸入：

- graph results
- RRF vector results

輸出：

- merged candidates

主要實作：

- `rag_demo.query._merge_graph_and_vector_candidates`

## 11. Reranker

目的：把候選 chunks 依照問題相關性重排。

輸入：

- merged candidates
- original question
- auxiliary query

輸出：

- reranked candidates

主要實作：

- `rag_demo.query._rerank_rrf_candidates`

## 12. Parent Chunk Expansion

目的：補上命中 chunk 的相鄰 context，避免答案落在前後文。

輸入：

- reranked chunks
- all chunks

輸出：

- expanded context chunks

主要實作：

- `rag_demo.query._expand_parent_chunks`

## 13. Top 8 Context

目的：限制最後交給 LLM 的 evidence 範圍，兼顧 recall 與 context noise。

輸出：

- top 8 final context chunks

主要實作：

- `rag_demo.query._rrf_parent_context_results`

## 14. LLM / QA Agent

目的：只根據 retrieved context 產生最後回答，並附來源。

輸入：

- original question
- retrieved contexts
- evidence facts

輸出：

- final answer
- sources

主要實作：

- `rag_demo.qa_agent`
- `rag_demo.query.answer_question`
