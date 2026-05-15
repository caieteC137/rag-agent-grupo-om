# app/tools/rag_query.py  (refactored)
#
# CHANGE: Replaced direct vertexai.rag calls with provider.search().
# All SDK-specific logic is now inside the provider. This file only
# handles: input validation, tool_context state, and output formatting.

import logging

from google.adk.tools.tool_context import ToolContext

from ..config import DEFAULT_DISTANCE_THRESHOLD, DEFAULT_TOP_K
from ..retrieval import get_provider

logger = logging.getLogger(__name__)


def rag_query(
    corpus_name: str,
    query: str,
    tool_context: ToolContext,
) -> dict:
    """
    Query a Vertex AI RAG corpus with a user question.

    Args:
        corpus_name: Full resource name OR display name of the corpus.
        query:       Natural language question.
        tool_context: ADK tool context for state management.

    Returns:
        dict with status, results, and metadata.
    """
    provider = get_provider()

    # ── Resolve corpus name ──────────────────────────────────────────────────
    resolved = provider.resolve_corpus_name(corpus_name)
    if not resolved:
        return {
            "status": "error",
            "message": (
                f"Corpus '{corpus_name}' does not exist. "
                "Please create it first using the create_corpus tool."
            ),
            "query": query,
            "corpus_name": corpus_name,
        }

    # ── Track current corpus in session state ────────────────────────────────
    if not tool_context.state.get("current_corpus"):
        tool_context.state["current_corpus"] = resolved

    # ── Execute search ───────────────────────────────────────────────────────
    logger.info("Querying corpus %s with: %s", resolved, query[:80])
    results = provider.search(
        corpus_resource_name=resolved,
        query=query,
        top_k=DEFAULT_TOP_K,
        distance_threshold=DEFAULT_DISTANCE_THRESHOLD,
    )

    if not results:
        return {
            "status": "warning",
            "message": (
                f"No results found in corpus '{corpus_name}' "
                f"for query: '{query}'"
            ),
            "query": query,
            "corpus_name": corpus_name,
            "results": [],
            "results_count": 0,
        }

    return {
        "status": "success",
        "message": f"Successfully queried corpus '{corpus_name}'",
        "query": query,
        "corpus_name": corpus_name,
        "results": [
            {
                "source_uri": r.source_uri,
                "source_name": r.source_name,
                "text": r.text,
                "score": r.score,
                "doc_id": r.doc_id,
                "chunk_id": r.chunk_id,
            }
            for r in results
        ],
        "results_count": len(results),
    }