# Three Body RAG

Retrieval-first RAG project for testing and improving a V2 retrieval pipeline with BM25, Dense Retrieval, RRF, Reranker, Parent Chunk Expansion, and Graph Retrieval.

## Workflow

```text
Question
↓
Query Rewrite
↓
Entity Extraction
↓
Metadata Filter
↓
Query Classifier
↓
Graph Retrieval + BM25(original question) + Dense(original question)
↓
Graph / Vector Merge
↓
Reranker
↓
Parent Chunk Expansion
↓
Top 8 Context
↓
LLM / QA Agent
```

## Architecture Notes

- BM25 and Dense Retrieval both use the original question.
- Query Rewrite is auxiliary and does not replace the original question.
- Graph Retrieval adds entity / relation evidence for people, organizations, factions, events, and multi-hop questions.
- Graph results are converted back into supporting chunks before merging with vector candidates.
- RRF merges BM25 and Dense ranked lists.
- Reranker ranks the merged candidates.
- Parent Chunk Expansion adds nearby chunks from the same parent section.
- Final answer generation uses Top 8 Context.

Detailed step-by-step workflow:

- [V2 Retrieval Workflow Steps](docs/v2_workflow_steps.md)

GraphRAG roadmap:

- [GraphRAG Incremental Upgrade Roadmap](docs/graphrag_incremental_roadmap.md)

## How To Use

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Build index from `data/raw/*`:

```bash
python3 -m rag_demo.ingest
```

Ask a question:

```bash
python3 -m rag_demo.query '申玉菲在地球三體組織中屬於哪一派？'
```

Specify a model:

```bash
python3 -m rag_demo.query '古箏行動的核心做法是什麼？' --model ollama:qwen2.5:7b
```

Run the web app:

```bash
python3 -m rag_demo.web_app --port 8766
```

Open:

```text
http://127.0.0.1:8766
```

Run tests:

```bash
python3 -m unittest discover -s tests
```

## Test Results

| Evaluation | Result |
| --- | ---: |
| First20 closed semantic score | `85 / 100` |
| First20 retrieval upper bound | `100 / 100` |
| Direct30 hybrid rerank final answer score | `124 / 150 = 82.7%` |
| Direct30 hybrid rerank Top5 evidence estimate | `140 / 150 = 93.3%` |
| Direct30 diagnosis retrieval ceiling | `77 / 90 = 85.6%` |
| Bad open-question current 5pt upper bound | `56 / 60 = 93.3%` |
| Bad open-question current 3pt ceiling | `34 / 36 = 94.4%` |
| Unit tests | `149 tests OK` |

Evaluation files and simulated QA outputs:

- [Simulated Questions and Answers](docs/simulated_questions_and_answers.md)

## Model Providers

Supported model spec examples:

```text
ollama:qwen2.5:7b
ollama:llama3.1:8b
ollama:gemma3:4b
openai:gpt-5.5
anthropic:claude-opus-4-1-20250805
```

The model provider controls the LLM / agent model. If the embedding model changes, rebuild the index with `rag_demo.ingest`.
