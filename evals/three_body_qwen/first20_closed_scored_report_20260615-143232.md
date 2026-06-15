# First20 Closed Three Body QA Agent Eval

- Time: 2026-06-15 14:34:27
- Model: `qwen2.5:7b`
- Workflow: `sparse_dense_refined_keywords`
- Top K: `5`
- Chunk size / stride: `1200/600`
- Questions: `evals/three_body_qwen/questions_first20_closed_20260615.json`
- Raw answers: `evals/three_body_qwen/first20_closed_raw_answers_20260615-143232.jsonl`
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
- Total elapsed: about `114.7s`
- Total score: `1 / 5 = 20.0 / 100`

## Score Table

| ID | Category | Score | Missed Criteria | Penalties |
| --- | --- | ---: | --- | --- |
| F20Q16 | 地球三體組織 | 1/5 | None | 錯說降臨派 (-4) |

## F20Q16 地球三體組織

Question: 申玉菲在地球三體組織中，較接近降臨派還是拯救派？

Standard answer: 申玉菲較接近拯救派。

Elapsed: `114.74s`

Score: `1 / 5`

Matched criteria:
- 申玉菲 (+1)
- 拯救派 (+4)

Missed criteria:
- None

Penalties:
- 錯說降臨派 (-4)

Final Answer:

```text
根據提供的信息，申玉菲在地球三體組織中較接近拯救派。這一點在第十九章《三體、愛因斯坦、單擺、大撕裂汪淼》（part 18）中有明確描述：“對降臨派的背叛，有大量的證據，申玉菲同志就是提供者之一，她曾位居降臨派的核心。但她在內心深處，卻是一名堅定的拯救派，你們也是後來才發現這點的。”此外，在同一章節中提到，“你可以看到，這次與會的大多是拯救派的同志，少數降臨派的成員”。這些信息表明，申玉菲雖然曾是降臨派的核心成員，但她的內心傾向於拯救派。

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
- sparse_refined: 申玉菲在地球三體組織中較接近降臨派還是拯救派？請用4到6句回答，回答要詳細一點；先直接回答標準答案，再補充來源中的關鍵依據。不要使用第一集以外的資訊。
- sparse_keywords: 申玉菲 地球三體組織 降臨派 拯救派
- dense_refined: 申玉菲在地球三體組織中較接近降臨派還是拯救派？請用4到6句回答，回答要詳細一點；先直接回答標準答案，再補充來源中的關鍵依據。不要使用第一集以外的資訊。
- dense_keywords: 申玉菲 地球三體組織 降臨派 拯救派

檢索來源 Top 5：
1. three-body-1.txt / 19.三體、愛因斯坦、單擺、大撕裂汪淼 / part 18 / score=4.0016, keyword=84.0000, embedding=0.0000, trace=sparse:sparse_refined:1, sparse:sparse_keywords:6
2. three-body-1.txt / 19.三體、愛因斯坦、單擺、大撕裂汪淼 / part 17 / score=3.9499, keyword=81.0000, embedding=0.4879, trace=sparse:sparse_refined:3, sparse:sparse_keywords:5, dense:dense_keywords:32
3. three-body-1.txt / 19.三體、愛因斯坦、單擺、大撕裂汪淼 / part 13 / score=3.8340, keyword=66.0000, embedding=0.4952, trace=sparse:sparse_refined:7, sparse:sparse_keywords:4, dense:dense_keywords:27
4. three-body-1.txt / 19.三體、愛因斯坦、單擺、大撕裂汪淼 / part 12 / score=3.6327, keyword=54.0000, embedding=0.5435, trace=sparse:sparse_refined:12, sparse:sparse_keywords:7, dense:dense_refined:3
5. three-body-1.txt / 16.三體問題 / part 14 / score=3.5140, keyword=78.0000, embedding=0.0000, trace=sparse:sparse_refined:5, sparse:sparse_keywords:18

Evidence Extraction Agent:
- [來源 1] 章節：19.三體、愛因斯坦、單擺、大撕裂汪淼 / part 18｜原文摘錄："對降臨派的背叛，有大量的證據，申玉菲同志就是提供者之一，她曾位居降臨派的核心。但她在內心深處，卻是一名堅定的拯救派，你們也是後來才發現這點的。"｜支持點：申玉菲是降臨派的核心成員，但她内心是拯救派。
- [來源 1] 章節：19.三體、愛因斯坦、單擺、大撕裂汪淼 / part 18｜原文摘錄："你可以看到，這次與會的大多是拯救派的同志，少數降臨派的成員。"｜支持點：會議中大多數是拯救派。
- [來源 5] 章節：16.三體問題 / part 14｜原文摘錄：申玉菲說："是的，你們藉著主的力量反對人類。" 潘寒說："你這麼理解也不是完全沒有道理，我們需要主降臨世界，懲罰那些早就該受到懲罰的罪惡，而你在阻止這種降臨，所以我們勢不兩立，你們要是不停止，我們會讓你們停止的！" 申玉菲說："讓你們這些魔鬼進入組織，統帥真瞎了眼！"｜支持點：申玉菲反對降臨派的理念。
節點耗時：
- load_index: 0.00s
- keyword_extraction_agent: 2.78s
- question_extraction_agent: 11.02s
- load_embeddings: 0.01s
- evidence_extraction_agent: 31.51s
- qa_agent: 56.44s
- total: 114.74s
- sparse_dense_retrieval: 12.98s

Final Answer:
根據提供的信息，申玉菲在地球三體組織中較接近拯救派。這一點在第十九章《三體、愛因斯坦、單擺、大撕裂汪淼》（part 18）中有明確描述：“對降臨派的背叛，有大量的證據，申玉菲同志就是提供者之一，她曾位居降臨派的核心。但她在內心深處，卻是一名堅定的拯救派，你們也是後來才發現這點的。”此外，在同一章節中提到，“你可以看到，這次與會的大多是拯救派的同志，少數降臨派的成員”。這些信息表明，申玉菲雖然曾是降臨派的核心成員，但她的內心傾向於拯救派。

來源：[來源 1] 章節：19.三體、愛因斯坦、單擺、大撕裂汪淼 / part 18

```
