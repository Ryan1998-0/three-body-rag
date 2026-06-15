import json
import os
from pathlib import Path


DEFAULT_GRAPH_PATH = "data/graph/three_body_graph.json"


def load_graph(path: Path = None, project_root: Path = None):
    graph_path = path or _default_graph_path(project_root=project_root)
    if not graph_path.exists():
        return {"entities": [], "relations": []}
    loaded = json.loads(graph_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"Graph file must contain a JSON object: {graph_path}")
    loaded.setdefault("entities", [])
    loaded.setdefault("relations", [])
    return loaded


def _default_graph_path(project_root: Path = None) -> Path:
    configured = os.getenv("RAG_GRAPH_PATH")
    if configured:
        return Path(configured).expanduser()
    root = project_root or Path(__file__).resolve().parents[1]
    return root / DEFAULT_GRAPH_PATH
