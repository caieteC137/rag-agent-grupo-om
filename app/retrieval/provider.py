# app/retrieval/provider.py
#
# ARCHITECTURAL DECISION: Define the retrieval contract as a Python Protocol
# (structural subtyping) rather than an ABC. This means any class with matching
# method signatures satisfies the interface without explicit inheritance —
# easier testing with mocks, no coupling to base classes.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


# ─────────────────────────────────────────────────────────────────────────────
# Data Transfer Objects
# These are pure data classes with no dependency on any external SDK.
# Providers translate SDK-specific objects into these DTOs.
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CorpusInfo:
    """Canonical representation of a document corpus / collection."""
    resource_name: str        # Unique identifier (provider-specific URI)
    display_name: str
    create_time: str = ""
    update_time: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentInfo:
    """Canonical representation of a document inside a corpus."""
    doc_id: str
    corpus_resource_name: str
    display_name: str = ""
    source_uri: str = ""
    gcs_path: str = ""
    create_time: str = ""
    update_time: str = ""
    chunk_ids: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """A single retrieved chunk with provenance information."""
    text: str
    source_uri: str = ""
    source_name: str = ""
    score: float = 0.0
    doc_id: str = ""
    chunk_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class IngestResult:
    """Result of ingesting one or more documents."""
    success: bool
    corpus_resource_name: str
    doc_ids: list[str] = field(default_factory=list)
    failed_sources: list[str] = field(default_factory=list)
    error: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# The Provider Protocol
# Implementors: RagEngineProvider, VertexVectorSearchProvider, MockProvider
# ─────────────────────────────────────────────────────────────────────────────

@runtime_checkable
class RetrievalProvider(Protocol):
    """
    Abstract contract for all retrieval backends.

    DESIGN PRINCIPLES:
    - Methods match 1:1 with the ADK tool surface (no leaky abstractions)
    - All I/O is synchronous to match ADK tool execution model
    - Errors are returned in result objects, not raised, so tools can
      format messages for the LLM rather than crashing
    """

    # ── Corpus / Collection management ──────────────────────────────────────

    def list_corpora(self) -> list[CorpusInfo]:
        """Return all corpora/collections visible to this provider."""
        ...

    def create_corpus(self, display_name: str) -> CorpusInfo:
        """Create an empty corpus and return its info."""
        ...

    def delete_corpus(self, corpus_resource_name: str, confirm: bool) -> bool:
        """
        Permanently delete a corpus.
        `confirm=True` is required as a safety gate — the caller (tool)
        must have obtained explicit user consent before setting this.
        """
        ...

    # ── Document management ─────────────────────────────────────────────────

    def get_corpus_info(self, corpus_resource_name: str) -> CorpusInfo | None:
        """Return corpus metadata including file list."""
        ...

    def list_documents(self, corpus_resource_name: str) -> list[DocumentInfo]:
        """List all documents in a corpus."""
        ...

    def ingest(
        self,
        corpus_resource_name: str,
        paths: list[str],          # GCS URIs or Google Drive URLs
    ) -> IngestResult:
        """
        Ingest one or more documents into the corpus.
        Each path can be a GCS URI (gs://...) or Google Drive URL.
        """
        ...

    def delete_document(
        self,
        corpus_resource_name: str,
        doc_id: str,
        confirm: bool,
    ) -> bool:
        """Remove a single document and all its chunks."""
        ...

    def update_document(
        self,
        corpus_resource_name: str,
        doc_id: str,
        paths: list[str],
    ) -> IngestResult:
        """Re-ingest a document (delete old chunks, ingest new version)."""
        ...

    # ── Retrieval ────────────────────────────────────────────────────────────

    def search(
        self,
        corpus_resource_name: str,
        query: str,
        top_k: int = 10,
        distance_threshold: float = 0.5,
    ) -> list[RetrievalResult]:
        """
        Semantic search over the corpus.
        Returns up to `top_k` results with score >= (1 - distance_threshold).
        """
        ...

    # ── Utility ──────────────────────────────────────────────────────────────

    def resolve_corpus_name(self, name_or_display: str) -> str | None:
        """
        Given a display name OR resource name, return the canonical
        resource name. Returns None if not found.
        This replaces tools/utils.py::get_corpus_resource_name().
        """
        ...

    def corpus_exists(self, corpus_resource_name: str) -> bool:
        """Fast existence check without full metadata fetch."""
        ...