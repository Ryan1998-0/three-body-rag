# Knowledge Base Interface

本專案的 knowledge base 由 `rag_demo/knowledge_base.py` 統一管理。核心 RAG pipeline 不應直接寫死某一個 corpus 的 raw path、index path、alias path 或 graph path。

## Profile Layout

建議每一個 knowledge base 使用一個 profile：

```text
profiles/<profile_name>/
  raw/
  index/
  entities/
    aliases.json
  graph/
    graph.json
```

啟用方式：

```bash
export RAG_PROFILE=fire_law
python3 -m rag_demo.ingest
python3 -m rag_demo.query '你的問題'
```

啟用後會自動使用：

```text
profiles/fire_law/raw/
profiles/fire_law/index/
profiles/fire_law/entities/aliases.json
profiles/fire_law/graph/graph.json
```

## Manifest

如果 profile 不想使用標準目錄，可以放一個 `knowledge_base.json`：

```json
{
  "raw_dir": "../../data/raw",
  "index_dir": "../../data/index",
  "alias_path": "../../data/entities/aliases.json",
  "graph_path": "../../data/graph/graph.json"
}
```

相對路徑會以該 profile 目錄為基準。

## Environment Overrides

以下環境變數會優先於 profile 與 manifest：

```bash
export RAG_KB_DIR=/path/to/raw
export RAG_INDEX_DIR=/path/to/index
export RAG_ENTITY_ALIASES=/path/to/aliases.json
export RAG_GRAPH_PATH=/path/to/graph.json
```

## Default Behavior

未設定 `RAG_PROFILE` 時，系統使用 generic default：

```text
data/raw/
data/index/
data/entities/default_aliases.json
data/graph/graph.json
```

其中 alias 與 graph 檔案不存在時會被視為空資料，不會自動套用任何特定 corpus 的人物、組織或關係資料。
