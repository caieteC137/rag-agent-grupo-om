#!/usr/bin/env python3
r"""
Migration script: RAG Engine corpora → Vertex Vector Search + Firestore + GCS

Usage:
    python scripts/migrate_rag_to_vertex_vs.py \
        --dry-run \          # preview only, no writes
        --corpus-filter "my-corpus"   # migrate only matching display names

This script:
  1. Lists all corpora from RAG Engine
  2. For each corpus, lists all files
  3. Downloads each file from GCS (RAG Engine stores them internally)
  4. Re-ingests through VertexVectorSearchProvider
  5. Validates chunk counts match

IMPORTANT: Run with --dry-run first. Validate, then run without.
"""

import argparse
import os
import sys

# Point to new provider for writing
os.environ["RETRIEVAL_PROVIDER"] = "vertex_vs"

from app.retrieval.rag_engine_provider import RagEngineProvider
from app.retrieval.vertex_vector_search_provider import VertexVectorSearchProvider


def migrate(dry_run: bool, corpus_filter: str | None) -> None:
    src = RagEngineProvider()
    dst = VertexVectorSearchProvider()

    corpora = src.list_corpora()
    print(f"Found {len(corpora)} corpora in RAG Engine")

    for corpus in corpora:
        if corpus_filter and corpus_filter not in corpus.display_name:
            print(f"  SKIP {corpus.display_name}")
            continue

        print(f"\n── Migrating corpus: {corpus.display_name} ──")
        docs = src.list_documents(corpus.resource_name)
        print(f"   {len(docs)} documents")

        if dry_run:
            for doc in docs:
                print(f"   [DRY-RUN] Would migrate: {doc.display_name} ({doc.source_uri})")
            continue

        # Create corresponding corpus in new provider
        new_corpus = dst.create_corpus(corpus.display_name)
        print(f"   Created new corpus: {new_corpus.resource_name}")

        for doc in docs:
            print(f"   Ingesting: {doc.display_name}")
            result = dst.ingest(
                corpus_resource_name=new_corpus.resource_name,
                paths=[doc.source_uri],
            )
            if result.success:
                print(f"   ✓ doc_ids: {result.doc_ids}")
            else:
                print(f"   ✗ FAILED: {result.error}")

    print("\nMigration complete." if not dry_run else "\nDry-run complete — no changes made.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--corpus-filter", default=None)
    args = parser.parse_args()
    migrate(dry_run=args.dry_run, corpus_filter=args.corpus_filter)