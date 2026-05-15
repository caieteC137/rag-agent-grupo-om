# app/retrieval/vertex_vector_search_provider.py
#
# ARCHITECTURAL DECISION: This provider owns the full retrieval lifecycle:
#   GCS (raw files) → text extraction → chunking → Gemini embeddings
#   → Vertex AI Vector Search (vectors) + Firestore (metadata)
#
# It does NOT depend on vertexai.rag at all. The only Vertex AI SDK
# usage is for embeddings and Vector Search, which are general-purpose
# services, not RAG-Engine-specific.

from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from google.cloud import firestore, storage
from google.cloud.aiplatform import MatchingEngineIndex, MatchingEngineIndexEndpoint
from google.cloud.aiplatform_v1 import (
    IndexServiceClient,
    UpsertDatapointsRequest,
    IndexDatapoint,
    RemoveDatapointsRequest,
)
from vertexai.language_models import TextEmbeddingModel

from .provider import (
    CorpusInfo,
    DocumentInfo,
    IngestResult,
    RetrievalResult,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Environment configuration
# ─────────────────────────────────────────────────────────────────────────────
_PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
_GCS_BUCKET = os.environ["RETRIEVAL_GCS_BUCKET"]          # raw document storage
_FIRESTORE_DB = os.getenv("FIRESTORE_DATABASE", "(default)")
_VECTOR_INDEX_ID = os.environ["VERTEX_VECTOR_INDEX_ID"]    # numeric index ID
_VECTOR_ENDPOINT_ID = os.environ["VERTEX_VECTOR_ENDPOINT_ID"]
_EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL", "text-embedding-005"
)
_CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "512"))
_CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))
_EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "768"))


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """
    Simple sliding-window chunker.
    FUTURE: Replace with a semantic chunker (e.g. split on sentence boundaries).
    """
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + size, len(words))
        chunks.append(" ".join(words[start:end]))
        start += size - overlap
    return [c for c in chunks if c.strip()]


def _extract_text(blob: storage.Blob) -> str:
    """
    Extract plain text from a GCS blob.
    Supports: .txt, .md  (extend with pdfminer / docx2txt as needed)
    ARCHITECTURAL NOTE: Keep extraction logic here, not in the tool layer.
    """
    content = blob.download_as_bytes()
    name = blob.name.lower()

    if name.endswith((".txt", ".md")):
        return content.decode("utf-8", errors="replace")

    if name.endswith(".pdf"):
        # Optional: pip install pdfminer.six
        try:
            from pdfminer.high_level import extract_text_to_fp
            from pdfminer.layout import LAParams
            buf = io.StringIO()
            extract_text_to_fp(
                io.BytesIO(content), buf, laparams=LAParams()
            )
            return buf.getvalue()
        except ImportError:
            logger.warning(
                "pdfminer not installed; treating PDF as binary (no text)"
            )
            return ""

    # Fallback: attempt UTF-8 decode
    try:
        return content.decode("utf-8", errors="replace")
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# Provider
# ─────────────────────────────────────────────────────────────────────────────

class VertexVectorSearchProvider:
    """
    Full replacement for RagEngineProvider using:
      - GCS: raw file storage
      - Firestore: document + chunk metadata
      - Vertex AI Vector Search: embedding index
      - Vertex AI text-embedding-005: embedding generation

    Corpus concept mapping:
      RAG Engine "corpus"  →  Firestore collection named by corpus_id
                              + a namespace prefix on Vector Search datapoint IDs

    This means corpora are logical partitions — no separate Vector Search
    index per corpus (cost-efficient). Isolation is enforced via
    datapoint ID prefix: "{corpus_id}::{chunk_id}".
    """

    def __init__(self) -> None:
        self._gcs = storage.Client(project=_PROJECT)
        self._bucket = self._gcs.bucket(_GCS_BUCKET)
        self._fs = firestore.Client(
            project=_PROJECT, database=_FIRESTORE_DB
        )
        self._embed_model = TextEmbeddingModel.from_pretrained(_EMBEDDING_MODEL)
        # Vector Search client (REST/gRPC)
        self._vs_client = IndexServiceClient(
            client_options={
                "api_endpoint": f"{_LOCATION}-aiplatform.googleapis.com"
            }
        )
        self._index_name = (
            f"projects/{_PROJECT}/locations/{_LOCATION}"
            f"/indexes/{_VECTOR_INDEX_ID}"
        )
        self._endpoint = MatchingEngineIndexEndpoint(
            index_endpoint_name=_VECTOR_ENDPOINT_ID,
            location=_LOCATION,
            project=_PROJECT,
        )

    # ── embedding ────────────────────────────────────────────────────────────

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """Batch embed. Vertex AI allows up to 250 texts per call."""
        batch_size = 250
        vectors: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            embeddings = self._embed_model.get_embeddings(batch)
            vectors.extend([e.values for e in embeddings])
        return vectors

    # ── Firestore helpers ────────────────────────────────────────────────────

    def _corpora_col(self) -> firestore.CollectionReference:
        return self._fs.collection("retrieval_corpora")

    def _docs_col(self, corpus_id: str) -> firestore.CollectionReference:
        return self._fs.collection(f"retrieval_corpus_{corpus_id}_docs")

    def _chunks_col(self, corpus_id: str) -> firestore.CollectionReference:
        return self._fs.collection(f"retrieval_corpus_{corpus_id}_chunks")

    @staticmethod
    def _corpus_id_from_resource(resource_name: str) -> str:
        """Extract corpus_id from 'corpora/{corpus_id}' resource name."""
        return resource_name.split("/")[-1]

    @staticmethod
    def _make_resource_name(corpus_id: str) -> str:
        return f"corpora/{corpus_id}"

    # ── Corpus management ────────────────────────────────────────────────────

    def list_corpora(self) -> list[CorpusInfo]:
        docs = self._corpora_col().stream()
        return [
            CorpusInfo(
                resource_name=self._make_resource_name(d.id),
                display_name=d.to_dict().get("display_name", d.id),
                create_time=d.to_dict().get("create_time", ""),
                update_time=d.to_dict().get("update_time", ""),
            )
            for d in docs
        ]

    def create_corpus(self, display_name: str) -> CorpusInfo:
        corpus_id = str(uuid.uuid4())
        resource_name = self._make_resource_name(corpus_id)
        now = _now_iso()
        self._corpora_col().document(corpus_id).set(
            {
                "display_name": display_name,
                "create_time": now,
                "update_time": now,
            }
        )
        return CorpusInfo(
            resource_name=resource_name,
            display_name=display_name,
            create_time=now,
            update_time=now,
        )

    def delete_corpus(
        self, corpus_resource_name: str, confirm: bool
    ) -> bool:
        if not confirm:
            return False
        corpus_id = self._corpus_id_from_resource(corpus_resource_name)
        # Delete all documents first
        for doc_info in self.list_documents(corpus_resource_name):
            self.delete_document(
                corpus_resource_name, doc_info.doc_id, confirm=True
            )
        # Delete corpus metadata
        self._corpora_col().document(corpus_id).delete()
        return True

    def get_corpus_info(
        self, corpus_resource_name: str
    ) -> CorpusInfo | None:
        corpus_id = self._corpus_id_from_resource(corpus_resource_name)
        snap = self._corpora_col().document(corpus_id).get()
        if not snap.exists:
            return None
        data = snap.to_dict() or {}
        docs = self.list_documents(corpus_resource_name)
        return CorpusInfo(
            resource_name=corpus_resource_name,
            display_name=data.get("display_name", corpus_id),
            create_time=data.get("create_time", ""),
            update_time=data.get("update_time", ""),
            metadata={"file_count": len(docs)},
        )

    # ── Document management ──────────────────────────────────────────────────

    def list_documents(
        self, corpus_resource_name: str
    ) -> list[DocumentInfo]:
        corpus_id = self._corpus_id_from_resource(corpus_resource_name)
        return [
            DocumentInfo(
                doc_id=d.id,
                corpus_resource_name=corpus_resource_name,
                **{
                    k: v
                    for k, v in (d.to_dict() or {}).items()
                    if k
                    in {
                        "display_name",
                        "source_uri",
                        "gcs_path",
                        "create_time",
                        "update_time",
                        "chunk_ids",
                        "tags",
                    }
                },
            )
            for d in self._docs_col(corpus_id).stream()
        ]

    def ingest(
        self,
        corpus_resource_name: str,
        paths: list[str],
    ) -> IngestResult:
        """
        Full ingestion pipeline:
          1. Copy file to GCS (if not already there)
          2. Extract text
          3. Chunk
          4. Embed all chunks in batch
          5. Upsert to Vector Search
          6. Write metadata to Firestore
        """
        corpus_id = self._corpus_id_from_resource(corpus_resource_name)
        doc_ids: list[str] = []
        failed: list[str] = []

        for path in paths:
            try:
                doc_id = self._ingest_single(corpus_id, path)
                doc_ids.append(doc_id)
            except Exception as exc:
                logger.exception("Failed to ingest %s: %s", path, exc)
                failed.append(path)

        return IngestResult(
            success=len(failed) == 0,
            corpus_resource_name=corpus_resource_name,
            doc_ids=doc_ids,
            failed_sources=failed,
        )

    def _ingest_single(self, corpus_id: str, path: str) -> str:
        doc_id = str(uuid.uuid4())
        now = _now_iso()

        # ── 1. Store raw file in GCS ─────────────────────────────────────
        gcs_path = self._copy_to_gcs(corpus_id, doc_id, path)

        # ── 2. Extract text ──────────────────────────────────────────────
        blob = self._bucket.blob(gcs_path)
        text = _extract_text(blob)
        if not text.strip():
            raise ValueError(f"No extractable text from {path}")

        # ── 3. Chunk ─────────────────────────────────────────────────────
        chunks = _chunk_text(text, _CHUNK_SIZE, _CHUNK_OVERLAP)

        # ── 4. Embed ─────────────────────────────────────────────────────
        vectors = self._embed(chunks)

        # ── 5. Upsert to Vector Search ───────────────────────────────────
        chunk_ids: list[str] = []
        datapoints: list[IndexDatapoint] = []
        for chunk_text, vector in zip(chunks, vectors):
            # Using a deterministic but unique chunk suffix
            chunk_hash = hashlib.md5(chunk_text.encode()).hexdigest()[:8]
            chunk_id = f"{corpus_id}::{doc_id}::{chunk_hash}::{uuid.uuid4().hex[:6]}"
            chunk_ids.append(chunk_id)
            datapoints.append(
                IndexDatapoint(
                    datapoint_id=chunk_id,
                    feature_vector=vector,
                    restricts=[
                        IndexDatapoint.Restriction(
                            namespace="corpus_id",
                            allow_list=[corpus_id],
                        )
                    ],
                )
            )

        # Batch upsert in groups of 100
        for i in range(0, len(datapoints), 100):
            self._vs_client.upsert_datapoints(
                UpsertDatapointsRequest(
                    index=self._index_name,
                    datapoints=datapoints[i : i + 100],
                )
            )

        # ── 6. Store metadata in Firestore ───────────────────────────────
        drive_id = self._extract_drive_id(path)
        
        # 6a. Individual chunk text
        chunk_col = self._chunks_col(corpus_id)
        batch = self._fs.batch()
        for chunk_id, chunk_text in zip(chunk_ids, chunks):
            batch.set(
                chunk_col.document(chunk_id.replace("::", "__")),
                {
                    "text": chunk_text,
                    "doc_id": doc_id,
                    "corpus_id": corpus_id,
                    "chunk_id": chunk_id,
                    "created_at": now,
                },
            )
        batch.commit()

        # 6b. Document-level metadata
        self._docs_col(corpus_id).document(doc_id).set(
            {
                "doc_id": doc_id,
                "title": path.split("/")[-1],
                "display_name": path.split("/")[-1],
                "source": path,
                "source_uri": path,
                "google_drive_id": drive_id or "",
                "gcs_path": f"gs://{_GCS_BUCKET}/{gcs_path}",
                "chunk_ids": chunk_ids,
                "create_time": now,
                "update_time": now,
                "updated_at": now,
                "tags": [],
                "permissions": {},
            }
        )

        # 6c. Update corpus timestamp
        self._corpora_col().document(corpus_id).update(
            {"update_time": now}
        )

        logger.info(
            "Ingested doc_id=%s corpus=%s chunks=%d drive_id=%s",
            doc_id, corpus_id, len(chunks), drive_id
        )
        return doc_id

    def _extract_drive_id(self, path: str) -> str | None:
        """Extract ID from various Google Drive URL formats."""
        if "drive.google.com" not in path:
            return None
        
        # Match /d/ID/ or id=ID
        patterns = [
            r"/d/([a-zA-Z0-9_-]+)",
            r"id=([a-zA-Z0-9_-]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, path)
            if match:
                return match.group(1)
        return None


    def _copy_to_gcs(
        self, corpus_id: str, doc_id: str, source_path: str
    ) -> str:
        """
        If source is already a gs:// URI, return as-is.
        Otherwise, treat as local path and upload.
        """
        if source_path.startswith("gs://"):
            # Already in GCS — compute relative path within our bucket
            gcs_path = f"corpora/{corpus_id}/{doc_id}/{source_path.split('/')[-1]}"
            src_bucket_name = source_path[5:].split("/")[0]
            src_blob_path = "/".join(source_path[5:].split("/")[1:])
            src_bucket = self._gcs.bucket(src_bucket_name)
            src_blob = src_bucket.blob(src_blob_path)
            src_bucket.copy_blob(
                src_blob, self._bucket, new_name=gcs_path
            )
            return gcs_path

        # Local file path
        filename = os.path.basename(source_path)
        gcs_path = f"corpora/{corpus_id}/{doc_id}/{filename}"
        self._bucket.blob(gcs_path).upload_from_filename(source_path)
        return gcs_path

    def delete_document(
        self,
        corpus_resource_name: str,
        doc_id: str,
        confirm: bool,
    ) -> bool:
        if not confirm:
            return False
        corpus_id = self._corpus_id_from_resource(corpus_resource_name)
        doc_snap = self._docs_col(corpus_id).document(doc_id).get()
        if not doc_snap.exists:
            return False

        doc_data = doc_snap.to_dict() or {}
        chunk_ids: list[str] = doc_data.get("chunk_ids", [])

        # Remove vectors from Vector Search
        if chunk_ids:
            for i in range(0, len(chunk_ids), 100):
                self._vs_client.remove_datapoints(
                    RemoveDatapointsRequest(
                        index=self._index_name,
                        datapoint_ids=chunk_ids[i : i + 100],
                    )
                )

        # Delete chunk metadata from Firestore
        batch = self._fs.batch()
        for chunk_id in chunk_ids:
            safe_id = chunk_id.replace("::", "__")
            batch.delete(self._chunks_col(corpus_id).document(safe_id))
        batch.commit()

        # Delete GCS file
        gcs_path = doc_data.get("gcs_path", "")
        if gcs_path:
            try:
                self._bucket.blob(gcs_path).delete()
            except Exception as exc:
                logger.warning("Could not delete GCS blob %s: %s", gcs_path, exc)

        # Delete document metadata
        self._docs_col(corpus_id).document(doc_id).delete()
        return True

    def update_document(
        self,
        corpus_resource_name: str,
        doc_id: str,
        paths: list[str],
    ) -> IngestResult:
        self.delete_document(corpus_resource_name, doc_id, confirm=True)
        return self.ingest(corpus_resource_name, paths)

    # ── Retrieval ────────────────────────────────────────────────────────────

    def search(
        self,
        corpus_resource_name: str,
        query: str,
        top_k: int = 10,
        distance_threshold: float = 0.5,
    ) -> list[RetrievalResult]:
        """
        Retrieval pipeline:
          1. Embed query
          2. ANN search on Vector Search with corpus_id filter
          3. Fetch chunk text from Firestore
          4. Return ranked RetrievalResult list
        """
        corpus_id = self._corpus_id_from_resource(corpus_resource_name)

        # ── 1. Embed query ───────────────────────────────────────────────
        [query_vector] = self._embed([query])

        # ── 2. ANN search ────────────────────────────────────────────────
        response = self._endpoint.find_neighbors(
            deployed_index_id=_VECTOR_ENDPOINT_ID,  
            queries=[query_vector],
            num_neighbors=top_k,
            filter=[
                # Namespace filter: only return chunks from this corpus
                MatchingEngineIndexEndpoint.Restriction(
                    namespace="corpus_id",
                    allow_list=[corpus_id],
                )
            ],
        )

        if not response or not response[0]:
            return []

        neighbors = response[0]  # first query's neighbors

        # ── 3. Fetch chunk texts from Firestore ──────────────────────────
        results: list[RetrievalResult] = []
        for neighbor in neighbors:
            # Filter by distance threshold
            # Vector Search returns distance (lower = more similar for L2)
            # Convert to similarity: 1 - distance
            similarity = 1.0 - neighbor.distance
            if similarity < (1.0 - distance_threshold):
                continue

            chunk_id = neighbor.id  # e.g. "corpus123::doc456::chunk789"
            safe_id = chunk_id.replace("::", "__")
            chunk_snap = (
                self._chunks_col(corpus_id).document(safe_id).get()
            )

            if not chunk_snap.exists:
                logger.warning("Chunk %s not found in Firestore", chunk_id)
                continue

            chunk_data = chunk_snap.to_dict() or {}
            doc_id = chunk_data.get("doc_id", "")

            # Optionally fetch doc metadata for source_uri
            source_uri = ""
            source_name = ""
            if doc_id:
                doc_snap = (
                    self._docs_col(corpus_id).document(doc_id).get()
                )
                if doc_snap.exists:
                    dd = doc_snap.to_dict() or {}
                    source_uri = dd.get("source_uri", "")
                    source_name = dd.get("display_name", "")

            results.append(
                RetrievalResult(
                    text=chunk_data.get("text", ""),
                    source_uri=source_uri,
                    source_name=source_name,
                    score=similarity,
                    doc_id=doc_id,
                    chunk_id=chunk_id,
                )
            )

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)
        return results

    # ── Utility ──────────────────────────────────────────────────────────────

    def resolve_corpus_name(self, name_or_display: str) -> str | None:
        # Already a resource name?
        if name_or_display.startswith("corpora/"):
            if self.corpus_exists(name_or_display):
                return name_or_display
            return None
        # Try display name lookup
        for info in self.list_corpora():
            if info.display_name == name_or_display:
                return info.resource_name
        return None

    def corpus_exists(self, corpus_resource_name: str) -> bool:
        corpus_id = self._corpus_id_from_resource(corpus_resource_name)
        snap = self._corpora_col().document(corpus_id).get()
        return snap.exists