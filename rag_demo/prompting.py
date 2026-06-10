from typing import List

from rag_demo.chunking import Chunk


def build_answer_prompt(question: str, chunks: List[Chunk]) -> str:
    source_text = render_retrieved_context(chunks)

    return f"""你是一個本機 RAG 系統的回答模型。你的任務是根據 retrieval chunks 回答使用者問題。

使用者問：
{question}

請根據以下檢索資料回答。

## 檢索資料
{source_text}

## 回答規則
請只能根據下列來源回答使用者問題。
請使用繁體中文回答。
不要使用簡體字。
若來源沒有明確提到，請回答「無法從來源確認」。
不要使用一般常識補答案，因為這份員工手冊的制度可能故意不符合常識。
不要把已經有來源支持的內容列入無法確認。
無法確認只限於使用者問題本身，不要延伸評論其他未被詢問的議題。
可以在答案後簡短列出依據來源；不需要固定輸出第 2 點或第 3 點。
不能把推測內容當成已確認答案。
不要加入結尾總結句。
來源依據若有列出，必須包含對應的來源編號與章節名稱。
回答前必須逐一檢視每個檢索來源；如果多個來源都直接回答問題，答案必須整合所有相關來源，不要只回答第一個來源。
"""


def render_retrieved_context(chunks: List[Chunk]) -> str:
    if not chunks:
        return "沒有找到相關來源。"

    sources = []
    for index, chunk in enumerate(chunks, start=1):
        sources.append(
            "\n".join(
                [
                    f"[來源 {index}]",
                    f"文件：{chunk['source']}",
                    f"父層章節：{chunk.get('parent_title', '')}",
                    f"章節：{chunk['title']}",
                    "內容：",
                    str(chunk["content"]),
                ]
            )
        )

    return "\n\n".join(sources)
