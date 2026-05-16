# app/retrieval/rag_engine_provider.py
#
# ARCHITECTURAL DECISION: This is a SHIM — it delegates 100% to the
# existing vertexai.rag SDK. No logic changes, only translation between
# SDK types ↔ our DTOs. Once the new provider is validated in production,
# this file is deleted.

from __future__ import annotations

import logging
import os
import re

from vertexai import rag

from .provider import (
    CorpusInfo,
    DocumentInfo,
    IngestResult,
    RetrievalProvider,
    RetrievalResult,
)

logger = logging.getLogger(__name__)

_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")
_LOCATION = os.getenv("RAG_ENGINE_LOCATION") or os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")


def _resource_name_pattern() -> re.Pattern[str]:
    return re.compile(
        r"^projects/[^/]+/locations/[^/]+/ragCorpora/[^/]+$"
    )


class RagEngineProvider:
    """
    Wraps vertexai.rag in the RetrievalProvider protocol.

    This class contains ZERO new logic — every method is a thin translation
    layer between the RAG Engine SDK and our canonical DTOs. If the SDK
    behaviour changes, only this file needs updating.
    """

    def __init__(self, location: str | None = None) -> None:
        self.location = location or _LOCATION
        # Ensure vertexai is initialized for this location
        import vertexai
        vertexai.init(project=_PROJECT, location=self.location)

    # ── helpers ─────────────────────────────────────────────────────────────

    def _to_resource_name(self, name: str) -> str:
        """Resolve display name → resource name, same logic as utils.py."""
        if _resource_name_pattern().match(name):
            return name
        # Try display name lookup
        try:
            for corpus in rag.list_corpora():
                if getattr(corpus, "display_name", None) == name:
                    return corpus.name
        except Exception:
            pass
        # Fall back to constructing the name (legacy behaviour)
        corpus_id = name.split("/")[-1] if "/" in name else name
        corpus_id = re.sub(r"[^a-zA-Z0-9_-]", "_", corpus_id)
        return (
            f"projects/{_PROJECT}/locations/{self.location}"
            f"/ragCorpora/{corpus_id}"
        )

    # ── Corpus management ────────────────────────────────────────────────────

    def list_corpora(self) -> list[CorpusInfo]:
        try:
            return [
                CorpusInfo(
                    resource_name=c.name,
                    display_name=getattr(c, "display_name", ""),
                    create_time=str(getattr(c, "create_time", "")),
                    update_time=str(getattr(c, "update_time", "")),
                )
                for c in rag.list_corpora()
            ]
        except Exception as exc:
            logger.error("list_corpora failed: %s", exc)
            return []

    def create_corpus(self, display_name: str) -> CorpusInfo:
        corpus = rag.create_corpus(display_name=display_name)
        return CorpusInfo(
            resource_name=corpus.name,
            display_name=getattr(corpus, "display_name", display_name),
        )

    def delete_corpus(self, corpus_resource_name: str, confirm: bool) -> bool:
        if not confirm:
            return False
        try:
            rag.delete_corpus(name=corpus_resource_name)
            return True
        except Exception as exc:
            logger.error("delete_corpus failed: %s", exc)
            return False

    def get_corpus_info(self, corpus_resource_name: str) -> CorpusInfo | None:
        resource_name = self._to_resource_name(corpus_resource_name)
        try:
            docs = self.list_documents(resource_name)
            return CorpusInfo(
                resource_name=resource_name,
                display_name=corpus_resource_name,
                metadata={"file_count": len(docs)},
            )
        except Exception as exc:
            logger.error("get_corpus_info failed: %s", exc)
            return None

    # ── Document management ──────────────────────────────────────────────────

    def list_documents(self, corpus_resource_name: str) -> list[DocumentInfo]:
        try:
            return [
                DocumentInfo(
                    doc_id=f.name.split("/")[-1],
                    corpus_resource_name=corpus_resource_name,
                    display_name=getattr(f, "display_name", ""),
                    source_uri=getattr(f, "source_uri", ""),
                    create_time=str(getattr(f, "create_time", "")),
                    update_time=str(getattr(f, "update_time", "")),
                )
                for f in rag.list_files(corpus_resource_name)
            ]
        except Exception as exc:
            logger.error("list_documents failed: %s", exc)
            return []

    def ingest(
        self,
        corpus_resource_name: str,
        paths: list[str],
    ) -> IngestResult:
        # RAG Engine uses rag.upload_file / import_files depending on source
        # This is a simplified shim — expand as needed.
        try:
            rag.import_files(
                corpus_name=corpus_resource_name,
                paths=paths,
            )
            return IngestResult(
                success=True,
                corpus_resource_name=corpus_resource_name,
            )
        except Exception as exc:
            logger.error("ingest failed: %s", exc)
            return IngestResult(
                success=False,
                corpus_resource_name=corpus_resource_name,
                error=str(exc),
            )

    def delete_document(
        self,
        corpus_resource_name: str,
        doc_id: str,
        confirm: bool,
    ) -> bool:
        if not confirm:
            return False
        file_name = f"{corpus_resource_name}/ragFiles/{doc_id}"
        try:
            rag.delete_file(name=file_name)
            return True
        except Exception as exc:
            logger.error("delete_document failed: %s", exc)
            return False

    def update_document(
        self,
        corpus_resource_name: str,
        doc_id: str,
        paths: list[str],
    ) -> IngestResult:
        self.delete_document(corpus_resource_name, doc_id, confirm=True)
        return self.ingest(corpus_resource_name, paths)

    # ── Retrieval ────────────────────────────────────────────────────────────

    def search(
        self,
        corpus_resource_name: str,
        query: str,
        top_k: int = 10,
        distance_threshold: float = 0.5,
    ) -> list[RetrievalResult]:
        config = rag.RagRetrievalConfig(
            top_k=top_k,
            filter=rag.Filter(
                vector_distance_threshold=distance_threshold
            ),
        )
        try:
            response = rag.retrieval_query(
                rag_resources=[
                    rag.RagResource(rag_corpus=corpus_resource_name)
                ],
                text=query,
                rag_retrieval_config=config,
            )
        except Exception as exc:
            logger.error("search failed: %s", exc)
            return []

        results = []
        if response.contexts and response.contexts.contexts:
            for ctx in response.contexts.contexts:
                results.append(
                    RetrievalResult(
                        text=getattr(ctx, "text", ""),
                        source_uri=getattr(ctx, "source_uri", ""),
                        source_name=getattr(ctx, "source_display_name", ""),
                        score=getattr(ctx, "score", 0.0),
                    )
                )
        return results

    # ── Utility ──────────────────────────────────────────────────────────────

    def resolve_corpus_name(self, name_or_display: str) -> str | None:
        resource = self._to_resource_name(name_or_display)
        if self.corpus_exists(resource):
            return resource
        return None

    def corpus_exists(self, corpus_resource_name: str) -> bool:
        resource = self._to_resource_name(corpus_resource_name)
        try:
            for c in rag.list_corpora():
                if c.name == resource or getattr(c, "display_name", "") == corpus_resource_name:
                    return True
        except Exception:
            pass
        return False