# src/kb_index.py
"""Knowledge-base RAG index.
Loads all Markdown docs, chunks by '---' separators, embeds with
Gemini embedding-001, stores in ChromaDB (in-memory, no disk needed)."""

import os
import re
from pathlib import Path
from typing import Optional
import chromadb
from chromadb import EmbeddingFunction, Documents, Embeddings
import google.generativeai as genai

KB_DIR = Path(__file__).parent.parent / "knowledge-base"
KB_FILES: list[Path] = list(KB_DIR.rglob("*.md"))


class GeminiEmbeddingFunction(EmbeddingFunction):
    """Custom ChromaDB Embedding Function using Google Gemini embed_content."""

    def __init__(self, api_key: Optional[str] = None, model_name: str = "models/gemini-embedding-001"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name

    def __call__(self, input: Documents) -> Embeddings:
        if self.api_key:
            genai.configure(api_key=self.api_key)
        embeddings = []
        for text in input:
            try:
                res = genai.embed_content(
                    model=self.model_name,
                    content=text,
                    task_type="retrieval_document"
                )
                embeddings.append(res["embedding"])
            except Exception as e:
                print(f"[Embedding Warning] Failed to embed snippet: {e}")
                embeddings.append([0.0] * 768)
        return embeddings


PERSIST_DIR = Path(__file__).parent.parent / "chroma_db"
_chroma_client = chromadb.PersistentClient(path=str(PERSIST_DIR))
_embed_fn: Optional[GeminiEmbeddingFunction] = None
_collection: Optional[chromadb.Collection] = None


def _chunk_markdown(text: str, source: str) -> list[dict]:
    chunks = []
    sections = re.split(r'\n---+\n', text)
    for i, section in enumerate(sections):
        section = section.strip()
        if len(section) < 50:
            continue
        heading_match = re.search(r'^#{1,3}\s+(.+)', section, re.MULTILINE)
        heading = heading_match.group(1) if heading_match else f"Section {i}"
        chunks.append({
            "text": section,
            "source": source,
            "heading": heading,
            "chunk_id": f"{source}::chunk_{i}",
        })
    return chunks


def build_index(api_key: str, force_rebuild: bool = False) -> None:
    global _collection, _embed_fn
    _embed_fn = GeminiEmbeddingFunction(
        api_key=api_key,
        model_name="models/gemini-embedding-001",
    )
    if not force_rebuild:
        try:
            _collection = _chroma_client.get_collection(
                name="knowledge_base",
                embedding_function=_embed_fn,
            )
            count = _collection.count()
            if count > 0:
                print(f"[KB Index] Loaded existing persistent index with {count} chunks.")
                return
        except Exception:
            pass

    try:
        _chroma_client.delete_collection("knowledge_base")
    except Exception:
        pass
    _collection = _chroma_client.create_collection(
        name="knowledge_base",
        embedding_function=_embed_fn,
    )
    all_chunks = []
    for kb_file in KB_FILES:
        relative = kb_file.relative_to(KB_DIR)
        source = str(relative)
        text = kb_file.read_text(encoding="utf-8")
        chunks = _chunk_markdown(text, source)
        all_chunks.extend(chunks)
    if not all_chunks:
        raise RuntimeError("No KB chunks generated — check knowledge-base/ directory.")
    _collection.add(
        documents=[c["text"] for c in all_chunks],
        metadatas=[{"source": c["source"], "heading": c["heading"]} for c in all_chunks],
        ids=[c["chunk_id"] for c in all_chunks],
    )
    print(f"[KB Index] Built with {len(all_chunks)} chunks from {len(KB_FILES)} files.")


def search_kb(query: str, top_k: int = 3) -> list[dict]:
    if _collection is None:
        raise RuntimeError("KB index not built. Call build_index() first.")
    results = _collection.query(
        query_texts=[query],
        n_results=min(top_k, _collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    output = []
    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0]
    for doc, meta, dist in zip(docs, metas, distances):
        output.append({
            "text": doc,
            "source": meta.get("source", ""),
            "heading": meta.get("heading", ""),
            "score": round(1 - dist, 4),
        })
    return output

