# app/tools/delete_document.py
from ..retrieval import get_provider


def delete_document(corpus_name: str, document_id: str, confirm: bool = False) -> dict:
    """
    Removes a single document and its associated chunks from a corpus.

    Args:
        corpus_name: Full resource name or display name of the corpus.
        document_id: The ID of the document to delete.
        confirm: Must be True to proceed with deletion.
    """
    if not confirm:
        return {
            "status": "warning",
            "message": f"Deletion of document '{document_id}' requires explicit confirmation. Please set confirm=True.",
        }

    provider = get_provider()
    resolved = provider.resolve_corpus_name(corpus_name)
    if not resolved:
        return {
            "status": "error",
            "message": f"Corpus '{corpus_name}' does not exist.",
        }

    try:
        success = provider.delete_document(
            corpus_resource_name=resolved, doc_id=document_id, confirm=confirm
        )
        if success:
            return {
                "status": "success",
                "message": f"Document '{document_id}' successfully deleted from '{corpus_name}'.",
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to delete document '{document_id}'. It might not exist.",
            }
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Error deleting document: {exc}",
        }
