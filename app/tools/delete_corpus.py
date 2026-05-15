# app/tools/delete_corpus.py
from ..retrieval import get_provider


def delete_corpus(corpus_name: str, confirm: bool = False) -> dict:
    """
    Permanently deletes an entire document corpus and all its files.

    Args:
        corpus_name: Full resource name or display name of the corpus to delete.
        confirm: Must be True to proceed with deletion.
    """
    if not confirm:
        return {
            "status": "warning",
            "message": f"Deletion of corpus '{corpus_name}' requires explicit confirmation. Please set confirm=True.",
        }

    provider = get_provider()
    resolved = provider.resolve_corpus_name(corpus_name)
    if not resolved:
        return {
            "status": "error",
            "message": f"Corpus '{corpus_name}' does not exist.",
        }

    try:
        success = provider.delete_corpus(corpus_resource_name=resolved, confirm=confirm)
        if success:
            return {
                "status": "success",
                "message": f"Corpus '{corpus_name}' and all its contents have been permanently deleted.",
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to delete corpus '{corpus_name}'.",
            }
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Error deleting corpus: {exc}",
        }
