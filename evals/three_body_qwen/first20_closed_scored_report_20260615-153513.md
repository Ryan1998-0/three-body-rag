# First20 Closed Three Body QA Agent Eval

- Time: 2026-06-15 15:36:57
- Model: `qwen2.5:7b`
- Workflow: `sparse_dense_original_refined_keywords`
- Top K: `5`
- Chunk size / stride: `1200/600`
- Questions: `evals/three_body_qwen/questions_first20_closed_20260615.json`
- Raw answers: `evals/three_body_qwen/first20_closed_raw_answers_20260615-153513.jsonl`
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
- Total elapsed: about `103.9s`
- Total score: `1 / 5 = 20.0 / 100`

## Score Table

| ID | Category | Score | Missed Criteria | Penalties |
| --- | --- | ---: | --- | --- |
| F20Q04 | 紅岸基地 | 1/5 | 紅岸基地 | None |

## F20Q04 紅岸基地

Question: 葉文潔後來被調到哪一個軍事基地工作？

Standard answer: 她被調到紅岸基地工作。

Elapsed: `103.926s`

Score: `1 / 5`

Matched criteria:
- 葉文潔 (+1)

Missed criteria:
- 紅岸基地

Penalties:
- None

Final Answer:

```text
根據提供的信息，葉文潔後來被調到雷達峰所在的軍事基地工作。在《三體》小說中提到，三年前建設該基地時曾動用巨大人力進行施工，包括架設高壓線和開闢通往峰頂的公路。雷達峰是一個神秘的地方，那裡有一座巨大的拋物面天線，但實際上並非真正的雷達設備。連隊的人只知道那是一個軍事基地，而葉文潔被調往該地工作。

來源：[來源 1]、[來源 2]
```

Full RAG Output:

```text
問題：葉文潔後來被調到哪一個軍事基地工作？
請用 4 到 6 句回答，回答要詳細一點；先直接回答標準答案，再補充來源中的關鍵依據。不要使用第一集以外的資訊。

Keyword Extraction Agent:
葉文潔, 軍事基地

Question Extraction Agent:
葉文潔後來被調到哪一個軍事基地工作？請用4到6句回答，回答要詳細一點；先直接回答標準答案，再補充來源中的關鍵依據。不要使用第一集以外的資訊。

Hybrid Retrieval Query Variants:
- sparse_refined: 葉文潔後來被調到哪一個軍事基地工作？請用4到6句回答，回答要詳細一點；先直接回答標準答案，再補充來源中的關鍵依據。不要使用第一集以外的資訊。
- sparse_original_keywords: 葉文潔 軍事基地
- sparse_refined_keywords: 葉文潔 軍事基地
- sparse_all_keywords: 葉文潔 軍事基地
- dense_refined: 葉文潔後來被調到哪一個軍事基地工作？請用4到6句回答，回答要詳細一點；先直接回答標準答案，再補充來源中的關鍵依據。不要使用第一集以外的資訊。
- dense_all_keywords: 葉文潔 軍事基地

檢索來源 Top 5：
1. three-body-1.txt / 2.寂靜的春天兩年以後，大興安嶺。 / part 4 / score=3.0723, keyword=54.0000, embedding=0.0000, trace=sparse:sparse_refined:2, sparse:sparse_original_keywords:1, sparse:sparse_refined_keywords:1, sparse:sparse_all_keywords:1
2. three-body-1.txt / 2.寂靜的春天兩年以後，大興安嶺。 / part 5 / score=2.8265, keyword=51.0000, embedding=0.0000, trace=sparse:sparse_refined:3, sparse:sparse_original_keywords:2, sparse:sparse_refined_keywords:2, sparse:sparse_all_keywords:2
3. three-body-1.txt / 8.葉文潔 / part 5 / score=2.4267, keyword=26.0000, embedding=0.0000, trace=sparse:sparse_refined:31, sparse:sparse_original_keywords:3, sparse:sparse_refined_keywords:3, sparse:sparse_all_keywords:3
4. three-body-1.txt / 8.葉文潔 / part 1 / score=2.2597, keyword=28.0000, embedding=0.0000, trace=sparse:sparse_refined:24, sparse:sparse_original_keywords:4, sparse:sparse_refined_keywords:4, sparse:sparse_all_keywords:4
5. three-body-1.txt / 8.葉文潔 / part 4 / score=2.2559, keyword=31.0000, embedding=0.0000, trace=sparse:sparse_refined:14, sparse:sparse_original_keywords:7, sparse:sparse_refined_keywords:7, sparse:sparse_all_keywords:7

Evidence Extraction Agent:
- [來源 5] 章節：8.葉文潔 / part 4｜原文摘錄：照片中，小楊冬的大眼睛中透出一種令汪淼心顫的恐惶，彷彿照片外的世界令她恐懼似的。｜支持點：無直接提及軍事基地。
- [來源 2] 章節：2.寂靜的春天兩年以後，大興安嶺 / part 5｜原文摘錄：連隊的人只知道那是一個軍事基地，聽當地人說，三年前建設那個基地時，曾動用巨大的人力，向峰頂架設了一條高壓線，開闢了一條通向峰頂的公路，有大量的物資沿公路運上去。｜支持點：描述了軍事基地的建設情況。
- [來源 1] 章節：2.寂靜的春天兩年以後，大興安嶺 / part 4｜原文摘錄：連隊的人只知道那是一個軍事基地，聽當地人說，三年前建設那個基地時，曾動用巨大的人力，向峰頂架設了一條高壓線，開闢了一條通向峰頂的公路，有大量的物資沿公路運上去。｜支持點：描述了軍事基地的建設情況。

無法從檢索來源抽取足夠 evidence。
節點耗時：
- load_index: 0.00s
- question_extraction_agent: 10.06s
- load_embeddings: 0.01s
- evidence_extraction_agent: 28.75s
- qa_agent: 51.31s
- total: 103.92s
- original_keyword_extraction_agent: 2.17s
- refined_keyword_extraction_agent: 1.32s
- sparse_dense_retrieval: 10.31s

Final Answer:
根據提供的信息，葉文潔後來被調到雷達峰所在的軍事基地工作。在《三體》小說中提到，三年前建設該基地時曾動用巨大人力進行施工，包括架設高壓線和開闢通往峰頂的公路。雷達峰是一個神秘的地方，那裡有一座巨大的拋物面天線，但實際上並非真正的雷達設備。連隊的人只知道那是一個軍事基地，而葉文潔被調往該地工作。

來源：[來源 1]、[來源 2]

```
