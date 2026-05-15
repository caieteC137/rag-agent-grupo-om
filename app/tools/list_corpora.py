# app/tools/list_corpora.py  (refactored)
from ..retrieval import get_provider


def list_corpora() -> dict:
    """List all available document corpora."""
    provider = get_provider()
    try:
        corpora = provider.list_corpora()
        return {
            "status": "success",
            "message": f"Found {len(corpora)} available corpora",
            "corpora": [
                {
                    "resource_name": c.resource_name,
                    "display_name": c.display_name,
                    "create_time": c.create_time,
                    "update_time": c.update_time,
                }
                for c in corpora
            ],
        }
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Error listing corpora: {exc}",
            "corpora": [],
        }