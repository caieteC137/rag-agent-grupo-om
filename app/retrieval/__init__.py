# app/retrieval/__init__.py
#
# ARCHITECTURAL DECISION: Single import point.
# Tools import from here, never from provider implementations directly.
# Switching providers = change one env var, zero tool code changes.

from __future__ import annotations

import os
from typing import Union

from .provider import (
    CorpusInfo,
    DocumentInfo,
    IngestResult,
    RetrievalProvider,
    RetrievalResult,
)

_PROVIDER_INSTANCE: RetrievalProvider | None = None


def get_provider() -> RetrievalProvider:
    """
    Lazy singleton. Returns the configured provider.

    Provider selection via RETRIEVAL_PROVIDER env var:
      "rag_engine"    → RagEngineProvider  (current default, zero risk)
      "vertex_vs"     → VertexVectorSearchProvider  (new)
      "mock"          → MockProvider  (testing)
    """
    global _PROVIDER_INSTANCE
    if _PROVIDER_INSTANCE is not None:
        return _PROVIDER_INSTANCE

    backend = os.getenv("RETRIEVAL_PROVIDER", "rag_engine").lower()

    if backend == "rag_engine":
        from .rag_engine_provider import RagEngineProvider
        _PROVIDER_INSTANCE = RagEngineProvider()

    elif backend == "vertex_vs":
        from .vertex_vector_search_provider import VertexVectorSearchProvider
        _PROVIDER_INSTANCE = VertexVectorSearchProvider()

    elif backend == "mock":
        from .mock_provider import MockProvider
        _PROVIDER_INSTANCE = MockProvider()

    else:
        raise ValueError(
            f"Unknown RETRIEVAL_PROVIDER='{backend}'. "
            "Valid values: rag_engine, vertex_vs, mock"
        )

    return _PROVIDER_INSTANCE


__all__ = [
    "get_provider",
    "CorpusInfo",
    "DocumentInfo",
    "IngestResult",
    "RetrievalProvider",
    "RetrievalResult",
]