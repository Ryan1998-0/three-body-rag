from pathlib import Path
from typing import Dict, List

from rag_demo.config import RagConfig


Chunk = Dict[str, object]


def chunk_markdown(markdown_text: str, source: str) -> List[Chunk]:
    chunks: List[Chunk] = []
    current_parent_title = ""
    current_title = None
    current_lines: List[str] = []
    chunk_index = 0

    for line in markdown_text.splitlines():
        if line.startswith("## ") and not line.startswith("### "):
            if current_title and current_lines:
                chunks.append(
                    _make_chunk(
                        source,
                        chunk_index,
                        current_parent_title,
                        current_title,
                        current_lines,
                    )
                )
                chunk_index += 1
                current_title = None
                current_lines = []
            current_parent_title = line.removeprefix("## ").strip()
            continue

        if line.startswith("### "):
            if current_title and current_lines:
                chunks.append(
                    _make_chunk(
                        source,
                        chunk_index,
                        current_parent_title,
                        current_title,
                        current_lines,
                    )
                )
                chunk_index += 1
            current_title = line.removeprefix("### ").strip()
            current_lines = []
            continue

        if current_title:
            current_lines.append(line)

    if current_title and current_lines:
        chunks.append(
            _make_chunk(
                source,
                chunk_index,
                current_parent_title,
                current_title,
                current_lines,
            )
        )

    return chunks


def load_markdown_chunks(raw_dir: Path) -> List[Chunk]:
    chunks: List[Chunk] = []
    for path in sorted(raw_dir.glob("*.md")):
        chunks.extend(chunk_markdown(path.read_text(encoding="utf-8"), source=str(path)))
    return chunks


def chunk_avalon_record_text(
    record_text: str,
    source: str,
    chunk_size: int = None,
    chunk_stride: int = None,
) -> List[Chunk]:
    config = RagConfig.from_env()
    chunk_size = chunk_size or config.chunk_size
    chunk_stride = chunk_stride or config.chunk_stride
    chunks: List[Chunk] = []
    current_title = None
    current_lines: List[str] = []
    chunk_index = 0

    for line in record_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("=== 第") and stripped.endswith("==="):
            if current_title and current_lines:
                chunk_index = _append_sized_chunks(
                    chunks,
                    source,
                    chunk_index,
                    "阿瓦隆對局紀錄",
                    current_title,
                    current_lines,
                    chunk_size,
                    chunk_stride,
                )
            current_title = stripped.strip("= ").strip()
            current_lines = []
            continue

        if current_title:
            if not stripped.startswith("=========="):
                current_lines.append(line)

    if current_title and current_lines:
        _append_sized_chunks(
            chunks,
            source,
            chunk_index,
            "阿瓦隆對局紀錄",
            current_title,
            current_lines,
            chunk_size,
            chunk_stride,
        )

    return chunks


def load_knowledge_base_chunks(kb_dir: Path) -> List[Chunk]:
    config = RagConfig.from_env()
    chunks: List[Chunk] = []
    for path in sorted(kb_dir.glob("*.md")):
        chunks.extend(chunk_markdown(path.read_text(encoding="utf-8"), source=str(path)))
    for path in sorted(kb_dir.glob("*formatted.txt")):
        chunks.extend(
            chunk_avalon_record_text(
                path.read_text(encoding="utf-8"),
                source=str(path),
                chunk_size=config.chunk_size,
                chunk_stride=config.chunk_stride,
            )
        )
    return chunks


def _make_chunk(
    source: str,
    chunk_index: int,
    parent_title: str,
    title: str,
    lines: List[str],
) -> Chunk:
    content = "\n".join(line for line in lines).strip()
    return _make_chunk_from_content(source, chunk_index, parent_title, title, content)


def _make_chunk_from_content(
    source: str,
    chunk_index: int,
    parent_title: str,
    title: str,
    content: str,
) -> Chunk:
    return {
        "id": f"{Path(source).name}::{chunk_index}",
        "source": source,
        "chunk_index": chunk_index,
        "parent_title": parent_title,
        "title": title,
        "content": content,
    }


def _append_sized_chunks(
    chunks: List[Chunk],
    source: str,
    start_index: int,
    parent_title: str,
    title: str,
    lines: List[str],
    chunk_size: int,
    chunk_stride: int,
) -> int:
    content = "\n".join(line for line in lines).strip()
    if len(content) <= chunk_size:
        chunks.append(_make_chunk_from_content(source, start_index, parent_title, title, content))
        return start_index + 1

    index = start_index
    part = 1
    start = 0
    while start < len(content):
        piece = content[start : start + chunk_size].strip()
        if piece:
            chunks.append(
                _make_chunk_from_content(
                    source,
                    index,
                    parent_title,
                    f"{title} / part {part}",
                    piece,
                )
            )
            index += 1
            part += 1
        if start + chunk_size >= len(content):
            break
        start += chunk_stride
    return index
