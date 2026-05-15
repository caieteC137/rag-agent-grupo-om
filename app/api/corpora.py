# app/api/corpora.py
# Add this to your ADK server or FastAPI app.
# The frontend calls GET /api/corpora → this handler → provider.list_corpora()

from fastapi import APIRouter
from ..retrieval import get_provider

router = APIRouter()

@router.get("/corpora")
async def list_corpora():
    """
    Provider-agnostic corpus listing.
    Replaces direct ragCorpora REST API calls in the frontend.
    """
    provider = get_provider()
    corpora = provider.list_corpora()
    # Return in same shape the frontend already expects
    return {
        "ragCorpora": [
            {
                "name": c.resource_name,
                "displayName": c.display_name,
            }
            for c in corpora
        ]
    }