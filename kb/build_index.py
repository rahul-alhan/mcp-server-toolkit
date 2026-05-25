"""Chunk + embed + persist to Chroma."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

COLLECTION = "kb_main"


def build(docs_dir: str, persist_dir: str):
    paths = list(Path(docs_dir).rglob("*.md")) + list(Path(docs_dir).rglob("*.txt"))
    docs = []
    for p in paths:
        docs.extend(TextLoader(str(p), encoding="utf-8").load())

    splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=50)
    chunks = splitter.split_documents(docs)
    for i, c in enumerate(chunks):
        c.metadata.setdefault("source", Path(c.metadata.get("source", paths[0])).name)
        c.metadata["chunk_id"] = i

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vec = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=persist_dir,
        collection_name=COLLECTION,
    )
    print(f"Indexed {len(chunks)} chunks from {len(paths)} docs → {persist_dir}")
    return vec


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--docs", default="docs")
    p.add_argument("--persist", default=os.getenv("KB_CHROMA_DIR", ".chroma"))
    args = p.parse_args()
    build(args.docs, args.persist)


if __name__ == "__main__":
    main()
