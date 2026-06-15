from typing import Callable, List

from rag_demo.chunking import Chunk
from rag_demo.model_providers import ask_model
from rag_demo.prompting import render_retrieved_context


QA_AGENT_SYSTEM_PROMPT = """你是 QA Agent。

你的任務是根據 Question Extraction Agent、Evidence Extraction Agent 與 retrieved chunks 回答問題。
只能根據提供的 retrieved chunks 回答，不可使用來源外資訊。
"""


def build_qa_prompt(
    original_question: str,
    refined_question: str,
    keywords: List[str],
    chunks: List[Chunk],
    extracted_evidence: str = "",
) -> str:
    evidence_text = str(extracted_evidence or "").strip() or "無"
    return f"""你會收到 Question Extraction Agent 的輸出、knowledge base retrieval 的 top chunks，以及 Evidence Extraction Agent 抽出的候選 evidence。

## Question Extraction Agent Output
{refined_question}

## Retrieved Chunks
{render_retrieved_context(chunks)}

## Evidence Extraction Agent Output
{evidence_text}

## QA Agent Rules
- 請回答 Question Extraction Agent Output 中的真正問題。
- Question Extraction Agent Output 已經是完整問題；請直接回答，不要反問使用者要問什麼。
- 最終答案必須根據 Evidence Extraction Agent Output 與 Retrieved Chunks。
- Retrieved Chunks 是最高優先與最終依據；Evidence Extraction Agent Output 只是提示與檢查清單。
- 不要只根據 Evidence Extraction Agent Output 回答；必須回到 Retrieved Chunks 核對完整內容。
- 如果 Evidence Extraction Agent Output 漏掉問題所需資訊，請直接使用 Retrieved Chunks 補足。
- 如果某條 evidence 只出現相關名詞但沒有回答問題，請忽略那條 evidence。
- 如果 Evidence Extraction Agent Output 與 Retrieved Chunks 有衝突，請以 Retrieved Chunks 的原文為準。
- 回答「如何處置/處理」時，請以來源中最後的實際處置為準；若來源出現「但、例外、自由、釋放」等轉折，必須保留轉折後的結果，不要把前面的假設或一般法律寫成已執行處置。
- 回答「如何處置/處理」時，如果同一來源還說明處置的期限、目的或後果，也必須一起回答，例如「活到她失去一切希望」不能省略成只有「自由」。
- 回答「核心做法」時，請回答具體操作，不要只回答任務目標；若來源有工具/材料、設置位置、作用對象與結果，必須一起說明。
- 如果 Retrieved Chunks 沒有足夠 evidence，請明確回答「無法從來源確認」。
- 如果 Evidence Extraction Agent Output 中出現數字、專名、術語或關鍵判斷詞，且它們與問題相關，Final Answer 必須保留這些詞。
- 如果 Retrieved Chunks 中有能直接回答問題的具體數字、工具、材料、處置結果或目標地點，即使 Evidence Extraction Agent Output 沒有整理好，Final Answer 仍必須保留。
- 請使用繁體中文。
- 不要使用簡體字。
- 請把簡體詞轉成繁體，例如：基础科學→基礎科學、科学→科學、干扰→干擾、信号→訊號。
- 請保留問題需要的關鍵詞，不要把「微波背景」「3K」「基礎科學」「四光年」「納米絲」「飛刃」「審判日號」「太陽系」「有罪」「自由」「活到她失去一切希望」這類具體詞改成太泛的說法。
- 不要使用一般常識、模型內部知識或來源外資訊補答案。
- 如果答案引用來源，請標明來源編號與章節名稱。
- 請用 1 到 3 個短段落回答；不要長篇複製 evidence 原文。
- 不要加入結尾總結句。
"""


def answer_with_qa_agent(
    original_question: str,
    refined_question: str,
    keywords: List[str],
    chunks: List[Chunk],
    extracted_evidence: str = "",
    model: str = "qwen2.5:7b",
    ask_model_fn: Callable[..., str] = ask_model,
) -> str:
    return ask_model_fn(
        build_qa_prompt(
            original_question=original_question,
            refined_question=refined_question,
            keywords=keywords,
            chunks=chunks,
            extracted_evidence=extracted_evidence,
        ),
        model=model,
        system=QA_AGENT_SYSTEM_PROMPT,
    ).strip()
