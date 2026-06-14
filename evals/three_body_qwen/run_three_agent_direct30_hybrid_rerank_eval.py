from datetime import datetime
from pathlib import Path
import json
import re
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag_demo.chunking import load_knowledge_base_chunks
from rag_demo.config import RagConfig, resolve_project_path
from rag_demo.embeddings import embed_query, load_embedding_matrix
from rag_demo.index_store import load_index
from rag_demo.keyword_extraction import extract_keywords
from rag_demo.qa_agent import answer_with_qa_agent
from rag_demo.question_extraction import extract_real_question
from rag_demo.retrieval import embedding_search, keyword_search


PROJECT_ROOT = ROOT
CANDIDATE_K = 50


def main() -> int:
    eval_dir = Path(__file__).resolve().parent
    question_path = eval_dir / "questions_direct30_lenient_20260615.json"
    questions = json.loads(question_path.read_text(encoding="utf-8"))
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    raw_path = eval_dir / f"three_agent_direct30_hybrid_rerank_raw_answers_{timestamp}.jsonl"
    report_path = eval_dir / f"three_agent_direct30_hybrid_rerank_scored_report_{timestamp}.md"

    model = "qwen2.5:7b"
    top_k = RagConfig.from_env().top_k
    chunks, embeddings = load_retrieval_assets()
    started = time.perf_counter()
    records = []

    with raw_path.open("w", encoding="utf-8") as raw_file:
        for item in questions:
            q_started = time.perf_counter()
            record = {
                "id": item["id"],
                "question": item["question"],
                "answer_output": "",
                "final_answer": "",
                "score": 0,
                "max_score": sum(int(criterion.get("weight", 1)) for criterion in item["criteria"]),
                "matched": [],
                "missed": [],
                "error": None,
                "elapsed_seconds": None,
            }
            try:
                record["answer_output"] = answer_question_hybrid_rerank(
                    item["question"],
                    chunks=chunks,
                    embeddings=embeddings,
                    model=model,
                    top_k=top_k,
                    candidate_k=CANDIDATE_K,
                )
                record["final_answer"] = extract_final_answer(record["answer_output"])
                score_record(record, item["criteria"])
            except Exception as exc:
                record["error"] = f"{type(exc).__name__}: {exc}"
                record["missed"] = [criterion["label"] for criterion in item["criteria"]]
            record["elapsed_seconds"] = round(time.perf_counter() - q_started, 3)
            records.append(record)
            raw_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            raw_file.flush()
            print(
                f"{record['id']} score={record['score']}/{record['max_score']} "
                f"elapsed={record['elapsed_seconds']}s error={record['error'] is not None}"
            )

    write_report(report_path, raw_path, question_path, records, model, top_k, started)
    print(f"Raw JSONL: {raw_path}")
    print(f"Scored report: {report_path}")
    return 0 if all(record["error"] is None for record in records) else 1


def load_retrieval_assets():
    kb_dir = resolve_project_path("RAG_KB_DIR", "data/raw", project_root=PROJECT_ROOT)
    index_dir = resolve_project_path("RAG_INDEX_DIR", "data/index", project_root=PROJECT_ROOT)
    index_path = index_dir / "chunks.json"
    if index_path.exists():
        chunks = load_index(index_path)
    else:
        chunks = load_knowledge_base_chunks(kb_dir)

    embedding_path = index_dir / "embeddings.npy"
    embeddings = load_embedding_matrix(embedding_path) if embedding_path.exists() else None
    return chunks, embeddings


def answer_question_hybrid_rerank(
    question: str,
    chunks,
    embeddings,
    model: str,
    top_k: int = 5,
    candidate_k: int = 50,
) -> str:
    total_started_at = time.perf_counter()
    timing = {}

    started_at = time.perf_counter()
    keywords = extract_keywords(question, model=model)
    timing["keyword_extraction_agent"] = time.perf_counter() - started_at

    started_at = time.perf_counter()
    refined_question = extract_real_question(question, model=model)
    timing["question_extraction_agent"] = time.perf_counter() - started_at

    started_at = time.perf_counter()
    results, query_variants = hybrid_retrieve_and_rerank(
        question=question,
        refined_question=refined_question,
        keywords=keywords,
        chunks=chunks,
        embeddings=embeddings,
        top_k=top_k,
        candidate_k=candidate_k,
    )
    timing["hybrid_retrieval_rerank"] = time.perf_counter() - started_at

    started_at = time.perf_counter()
    answer = answer_with_qa_agent(
        original_question=question,
        refined_question=refined_question,
        keywords=keywords,
        chunks=results,
        model=model,
    )
    timing["qa_agent"] = time.perf_counter() - started_at
    timing["total"] = time.perf_counter() - total_started_at

    return format_output(
        question=question,
        keywords=keywords,
        refined_question=refined_question,
        query_variants=query_variants,
        results=results,
        answer=answer,
        timing=timing,
    )


def hybrid_retrieve_and_rerank(
    question: str,
    refined_question: str,
    keywords,
    chunks,
    embeddings,
    top_k: int,
    candidate_k: int,
):
    query_variants = build_query_variants(question, refined_question, keywords)
    candidates = {}

    for query_index, variant in enumerate(query_variants):
        query_text = variant["query"]
        query_weight = variant["weight"]

        keyword_results = keyword_search(query_text, chunks, top_k=candidate_k)
        max_keyword_score = max((float(item.get("score", 0.0)) for item in keyword_results), default=1.0)
        for rank, chunk in enumerate(keyword_results, start=1):
            normalized_score = float(chunk.get("score", 0.0)) / max_keyword_score if max_keyword_score else 0.0
            add_candidate_score(
                candidates,
                chunk,
                score=query_weight * (0.58 * normalized_score + reciprocal_rank(rank, 0.10)),
                method=f"kw:{variant['name']}:{rank}",
                keyword_score=float(chunk.get("score", 0.0)),
            )

        if embeddings is None:
            continue

        embedding_results = embedding_search(
            query_text,
            chunks,
            embeddings=embeddings,
            embed_query_fn=embed_query,
            top_k=candidate_k,
        )
        embedding_scores = [float(item.get("embedding_score", 0.0)) for item in embedding_results]
        min_embedding = min(embedding_scores, default=0.0)
        max_embedding = max(embedding_scores, default=1.0)
        span = max(max_embedding - min_embedding, 1e-9)
        for rank, chunk in enumerate(embedding_results, start=1):
            raw_embedding = float(chunk.get("embedding_score", 0.0))
            normalized_score = (raw_embedding - min_embedding) / span
            add_candidate_score(
                candidates,
                chunk,
                score=query_weight * (0.32 * normalized_score + reciprocal_rank(rank, 0.07)),
                method=f"emb:{variant['name']}:{rank}",
                embedding_score=raw_embedding,
            )

    apply_lexical_coverage_boost(candidates, question, refined_question, keywords)
    ranked = sorted(candidates.values(), key=lambda item: item["score"], reverse=True)
    return [strip_candidate_metadata(item) for item in ranked[:top_k]], query_variants


def build_query_variants(question: str, refined_question: str, keywords):
    keyword_query = " ".join(str(keyword).strip() for keyword in keywords if str(keyword).strip())
    combined_query = " ".join(
        item
        for item in [
            " ".join(str(question).split()),
            " ".join(str(refined_question).split()),
            keyword_query,
        ]
        if item
    )
    variants = [
        {"name": "original", "query": " ".join(str(question).split()), "weight": 1.00},
        {"name": "question_agent", "query": " ".join(str(refined_question).split()), "weight": 1.10},
        {"name": "keywords", "query": keyword_query, "weight": 1.00},
        {"name": "combined", "query": combined_query, "weight": 0.85},
    ]

    unique = []
    seen = set()
    for variant in variants:
        query = variant["query"].strip()
        if not query or query in seen:
            continue
        seen.add(query)
        unique.append({**variant, "query": query})
    return unique


def add_candidate_score(
    candidates,
    chunk,
    score: float,
    method: str,
    keyword_score: float = 0.0,
    embedding_score: float = 0.0,
):
    chunk_id = chunk["id"]
    if chunk_id not in candidates:
        candidate = dict(chunk)
        candidate["score"] = 0.0
        candidate["keyword_score"] = 0.0
        candidate["embedding_score"] = 0.0
        candidate["retrieval_methods"] = []
        candidates[chunk_id] = candidate

    candidate = candidates[chunk_id]
    candidate["score"] += score
    candidate["keyword_score"] = max(float(candidate.get("keyword_score", 0.0)), keyword_score)
    candidate["embedding_score"] = max(float(candidate.get("embedding_score", 0.0)), embedding_score)
    candidate["retrieval_methods"].append(method)


def reciprocal_rank(rank: int, weight: float) -> float:
    return weight / max(rank, 1)


def apply_lexical_coverage_boost(candidates, question: str, refined_question: str, keywords) -> None:
    terms = relevant_terms(" ".join([question, refined_question, " ".join(keywords)]))
    if not terms:
        return
    for candidate in candidates.values():
        text = normalize_compact(
            f"{candidate.get('parent_title', '')} {candidate.get('title', '')} {candidate.get('content', '')}"
        )
        covered = sum(1 for term in terms if normalize_compact(term) in text)
        coverage = covered / len(terms)
        candidate["score"] += 0.16 * coverage


def relevant_terms(text: str):
    raw_terms = re.findall(r"[A-Za-z0-9_.-]+|[\u4e00-\u9fff]{2,}", str(text))
    stop_terms = {
        "什麼",
        "為什麼",
        "如何",
        "哪裡",
        "哪種",
        "問題",
        "核心",
        "主要",
        "代表",
        "得到",
        "提到",
        "造成",
        "認為",
        "需要",
        "希望",
    }
    terms = []
    for term in raw_terms:
        cleaned = term.strip().lower()
        if len(cleaned) < 2 or cleaned in stop_terms:
            continue
        terms.append(cleaned)
    return list(dict.fromkeys(terms))[:24]


def normalize_compact(text: str) -> str:
    return re.sub(r"\s+", "", str(text)).lower()


def strip_candidate_metadata(candidate):
    result = dict(candidate)
    result["retrieval_method"] = "hybrid_rerank"
    methods = result.get("retrieval_methods", [])
    result["rerank_trace"] = ", ".join(methods[:10])
    if len(methods) > 10:
        result["rerank_trace"] += f", +{len(methods) - 10} more"
    return result


def format_output(question, keywords, refined_question, query_variants, results, answer, timing) -> str:
    query_lines = [f"- {variant['name']}: {variant['query']}" for variant in query_variants]
    source_lines = []
    for index, chunk in enumerate(results, start=1):
        source_lines.append(
            f"{index}. {Path(str(chunk['source'])).name} / {chunk['title']} / "
            f"score={float(chunk.get('score', 0.0)):.4f}, "
            f"keyword={float(chunk.get('keyword_score', 0.0)):.4f}, "
            f"embedding={float(chunk.get('embedding_score', 0.0)):.4f}, "
            f"trace={chunk.get('rerank_trace', '')}"
        )

    sources = "\n".join(source_lines) if source_lines else "No sources found"
    keyword_text = ", ".join(str(keyword) for keyword in keywords) if keywords else "None"
    timing_text = format_timing(timing)

    return f"""Question:
{question}

Keyword Extraction Agent:
{keyword_text}

Question Extraction Agent:
{refined_question}

Hybrid retrieval query variants:
{chr(10).join(query_lines)}

Retrieved sources Top {len(results)}:
{sources}
{timing_text}

Final Answer:
{answer}
"""


def format_timing(timing) -> str:
    if not timing:
        return ""
    lines = ["Timing:"]
    for key, value in timing.items():
        lines.append(f"- {key}: {float(value):.2f}s")
    return "\n".join(lines)


def extract_final_answer(answer_output: str) -> str:
    marker = "Final Answer:"
    if marker in answer_output:
        return answer_output.split(marker, 1)[1].strip()
    return str(answer_output).strip()


def score_record(record, criteria) -> None:
    answer = normalize_compact(record["final_answer"])
    score = 0
    matched = []
    missed = []

    for criterion in criteria:
        aliases = [normalize_compact(alias) for alias in criterion.get("aliases", [])]
        if any(alias and alias in answer for alias in aliases):
            weight = int(criterion.get("weight", 1))
            score += weight
            matched.append(f"{criterion['label']} (+{weight})")
        else:
            missed.append(criterion["label"])

    record["score"] = min(score, record["max_score"])
    record["matched"] = matched
    record["missed"] = missed


def write_report(report_path, raw_path, question_path, records, model, top_k, started) -> None:
    total_score = sum(record["score"] for record in records)
    max_score = sum(record["max_score"] for record in records)
    percent = round(total_score / max_score * 100, 1) if max_score else 0.0
    completed = sum(1 for record in records if record["error"] is None)
    elapsed = round(time.perf_counter() - started, 1)
    config = RagConfig.from_env()

    lines = [
        "# Three-Agent Direct30 Hybrid Rerank Scored Report",
        "",
        f"- Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Model: `{model}`",
        "- Retrieval mode: original question + question-agent output + keywords, keyword/embedding candidate recall, deterministic rerank",
        f"- Candidate K: `{CANDIDATE_K}`",
        f"- Top K: `{top_k}`",
        f"- Chunk size / stride: `{config.chunk_size}/{config.chunk_stride}`",
        f"- Questions: `{question_path.as_posix()}`",
        f"- Raw answers: `{raw_path.as_posix()}`",
        "",
        "## Scoring Mechanism",
        "",
        "- 30 narrower questions designed for direct retrieval checks.",
        "- Each question has 3 weighted criteria adding up to 5 points.",
        "- A criterion gets full weighted credit if the Final Answer contains any configured alias.",
        "",
        "## Run Result",
        "",
        f"- Completed: `{completed}/{len(records)}`",
        f"- Runtime errors: `{len(records) - completed}`",
        f"- Total elapsed: about `{elapsed}s`",
        f"- Total score: `{total_score} / {max_score} = {percent} / 100`",
        "",
        "## Score Table",
        "",
        "| ID | Score | Missed Criteria |",
        "| --- | ---: | --- |",
    ]

    for record in records:
        missed = "; ".join(record["missed"]) if record["missed"] else "None"
        lines.append(f"| {record['id']} | {record['score']}/{record['max_score']} | {missed} |")

    for record in records:
        lines.extend(
            [
                "",
                f"## {record['id']}",
                "",
                f"Question: {record['question']}",
                "",
                f"Elapsed: `{record['elapsed_seconds']}s`",
                "",
                f"Score: `{record['score']} / {record['max_score']}`",
                "",
                "Matched criteria:",
            ]
        )
        lines.extend(f"- {item}" for item in record["matched"]) if record["matched"] else lines.append("- None")
        lines.append("")
        lines.append("Missed criteria:")
        lines.extend(f"- {item}" for item in record["missed"]) if record["missed"] else lines.append("- None")
        lines.append("")
        if record["error"]:
            lines.append(f"Error: `{record['error']}`")
        else:
            lines.extend(
                [
                    "Final Answer:",
                    "",
                    "```text",
                    record["final_answer"],
                    "```",
                    "",
                    "Full RAG Output:",
                    "",
                    "```text",
                    record["answer_output"],
                    "```",
                ]
            )

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
