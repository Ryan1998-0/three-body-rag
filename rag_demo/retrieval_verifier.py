import json
import re
from typing import Dict, List

from rag_demo.chunking import Chunk
from rag_demo.config import RagConfig
from rag_demo.model_providers import ask_model


VERIFIER_SYSTEM_PROMPT = """你是 RAG retrieval verifier agent。

你的任務是驗證輸入問題和 retrieval chunks 的關聯性。
你不負責回答使用者問題。

請只輸出 JSON，不要輸出 Markdown。
"""


def build_verifier_prompt(question: str, chunks: List[Chunk], context_chars: int = None) -> str:
    config = RagConfig.from_env()
    context_chars = context_chars or config.verifier_context_chars
    return f"""請驗證輸入問題和 retrieval chunks 的關聯性。

如果 chunks 可以直接支持回答問題，is_related 為 true。
如果 chunks 只是一般公司制度、相似但沒有提到問題核心，is_related 為 false。
如果 is_related 為 false，最終系統會回答「無正確來源資料」。

輸出 JSON 格式：
{{
  "is_related": true,
  "confidence": 0.0,
  "reason": "簡短原因"
}}

使用者問題：
{question}

retrieval chunks：
{render_verifier_context(chunks, context_chars=context_chars)}
"""


def verify_retrieval(
    question: str,
    chunks: List[Chunk],
    model: str = "qwen2.5:7b",
    ask_model_fn=ask_model,
    config: RagConfig = None,
) -> Dict[str, object]:
    config = config or RagConfig.from_env()
    if not chunks:
        return {
            "is_related": False,
            "confidence": 0.0,
            "reason": "no retrieved chunks",
        }

    confidence_decision = assess_retrieval_confidence(chunks, config)
    if confidence_decision is not None:
        return confidence_decision

    output = ask_model_fn(
        build_verifier_prompt(question, chunks, context_chars=config.verifier_context_chars),
        model=model,
        system=VERIFIER_SYSTEM_PROMPT,
    )
    return parse_verifier_output(output)


def assess_retrieval_confidence(chunks: List[Chunk], config: RagConfig = None):
    config = config or RagConfig.from_env()
    if not chunks:
        return {
            "is_related": False,
            "confidence": 0.0,
            "reason": "no retrieved chunks",
        }

    top = chunks[0]
    score = float(top.get("score", 0.0))
    keyword_score = float(top.get("keyword_score", 0.0))
    embedding_score = float(top.get("embedding_score", 0.0))

    has_strong_signal = (
        keyword_score >= config.verifier_min_keyword_score
        or embedding_score >= config.verifier_min_embedding_score
    )
    if config.verifier_auto_accept_enabled and score >= config.verifier_auto_accept_score and has_strong_signal:
        return {
            "is_related": True,
            "confidence": min(1.0, score),
            "reason": (
                "auto_accept: retrieval confidence gate passed "
                f"(score={score:.4f}, keyword={keyword_score:.1f}, embedding={embedding_score:.4f})"
            ),
        }

    if (
        score <= config.verifier_auto_reject_score
        and keyword_score <= 0
        and embedding_score < config.verifier_min_embedding_score
    ):
        return {
            "is_related": False,
            "confidence": max(0.0, score),
            "reason": (
                "auto_reject: retrieval confidence gate failed "
                f"(score={score:.4f}, keyword={keyword_score:.1f}, embedding={embedding_score:.4f})"
            ),
        }

    return None


def render_verifier_context(chunks: List[Chunk], context_chars: int = 600) -> str:
    if not chunks:
        return "沒有找到相關來源。"

    sources = []
    for index, chunk in enumerate(chunks, start=1):
        content = str(chunk.get("content", ""))
        clipped = content[:context_chars]
        if len(content) > context_chars:
            clipped = f"{clipped}\n...（內容已截斷，僅供 verifier 判斷相關性）"
        sources.append(
            "\n".join(
                [
                    f"[來源 {index}]",
                    f"文件：{chunk.get('source', '')}",
                    f"父層章節：{chunk.get('parent_title', '')}",
                    f"章節：{chunk.get('title', '')}",
                    f"score：{chunk.get('score', '')}",
                    f"keyword_score：{chunk.get('keyword_score', '')}",
                    f"embedding_score：{chunk.get('embedding_score', '')}",
                    "內容節錄：",
                    clipped,
                ]
            )
        )

    return "\n\n".join(sources)


def parse_verifier_output(output: str) -> Dict[str, object]:
    text = output.strip()
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        text = match.group(0)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        lowered = output.lower()
        related = "true" in lowered and "false" not in lowered
        return {
            "is_related": related,
            "confidence": 0.5 if related else 0.0,
            "reason": output.strip(),
        }

    return {
        "is_related": bool(parsed.get("is_related")),
        "confidence": float(parsed.get("confidence", 0.0)),
        "reason": str(parsed.get("reason", "")),
    }
