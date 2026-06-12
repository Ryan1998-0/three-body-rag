import json
import re
from typing import Dict, List

from rag_demo.chunking import Chunk
from rag_demo.config import RagConfig
from rag_demo.evidence_policy import answerable_event_spans, has_answerable_event_evidence
from rag_demo.model_providers import ask_model


VERIFIER_SYSTEM_PROMPT = """你是 RAG retrieval verifier agent。

你的任務是驗證 retrieval chunks 是否包含足夠 evidence 回答使用者問題。
你不負責回答使用者問題。
你必須先找 evidence，再判斷是否可回答。

請只輸出 JSON，不要輸出 Markdown。
"""


def build_verifier_prompt(
    question: str,
    chunks: List[Chunk],
    context_chars: int = None,
    evidence_summary: str = "",
) -> str:
    config = RagConfig.from_env()
    context_chars = context_chars or config.verifier_context_chars
    evidence_section = ""
    if evidence_summary:
        evidence_section = f"""deterministic evidence：
{evidence_summary}

"""
    return f"""請驗證 retrieval chunks 是否包含足夠 evidence 回答使用者問題。

請先找 evidence，再判斷是否可回答。

重要判斷原則：
- 「相關」不等於「足以回答」；只有找到可支持答案的 evidence，is_answerable 才能是 true。
- evidence 可以出現在正文、標題、章節名稱、metadata、表格列、列表、條列項、檔名、欄位名稱、角色標籤、代號標籤或結構化資料中。
- 如果問題問的是名單、身份、分類、欄位、表格值或對照關係，標題、列表、表格列、metadata、角色標籤都可以是有效 evidence。
- 如果 chunks 只是語意相近，但沒有提供能回答問題的 evidence，is_answerable 為 false。
- 如果 is_answerable 為 false，最終系統會回答「無正確來源資料」或進入 fallback。

輸出 JSON 格式：
{{
  "is_answerable": true,
  "confidence": 0.0,
  "evidence_spans": ["直接支持答案的原文片段"],
  "missing_info": ["仍缺少的資訊，若沒有則輸出空陣列"],
  "reason": "簡短原因"
}}

使用者問題：
{question}

{evidence_section}請優先檢查 deterministic evidence。若 deterministic evidence 已直接支持答案，請勿因 retrieval chunks 文字較長而誤判為不可回答。

retrieval chunks：
{render_verifier_context(chunks, context_chars=context_chars)}
"""


def verify_retrieval(
    question: str,
    chunks: List[Chunk],
    model: str = "qwen2.5:7b",
    ask_model_fn=ask_model,
    config: RagConfig = None,
    evidence_summary: str = "",
) -> Dict[str, object]:
    config = config or RagConfig.from_env()
    if not chunks:
        return {
            "is_related": False,
            "is_answerable": False,
            "confidence": 0.0,
            "evidence_spans": [],
            "missing_info": ["no retrieved chunks"],
            "reason": "no retrieved chunks",
        }

    deterministic_decision = assess_deterministic_evidence(question, evidence_summary)
    if deterministic_decision is not None:
        return deterministic_decision

    confidence_decision = assess_retrieval_confidence(chunks, config)
    if confidence_decision is not None:
        return confidence_decision

    output = ask_model_fn(
        build_verifier_prompt(
            question,
            chunks,
            context_chars=config.verifier_context_chars,
            evidence_summary=evidence_summary,
        ),
        model=model,
        system=VERIFIER_SYSTEM_PROMPT,
    )
    return parse_verifier_output(output)


def assess_deterministic_evidence(question: str, evidence_summary: str):
    if not has_answerable_event_evidence(question, evidence_summary):
        return None

    return {
        "is_related": True,
        "is_answerable": True,
        "confidence": 0.95,
        "evidence_spans": answerable_event_spans(evidence_summary),
        "missing_info": [],
        "reason": "deterministic_evidence: structured event fields directly support the answer",
    }


def assess_retrieval_confidence(chunks: List[Chunk], config: RagConfig = None):
    config = config or RagConfig.from_env()
    if not chunks:
        return {
            "is_related": False,
            "is_answerable": False,
            "confidence": 0.0,
            "evidence_spans": [],
            "missing_info": ["no retrieved chunks"],
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
            "is_answerable": True,
            "confidence": min(1.0, score),
            "evidence_spans": [],
            "missing_info": [],
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
            "is_answerable": False,
            "confidence": max(0.0, score),
            "evidence_spans": [],
            "missing_info": ["retrieval confidence too low"],
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
        clipped = _clip_for_verifier(content, context_chars)
        candidates = extract_evidence_candidates(content)
        candidate_text = "\n".join(f"- {item}" for item in candidates) if candidates else "無"
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
                    "evidence 候選：",
                    candidate_text,
                    "內容節錄：",
                    clipped,
                ]
            )
        )

    return "\n\n".join(sources)


def extract_evidence_candidates(content: str, max_candidates: int = 12) -> List[str]:
    candidates = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if _is_evidence_candidate_line(line):
            candidates.append(line)
        if len(candidates) >= max_candidates:
            break
    return candidates


def _is_evidence_candidate_line(line: str) -> bool:
    if len(line) > 120:
        return False
    if re.match(r"^#{1,6}\s+\S+", line):
        return True
    if re.match(r"^[\-*]\s+\S+", line):
        return True
    if line.startswith("|") and line.endswith("|") and line.count("|") >= 2:
        return True
    if re.match(r"^[【\[][^】\]]+[】\]]$", line):
        return True
    if re.match(r"^[^：:]{1,30}[：:]\s*\S+", line):
        return True
    return False


def _clip_for_verifier(content: str, context_chars: int) -> str:
    if len(content) <= context_chars:
        return content

    head_chars = max(1, context_chars // 2)
    tail_chars = max(1, context_chars - head_chars)
    return (
        f"{content[:head_chars]}\n"
        "...（內容已截斷，保留開頭與結尾供 verifier 判斷相關性）\n"
        f"{content[-tail_chars:]}"
    )


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
            "is_answerable": related,
            "confidence": 0.5 if related else 0.0,
            "evidence_spans": [],
            "missing_info": [],
            "reason": output.strip(),
        }

    is_answerable = parsed.get("is_answerable")
    if is_answerable is None:
        is_answerable = parsed.get("is_related")
    is_answerable = bool(is_answerable)
    evidence_spans = parsed.get("evidence_spans", [])
    if not isinstance(evidence_spans, list):
        evidence_spans = [str(evidence_spans)]
    missing_info = parsed.get("missing_info", [])
    if not isinstance(missing_info, list):
        missing_info = [str(missing_info)]

    return {
        "is_related": is_answerable,
        "is_answerable": is_answerable,
        "confidence": float(parsed.get("confidence", 0.0)),
        "evidence_spans": [str(item) for item in evidence_spans],
        "missing_info": [str(item) for item in missing_info],
        "reason": str(parsed.get("reason", "")),
    }
