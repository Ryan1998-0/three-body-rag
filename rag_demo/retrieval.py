import re
from typing import Callable, List, Optional, Sequence

from rag_demo.chunking import Chunk


def keyword_search(query: str, chunks: List[Chunk], top_k: int = 5) -> List[Chunk]:
    normalized_query = _normalize_query(query)
    query_terms = _tokenize(normalized_query)
    scored = []

    for chunk in chunks:
        haystack = f"{chunk.get('parent_title', '')}\n{chunk['title']}\n{chunk['content']}"
        haystack_terms = _tokenize(haystack)
        score = _score(normalized_query, query_terms, haystack, haystack_terms)
        score += _metadata_boost(normalized_query, chunk)
        if score > 0:
            result = dict(chunk)
            result["score"] = score
            scored.append(result)

    return sorted(scored, key=lambda item: item["score"], reverse=True)[:top_k]


def embedding_search(
    query: str,
    chunks: List[Chunk],
    embeddings: Sequence[Sequence[float]],
    embed_query_fn: Callable[[str], Sequence[float]],
    top_k: int = 5,
) -> List[Chunk]:
    query_embedding = embed_query_fn(query)
    scored = []

    for chunk, embedding in zip(chunks, embeddings):
        score = _cosine_similarity(query_embedding, embedding)
        result = dict(chunk)
        result["embedding_score"] = score
        result["score"] = score
        result["retrieval_method"] = "embedding"
        scored.append(result)

    return sorted(scored, key=lambda item: item["embedding_score"], reverse=True)[:top_k]


def hybrid_search(
    query: str,
    chunks: List[Chunk],
    embeddings: Optional[Sequence[Sequence[float]]] = None,
    embed_query_fn: Optional[Callable[[str], Sequence[float]]] = None,
    top_k: int = 5,
    keyword_weight: float = 0.3,
    embedding_weight: float = 0.7,
    metadata_boost_max: float = 0.18,
) -> List[Chunk]:
    keyword_weight, embedding_weight = _normalize_weights(keyword_weight, embedding_weight)
    keyword_results = keyword_search(query, chunks, top_k=len(chunks))
    keyword_scores = {chunk["id"]: float(chunk["score"]) for chunk in keyword_results}
    max_keyword_score = max(keyword_scores.values(), default=1.0)

    embedding_scores = {}
    if embeddings is not None and embed_query_fn is not None:
        normalized_query = _normalize_query(query)
        for chunk in embedding_search(normalized_query, chunks, embeddings, embed_query_fn, top_k=len(chunks)):
            embedding_scores[chunk["id"]] = float(chunk["embedding_score"])

    scored = []
    for chunk in chunks:
        keyword_score = keyword_scores.get(chunk["id"], 0.0)
        normalized_keyword = keyword_score / max_keyword_score if max_keyword_score else 0.0
        embedding_score = embedding_scores.get(chunk["id"], 0.0)
        score = (keyword_weight * normalized_keyword) + (embedding_weight * embedding_score)
        score += _hybrid_metadata_boost(query, chunk, metadata_boost_max=metadata_boost_max)

        if score > 0:
            result = dict(chunk)
            result["keyword_score"] = keyword_score
            result["embedding_score"] = embedding_score
            result["score"] = score
            result["retrieval_method"] = "hybrid" if embedding_scores else "keyword"
            scored.append(result)

    return sorted(scored, key=lambda item: item["score"], reverse=True)[:top_k]


def _score(query: str, query_terms: List[str], haystack: str, haystack_terms: List[str]) -> int:
    score = 0
    compact_query = re.sub(r"\s+", "", query)
    compact_haystack = re.sub(r"\s+", "", haystack)

    for term in query_terms:
        if term in haystack_terms:
            score += 3
        elif term and term in compact_haystack:
            score += 1

    for length in (4, 3, 2):
        for i in range(max(0, len(compact_query) - length + 1)):
            phrase = compact_query[i : i + length]
            if phrase in compact_haystack:
                score += length

    score += _polarity_score(query, haystack)
    return score


def _tokenize(text: str) -> List[str]:
    latin = re.findall(r"[A-Za-z0-9_,.]+", text.lower())
    cjk = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    return latin + cjk


def _normalize_query(query: str) -> str:
    return query


def _metadata_boost(query: str, chunk: Chunk) -> int:
    title = str(chunk.get("title", ""))
    parent_title = str(chunk.get("parent_title", ""))
    metadata_text = f"{parent_title}\n{title}"
    return _metadata_overlap_score(query, metadata_text)


def _hybrid_metadata_boost(query: str, chunk: Chunk, metadata_boost_max: float = 0.18) -> float:
    title = str(chunk.get("title", ""))
    parent_title = str(chunk.get("parent_title", ""))
    metadata_text = f"{parent_title}\n{title}"
    return min(_metadata_overlap_score(query, metadata_text) * 0.01, metadata_boost_max)


def _normalize_weights(keyword_weight: float, embedding_weight: float):
    keyword_weight = max(0.0, float(keyword_weight))
    embedding_weight = max(0.0, float(embedding_weight))
    total = keyword_weight + embedding_weight
    if total <= 0:
        return 0.3, 0.7
    return keyword_weight / total, embedding_weight / total


def _metadata_overlap_score(query: str, metadata_text: str) -> int:
    score = 0
    compact_query = re.sub(r"\s+", "", query)
    compact_metadata = re.sub(r"\s+", "", metadata_text)

    for term in _tokenize(query):
        if len(term) >= 2 and term in metadata_text:
            score += min(len(term) * 2, 16)

    for length in (6, 5, 4, 3, 2):
        for i in range(max(0, len(compact_query) - length + 1)):
            phrase = compact_query[i : i + length]
            if phrase in compact_metadata:
                score += length

    return score


def _polarity_score(query: str, haystack: str) -> int:
    compact_query = re.sub(r"\s+", "", query)
    compact_haystack = re.sub(r"\s+", "", haystack)
    score = 0

    if "失敗" in compact_query:
        if _has_positive_outcome_match(compact_haystack, "失敗"):
            score += 28
        elif "失敗" in compact_haystack:
            score += 6
        if _has_negated_outcome_match(compact_haystack, "失敗"):
            score -= 24

    if "成功" in compact_query:
        if _has_positive_outcome_match(compact_haystack, "成功"):
            score += 28
        elif "成功" in compact_haystack:
            score += 6
        if _has_negated_outcome_match(compact_haystack, "成功"):
            score -= 24

    return score


def _has_positive_outcome_match(compact_text: str, outcome: str) -> bool:
    field_names = "結果|狀態|判定|結論|任務|處理狀態"
    return bool(re.search(rf"({field_names})[:：]{outcome}", compact_text))


def _has_negated_outcome_match(compact_text: str, outcome: str) -> bool:
    if outcome == "失敗":
        return bool(re.search(r"(失敗\w{0,4}0|0失敗|無失敗|沒有失敗)", compact_text))
    if outcome == "成功":
        return bool(re.search(r"(未成功|沒有成功|不成功|成功\w{0,4}0)", compact_text))
    return False


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = sum(a * a for a in left) ** 0.5
    right_norm = sum(b * b for b in right) ** 0.5
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)
