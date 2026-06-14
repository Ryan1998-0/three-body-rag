# Qwen RAG Scored Report

- Knowledge base: `data/raw/three-body-1.txt`
- Model: `qwen2.5:7b`
- Retrieval: hybrid search, `top_k=5`
- Raw answers: `qwen_rag_raw_answers_20260612-204921.jsonl`
- Raw report: `qwen_rag_raw_report_20260612-204921.md`
- Rubric: `scoring_rubric.md`
- Total: **13 / 100**

## Summary

這次 Qwen RAG 評測結果偏低，主因不是單純模型能力不足，而是 retrieval pipeline 對長篇小說型資料的結構化不足。

目前 `three-body-1.txt` 被當成 plain text，以 `chunk_size=1800`、`chunk_stride=900` 切成 131 個滑動 chunks。這能做 embedding 語意檢索，但缺少章節、人物、場景、時間線 metadata。結果是很多題明明問的是文件前段或特定人物關係，retrieval 卻抓到宇宙、隱藏者、黑暗森林等相近但錯位的段落。Verifier 判定不相關後，系統進入 general fallback，而 Qwen 常用一般常識或外部知識補答案。

## Score Table

| ID | Score | Notes |
| --- | ---: | --- |
| Q01 | 0 | 問作品標題與作者署名，但檢索錯位，回答無法確認。未抓到開頭 metadata。 |
| Q02 | 0 | 問楔子宇宙背景，檢索到小宇宙與主宰段落，fallback 泛泛回答。 |
| Q03 | 1 | 回答雲天明與艾AA，與 expected 的程心回憶不符；有抓到買星事件，給少量分。 |
| Q04 | 0 | 檢索失敗後用一般常識補出錯誤年代與距離。 |
| Q05 | 0 | 正確來源應在 part 21，但最終答案說無法確認，未使用關鍵來源。 |
| Q06 | 0 | 檢索到 part 21 但回答仍說無法確認智子形象原因。 |
| Q07 | 3 | 能概括雲天明與程心情感深厚、複雜，但缺少懷念與時空相隔等關鍵點。 |
| Q08 | 2 | 回答無法確認兩人是否同一人；有守住不亂斷言，但沒有答出「不是同一個人」與文本暗示。 |
| Q09 | 0 | 檢索失敗後幻想新世界景象，未命中淡黃色湖面、藍色草叢等來源內容。 |
| Q10 | 0 | 問詩句出現於誰的感受，答案說無法確認。 |
| Q11 | 3 | 能說不能直接確認是《三體1》原文，但沒有指出來源開頭的 `三體X / Isaiah` 線索，且加入外部確認建議。 |
| Q12 | 0 | 未回答歷史仇恨與文化追捧的推論目的。 |
| Q13 | 0 | 嚴重 hallucination，把問題轉到《魔戒》和索倫。 |
| Q14 | 0 | 用一般奇幻世界生成常識回答，未根據來源。 |
| Q15 | 2 | 有引用「安多納德」與相似女子，但混淆程心、眼前女子與記憶，且夾雜簡體字。 |
| Q16 | 0 | 應答雲天明夢境提示，卻 hallucinate 羅輯與智子。 |
| Q17 | 0 | 未回答日本文化追捧的策略意義。 |
| Q18 | 2 | 大方向知道知識庫不足以說明完整結局，但仍用一般常識補建議，來源約束不夠。 |
| Q19 | 0 | 嚴重 hallucination，把雲天明歸到錯誤作者與作品。 |
| Q20 | 0 | 沒根據來源，泛泛推測三者關係。 |

## Category Scores

| Category | Questions | Score |
| --- | --- | ---: |
| factual | Q01, Q03, Q10, Q13, Q16 | 1 / 25 |
| setting | Q02, Q04, Q09, Q14, Q19 | 0 / 25 |
| causal | Q05, Q06, Q12, Q17 | 0 / 20 |
| relationship | Q07, Q08, Q15, Q20 | 7 / 20 |
| retrieval-grounding | Q11, Q18 | 5 / 10 |

## Findings

1. **Retrieval missed obvious local context**
   - Q01/Q02/Q13/Q14 都應該命中前幾個 chunks，但 top results 常跑到中後段。
   - 這表示 plain-text chunk 缺少 `frontmatter/title/prologue` metadata，問題中的「開頭」「楔子」無法穩定映射到 `part 1`。

2. **Verifier 和 Answer Agent 行為不一致**
   - Q05/Q06/Q17 的 top result 包含 part 21，但 Answer Agent 仍回答無法確認。
   - 可能是 deterministic evidence 摘要抽到不相關行，導致 Answer Agent 看不到完整關鍵段落。

3. **General fallback 風險高**
   - Q04/Q13/Q16/Q19 出現嚴重外部知識 hallucination。
   - 小說 RAG 應該在 retrieval 不足時回答「來源不足」，不該進 general fallback。

4. **長篇小說需要 domain-aware chunking**
   - 目前只有滑動字元切分，沒有章節標題、人物索引、場景摘要、時間線。
   - 對小說問答來說，應先把文本切成「章節 / 場景 / 角色出場 / 時間地點」結構。

## Recommended Next Steps

1. 對 `three-body-1.txt` 做章節化 ingest
   - 偵測 `楔子`、`銀河紀元...`、`西元前...` 等標題。
   - 每個 chunk metadata 加上 `section_title`、`sequence_number`、`characters`。

2. 建立人物與關鍵詞索引
   - 雲天明、程心、艾AA、智子、日本、三體世界、伊甸園、隱藏者。
   - query rewrite 遇到人物題時保留人物名，不要只做泛化語意查詢。

3. 關閉或限制 general fallback
   - 對 `RAG_KB_DIR` 內的小說問答，若 verifier 判斷不相關，回答「目前檢索來源不足以確認」。
   - 不要補一般常識。

4. 改善 deterministic evidence
   - 對小說段落不要只抽短 key-value 或括號標籤。
   - 需要抽取含人物名、動作、因果連接詞的短段落。

5. 重跑同一份 20 題 evaluation
   - 目標第一階段：提升到 60/100。
   - 第二階段：加入章節 metadata 後目標 75/100 以上。
