# First20 Closed Three Body QA Agent Eval

- Time: 2026-06-15 11:44:38
- Model: `qwen2.5:7b`
- Top K: `5`
- Chunk size / stride: `1200/600`
- Questions: `evals/three_body_qwen/questions_first20_closed_20260615.json`
- Raw answers: `evals/three_body_qwen/first20_closed_raw_answers_20260615-114154.jsonl`
- Detail instruction: `請用 4 到 6 句回答，回答要詳細一點；先直接回答標準答案，再補充來源中的關鍵依據。不要使用第一集以外的資訊。`

## Scoring Mechanism

- 20 closed-answer questions limited to the first volume of Three Body.
- Each question has a standard answer and weighted criteria totaling 5 points.
- A criterion gets full credit when the Final Answer contains one configured alias.
- Forbidden aliases subtract points for common wrong answers, with a floor of 0.
- This is deterministic keyword scoring for regression tracking; human review is still useful for borderline phrasing.

## Run Result

- Completed: `1/1`
- Runtime errors: `0`
- Total elapsed: about `0.0s`
- Total score: `5 / 5 = 100.0 / 100`

## Score Table

| ID | Category | Score | Missed Criteria | Penalties |
| --- | --- | ---: | --- | --- |
| F20Q16 | 地球三體組織 | 5/5 | None | None |

## F20Q16 地球三體組織

Question: 申玉菲在地球三體組織中，較接近降臨派還是拯救派？

Standard answer: 申玉菲較接近拯救派。

Elapsed: `108.822s`

Score: `5 / 5`

Matched criteria:
- 申玉菲 (+1)
- 拯救派 (+4)

Missed criteria:
- None

Penalties:
- None

Final Answer:

```text
根據提供的信息，申玉菲在地球三體組織中較接近拯救派。這一點在第十九章《三體、愛因斯坦、單擺、大撕裂汪淼》（part 18）中有明確描述：“對降臨派的背叛，有大量的證據，申玉菲同志就是提供者之一，她曾位居降臨派的核心。但她在內心深處，卻是一名堅定的拯救派，你們也是後來才發現這點的。”此外，在同一章節中提到，“你可以看到，這次與會的大多是拯救派的同志，少數降臨派的成員”，這也進一步印證了申玉菲屬於拯救派。

來源：[來源 1] 章節：19.三體、愛因斯坦、單擺、大撕裂汪淼 / part 18
```

Full RAG Output:

```text
問題：申玉菲在地球三體組織中，較接近降臨派還是拯救派？
請用 4 到 6 句回答，回答要詳細一點；先直接回答標準答案，再補充來源中的關鍵依據。不要使用第一集以外的資訊。

Keyword Extraction Agent:
申玉菲, 地球三體組織, 降臨派, 拯救派

Question Extraction Agent:
申玉菲在地球三體組織中較接近降臨派還是拯救派？請用4到6句回答，回答要詳細一點；先直接回答標準答案，再補充來源中的關鍵依據。不要使用第一集以外的資訊。

Hybrid Retrieval Query Variants:
- original: 申玉菲在地球三體組織中，較接近降臨派還是拯救派？ 請用 4 到 6 句回答，回答要詳細一點；先直接回答標準答案，再補充來源中的關鍵依據。不要使用第一集以外的資訊。
- question_agent: 申玉菲在地球三體組織中較接近降臨派還是拯救派？請用4到6句回答，回答要詳細一點；先直接回答標準答案，再補充來源中的關鍵依據。不要使用第一集以外的資訊。
- keywords: 申玉菲 地球三體組織 降臨派 拯救派
- keyword_only: 申玉菲 地球三體組織 降臨派 拯救派

檢索來源 Top 5：
1. three-body-1.txt / 19.三體、愛因斯坦、單擺、大撕裂汪淼 / part 18 / score=5.0598, keyword=84.0000, embedding=0.0000, trace=kw:original:1, kw:question_agent:1, kw:keywords:6, kw:keyword_only:6
2. three-body-1.txt / 19.三體、愛因斯坦、單擺、大撕裂汪淼 / part 17 / score=4.9623, keyword=81.0000, embedding=0.4879, trace=kw:original:3, kw:question_agent:3, kw:keywords:5, emb:keywords:32, kw:keyword_only:5, emb:keyword_only:32
3. three-body-1.txt / 19.三體、愛因斯坦、單擺、大撕裂汪淼 / part 13 / score=4.7316, keyword=66.0000, embedding=0.4952, trace=kw:original:8, kw:question_agent:7, kw:keywords:4, emb:keywords:27, kw:keyword_only:4, emb:keyword_only:27
4. three-body-1.txt / 19.三體、愛因斯坦、單擺、大撕裂汪淼 / part 12 / score=4.5577, keyword=56.0000, embedding=0.5466, trace=kw:original:11, emb:original:3, kw:question_agent:12, emb:question_agent:3, kw:keywords:7, kw:keyword_only:7
5. three-body-1.txt / 16.三體問題 / part 14 / score=4.2817, keyword=80.0000, embedding=0.0000, trace=kw:original:5, kw:question_agent:5, kw:keywords:18, kw:keyword_only:18

Evidence Extraction Agent:
- [來源 1] 章節：19.三體、愛因斯坦、單擺、大撕裂汪淼 / part 18｜原文摘錄："對降臨派的背叛，有大量的證據，申玉菲同志就是提供者之一，她曾位居降臨派的核心。但她在內心深處，卻是一名堅定的拯救派，你們也是後來才發現這點的。"｜支持點：申玉菲在降臨派核心，但她是拯救派。
- [來源 1] 章節：19.三體、愛因斯坦、單擺、大撕裂汪淼 / part 18｜原文摘錄："你可以看到，這次與會的大多是拯救派的同志，少數降臨派的成員。"｜支持點：會議中大多數是拯救派。
- [來源 5] 章節：16.三體問題 / part 14｜原文摘錄：申玉菲說："是的，你們藉著主的力量反對人類。" 潘寒說："你這麼理解也不是完全沒有道理，我們需要主降臨世界，懲罰那些早就該受到懲罰的罪惡，而你在阻止這種降臨，所以我們勢不兩立，你們要是不停止，我們會讓你們停止的！" 申玉菲說："讓你們這些魔鬼進入組織，統帥真瞎了眼！"｜支持點：申玉菲反對降臨派的理念。
節點耗時：
- load_index: 0.00s
- keyword_extraction_agent: 6.19s
- question_extraction_agent: 5.56s
- load_embeddings: 0.01s
- retrieval: 9.87s
- evidence_extraction_agent: 30.99s
- qa_agent: 56.21s
- total: 108.82s

Final Answer:
根據提供的信息，申玉菲在地球三體組織中較接近拯救派。這一點在第十九章《三體、愛因斯坦、單擺、大撕裂汪淼》（part 18）中有明確描述：“對降臨派的背叛，有大量的證據，申玉菲同志就是提供者之一，她曾位居降臨派的核心。但她在內心深處，卻是一名堅定的拯救派，你們也是後來才發現這點的。”此外，在同一章節中提到，“你可以看到，這次與會的大多是拯救派的同志，少數降臨派的成員”，這也進一步印證了申玉菲屬於拯救派。

來源：[來源 1] 章節：19.三體、愛因斯坦、單擺、大撕裂汪淼 / part 18

```
