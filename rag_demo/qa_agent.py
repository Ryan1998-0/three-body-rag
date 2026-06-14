from typing import Callable, List

from rag_demo.chunking import Chunk
from rag_demo.model_providers import ask_model
from rag_demo.prompting import render_retrieved_context


QA_AGENT_SYSTEM_PROMPT = """你是 QA Agent。

你的任務是根據 Keyword Extraction Agent、Question Extraction Agent 與 retrieved chunks 回答問題。
只能根據提供的 retrieved chunks 回答，不可使用來源外資訊。
"""


def build_qa_prompt(
    original_question: str,
    refined_question: str,
    keywords: List[str],
    chunks: List[Chunk],
) -> str:
    return f"""你會收到 Question Extraction Agent 的輸出，以及 knowledge base retrieval 的 top chunks。

## Question Extraction Agent Output
{refined_question}

## Retrieved Chunks
{render_retrieved_context(chunks)}

## QA Agent Rules
- 請回答 Question Extraction Agent Output 中的真正問題。
- Question Extraction Agent Output 已經是完整問題；請直接回答，不要反問使用者要問什麼。
- 最終答案必須根據 Retrieved Chunks。
- 如果 Retrieved Chunks 沒有足夠 evidence，請明確回答「無法從來源確認」。
- 請使用繁體中文。
- 不要使用簡體字。
- 不要使用一般常識、模型內部知識或來源外資訊補答案。
- 如果答案引用來源，請標明來源編號與章節名稱。
- 不要加入結尾總結句。
"""


def answer_with_qa_agent(
    original_question: str,
    refined_question: str,
    keywords: List[str],
    chunks: List[Chunk],
    model: str = "qwen2.5:7b",
    ask_model_fn: Callable[..., str] = ask_model,
) -> str:
    return ask_model_fn(
        build_qa_prompt(
            original_question=original_question,
            refined_question=refined_question,
            keywords=keywords,
            chunks=chunks,
        ),
        model=model,
        system=QA_AGENT_SYSTEM_PROMPT,
    ).strip()
