import argparse
import os
from pathlib import Path
from time import perf_counter

from rag_demo.action_result_resolution import answer_action_result
from rag_demo.chunking import load_knowledge_base_chunks
from rag_demo.config import RagConfig, resolve_project_path
from rag_demo.embeddings import embed_query, load_embedding_matrix
from rag_demo.entity_resolution import answer_entity_existence
from rag_demo.event_list_retrieval import find_event_list_chunks, find_result_constrained_chunks, merge_event_list_chunks
from rag_demo.evidence_policy import build_evidence_policy
from rag_demo.general_answer import build_general_answer_prompt
from rag_demo.index_store import load_index
from rag_demo.model_providers import ask_model
from rag_demo.prompting import build_answer_prompt
from rag_demo.context_summary import build_deterministic_context_summary
from rag_demo.query_rewriter import rewrite_query_for_retrieval
from rag_demo.retrieval import hybrid_search, keyword_search
from rag_demo.retrieval_verifier import verify_retrieval


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def answer_question(question: str, model: str, top_k: int = 3) -> str:
    total_started_at = perf_counter()
    timing = {}
    config = RagConfig.from_env()
    top_k = top_k or config.top_k
    kb_dir = resolve_project_path("RAG_KB_DIR", "data/raw", project_root=PROJECT_ROOT)
    index_dir = resolve_project_path("RAG_INDEX_DIR", "data/index", project_root=PROJECT_ROOT)
    index_path = index_dir / "chunks.json"
    started_at = perf_counter()
    if index_path.exists():
        chunks = load_index(index_path)
    else:
        chunks = load_knowledge_base_chunks(kb_dir)
    timing["load_index"] = perf_counter() - started_at

    section_titles = [str(chunk["title"]) for chunk in chunks]
    started_at = perf_counter()
    retrieval_query = rewrite_query_for_retrieval(
        question,
        model=model,
        section_titles=section_titles,
    )
    timing["query_rewrite"] = perf_counter() - started_at

    embedding_path = index_dir / "embeddings.npy"
    if embedding_path.exists():
        try:
            started_at = perf_counter()
            embeddings = load_embedding_matrix(embedding_path)
            timing["load_embeddings"] = perf_counter() - started_at
            started_at = perf_counter()
            results = hybrid_search(
                retrieval_query,
                chunks,
                embeddings=embeddings,
                embed_query_fn=embed_query,
                top_k=top_k,
                keyword_weight=config.keyword_weight,
                embedding_weight=config.embedding_weight,
                metadata_boost_max=config.metadata_boost_max,
            )
            timing["retrieval"] = perf_counter() - started_at
        except Exception:
            started_at = perf_counter()
            results = keyword_search(retrieval_query, chunks, top_k=top_k)
            timing["retrieval"] = perf_counter() - started_at
    else:
        started_at = perf_counter()
        results = keyword_search(retrieval_query, chunks, top_k=top_k)
        timing["retrieval"] = perf_counter() - started_at

    started_at = perf_counter()
    event_results = find_event_list_chunks(question, chunks)
    result_constrained_results = find_result_constrained_chunks(question, chunks)
    structured_results = merge_event_list_chunks(event_results, result_constrained_results)
    if structured_results:
        if build_evidence_policy(question).result_only and result_constrained_results:
            results = structured_results
        else:
            results = merge_event_list_chunks(structured_results, results)
    timing["event_list_retrieval"] = perf_counter() - started_at

    started_at = perf_counter()
    context_summary = build_deterministic_context_summary(results, question=question)
    timing["deterministic_evidence"] = perf_counter() - started_at

    started_at = perf_counter()
    entity_answer = answer_entity_existence(question, context_summary)
    timing["entity_resolution"] = perf_counter() - started_at
    if entity_answer is not None:
        timing["total"] = perf_counter() - total_started_at
        return _format_output(
            question,
            retrieval_query,
            results,
            entity_answer,
            verification={
                "is_related": True,
                "confidence": 0.95,
                "reason": "entity_resolution: structured entity evidence answered existence question",
            },
            timing=timing,
            context_summary=context_summary,
        )

    started_at = perf_counter()
    action_answer = answer_action_result(question, context_summary)
    timing["action_result_resolution"] = perf_counter() - started_at
    if action_answer is not None:
        timing["total"] = perf_counter() - total_started_at
        return _format_output(
            question,
            retrieval_query,
            results,
            action_answer,
            verification={
                "is_related": True,
                "confidence": 0.95,
                "reason": "action_result_resolution: action evidence found but success result is not explicit",
            },
            timing=timing,
            context_summary=context_summary,
        )

    started_at = perf_counter()
    verification = verify_retrieval(
        question,
        results,
        model=model,
        evidence_summary=context_summary,
    )
    timing["verifier"] = perf_counter() - started_at
    if not verification["is_related"]:
        started_at = perf_counter()
        answer = ask_model(build_general_answer_prompt(question), model=model)
        timing["general_fallback"] = perf_counter() - started_at
        timing["total"] = perf_counter() - total_started_at
        return _format_output(
            question,
            retrieval_query,
            results,
            answer,
            verification=verification,
            timing=timing,
            context_summary=context_summary,
        )

    prompt = build_answer_prompt(question, results, context_summary=context_summary)
    started_at = perf_counter()
    answer = ask_model(prompt, model=model)
    timing["answer_generation"] = perf_counter() - started_at
    timing["total"] = perf_counter() - total_started_at
    return _format_output(
        question,
        retrieval_query,
        results,
        answer,
        verification=verification,
        timing=timing,
        context_summary=context_summary,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the local Qwen RAG demo.")
    parser.add_argument("question", help="Question to ask against local raw documents.")
    parser.add_argument("--model", default=os.getenv("RAG_MODEL", "qwen2.5:7b"))
    parser.add_argument("--top-k", type=int, default=RagConfig.from_env().top_k)
    args = parser.parse_args()

    print(answer_question(args.question, model=args.model, top_k=args.top_k))


def _format_output(
    question: str,
    retrieval_query: str,
    results,
    answer: str,
    verification=None,
    timing=None,
    context_summary: str = "",
) -> str:
    source_lines = []
    for index, chunk in enumerate(results, start=1):
        detail = f"score={chunk['score']}"
        if "keyword_score" in chunk and "embedding_score" in chunk:
            detail = (
                f"score={float(chunk['score']):.4f}, "
                f"keyword={float(chunk['keyword_score']):.1f}, "
                f"embedding={float(chunk['embedding_score']):.4f}"
            )
        source_lines.append(
            f"{index}. {Path(str(chunk['source'])).name} / {chunk['title']} / {detail}"
        )

    sources = "\n".join(source_lines) if source_lines else "沒有找到來源"
    verifier_text = ""
    if verification:
        verifier_text = f"""
Verifier Agent:
is_related={verification["is_related"]}, confidence={verification["confidence"]}, reason={verification["reason"]}
"""
    summary_text = ""
    if context_summary:
        summary_text = f"""
彙整資料：
{context_summary}
"""
    timing_text = _format_timing(timing or {})

    return f"""問題：{question}

向量檢索用查詢：
{retrieval_query}

檢索來源：
{sources}
{verifier_text}
{summary_text}
{timing_text}

模型回答：
{answer}
"""


def _format_timing(timing) -> str:
    if not timing:
        return ""
    preferred_order = [
        "load_index",
        "query_rewrite",
        "load_embeddings",
        "retrieval",
        "event_list_retrieval",
        "deterministic_evidence",
        "entity_resolution",
        "action_result_resolution",
        "verifier",
        "context_summary",
        "answer_generation",
        "general_fallback",
        "total",
    ]
    lines = ["節點耗時："]
    for key in preferred_order:
        if key in timing:
            lines.append(f"- {key}: {float(timing[key]):.2f}s")
    for key, value in timing.items():
        if key not in preferred_order:
            lines.append(f"- {key}: {float(value):.2f}s")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
