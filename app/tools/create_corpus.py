# app/tools/create_corpus.py
from ..retrieval import get_provider


def create_corpus(corpus_name: str) -> dict:
    """
    Creates a new, empty document corpus.

    Args:
        corpus_name: Descriptive display name for the new corpus.
    """
    provider = get_provider()
    try:
        info = provider.create_corpus(display_name=corpus_name)
        return {
            "status": "success",
            "message": f"Successfully created corpus '{corpus_name}'",
            "corpus_name": info.resource_name,
            "display_name": info.display_name,
        }
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Failed to create corpus '{corpus_name}': {exc}",
        }
