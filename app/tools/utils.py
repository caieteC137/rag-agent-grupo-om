# app/tools/utils.py
#
# DEPRECATION NOTICE:
# get_corpus_resource_name() and check_corpus_exists() are now handled
# by provider.resolve_corpus_name() and provider.corpus_exists().
#
# This file is kept for backward compatibility only.
# Remove after all callers are migrated to use the provider directly.

import logging

from ..retrieval import get_provider

logger = logging.getLogger(__name__)


def get_corpus_resource_name(corpus_name: str) -> str:
    """DEPRECATED: Use provider.resolve_corpus_name() instead."""
    provider = get_provider()
    resolved = provider.resolve_corpus_name(corpus_name)
    return resolved or corpus_name  # fallback to original string


def check_corpus_exists(corpus_name: str, tool_context=None) -> bool:
    """DEPRECATED: Use provider.corpus_exists() instead."""
    provider = get_provider()
    resolved = provider.resolve_corpus_name(corpus_name)
    if resolved is None:
        return False
    # Update state for backward compatibility
    if tool_context is not None:
        tool_context.state[f"corpus_exists_{corpus_name}"] = True
        if not tool_context.state.get("current_corpus"):
            tool_context.state["current_corpus"] = resolved
    return True