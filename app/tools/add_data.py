# app/tools/add_data.py
from ..retrieval import get_provider


def add_data(corpus_name: str, paths: list[str]) -> dict:
    """
    Ingests documents into a corpus.

    Args:
        corpus_name: Full resource name or display name of the target corpus.
        paths: List of file paths to ingest (GCS gs://... or local paths).
    """
    provider = get_provider()
    
    resolved = provider.resolve_corpus_name(corpus_name)
    if not resolved:
        return {
            "status": "error",
            "message": f"Corpus '{corpus_name}' does not exist. Create it first.",
        }

    try:
        result = provider.ingest(corpus_resource_name=resolved, paths=paths)
        if result.success:
            return {
                "status": "success",
                "message": f"Successfully ingested {len(result.doc_ids)} documents into '{corpus_name}'",
                "doc_ids": result.doc_ids,
            }
        else:
            return {
                "status": "error",
                "message": f"Ingestion partially failed for '{corpus_name}'",
                "failed_sources": result.failed_sources,
                "error": result.error,
            }
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Unexpected error during ingestion: {exc}",
        }
