# app/tools/get_corpus_info.py  (refactored)
from google.adk.tools.tool_context import ToolContext
from ..retrieval import get_provider


def get_corpus_info(corpus_name: str, tool_context: ToolContext) -> dict:
    provider = get_provider()

    resolved = provider.resolve_corpus_name(corpus_name)
    if not resolved:
        return {
            "status": "error",
            "message": f"Corpus '{corpus_name}' does not exist",
            "corpus_name": corpus_name,
        }

    info = provider.get_corpus_info(resolved)
    if not info:
        return {
            "status": "error",
            "message": f"Could not retrieve info for '{corpus_name}'",
            "corpus_name": corpus_name,
        }

    docs = provider.list_documents(resolved)

    return {
        "status": "success",
        "message": f"Successfully retrieved information for corpus '{info.display_name}'",
        "corpus_name": resolved,
        "corpus_display_name": info.display_name,
        "file_count": len(docs),
        "files": [
            {
                "file_id": d.doc_id,
                "display_name": d.display_name,
                "source_uri": d.source_uri,
                "create_time": d.create_time,
                "update_time": d.update_time,
            }
            for d in docs
        ],
    }