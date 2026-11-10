"""Wiring: build the index, retriever and LLM from settings (used by the API, CLIs and tests)."""

from __future__ import annotations

from dataclasses import dataclass

from kestrel_docs.adapters.embeddings import build_embedder
from kestrel_docs.adapters.llm import LLMClient, build_llm
from kestrel_docs.config import Settings
from kestrel_docs.domain.documents import load_corpus
from kestrel_docs.domain.rerank import CrossEncoderReranker, LexicalOverlapReranker, NoReranker, Reranker
from kestrel_docs.domain.retrieval import HandbookIndex, Retriever


@dataclass
class Services:
    settings: Settings
    index: HandbookIndex
    retriever: Retriever
    llm: LLMClient


def build_reranker(settings: Settings) -> Reranker:
    if settings.reranker == "cross-encoder":
        return CrossEncoderReranker()
    if settings.reranker == "none":
        return NoReranker()
    return LexicalOverlapReranker()


def build_services(settings: Settings) -> Services:
    docs = load_corpus(settings.resolved_handbook_dir())
    index = HandbookIndex(docs, build_embedder(settings), settings.chunk_size, settings.chunk_overlap)
    retriever = Retriever(index, build_reranker(settings), settings.candidates_per_retriever)
    return Services(settings, index, retriever, build_llm(settings))
