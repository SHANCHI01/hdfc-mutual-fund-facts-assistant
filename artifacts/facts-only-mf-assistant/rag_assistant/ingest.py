"""Build sanitized raw corpus, inspectable chunks/embeddings, and persistent Chroma."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .chunking import make_chunks
from .retrieval import _chroma, rebuild_collection
from .sources import EMBEDDING_MODEL, find_repo_root, load_sources


def build(data_dir: Path | None = None, repo_root: Path | None = None) -> int:
    root = repo_root or find_repo_root()
    output = data_dir or Path(__file__).resolve().parents[1] / "data"
    raw_dir = output / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    sources = load_sources(root)
    for source in sources:
        (raw_dir / f'{source["id"]}.json').write_text(
            json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    chunks = make_chunks(sources)
    (output / "chunks.jsonl").write_text(
        "".join(json.dumps(chunk, ensure_ascii=False) + "\n" for chunk in chunks),
        encoding="utf-8",
    )

    _, embedding_function = _chroma()
    vectors = embedding_function([chunk["text"] for chunk in chunks])
    with (output / "embeddings.txt").open("w", encoding="utf-8") as handle:
        handle.write(f"Embedding model: {EMBEDDING_MODEL}\n")
        handle.write(
            "Implementation: Chroma DefaultEmbeddingFunction, ONNX all-MiniLM-L6-v2\n"
        )
        handle.write(f"Vectors: {len(vectors)}\n\n")
        for chunk, vector in zip(chunks, vectors):
            handle.write(f'[{chunk["id"]}] ({len(vector)} dimensions)\n')
            handle.write("[" + ", ".join(f"{value:.8f}" for value in vector) + "]\n\n")

    rebuild_collection(output, chunks)
    return len(chunks)


if __name__ == "__main__":
    print(f"Built {build()} chunks.")
