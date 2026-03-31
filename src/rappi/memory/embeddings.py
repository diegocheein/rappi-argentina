"""Optional embedding providers for semantic search.

Embeddings are disabled by default. Enable via:
    rappi prefs set embeddings.enabled true
    rappi prefs set embeddings.provider openai

Requires: pip install rappi-cli[embeddings]  (adds openai dependency)
"""

from __future__ import annotations

import struct
from abc import ABC, abstractmethod
from math import sqrt

import aiosqlite


class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @property
    @abstractmethod
    def dimensions(self) -> int: ...


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Uses OpenAI text-embedding-3-small (1536 dims).

    Requires OPENAI_API_KEY environment variable.
    Cost: ~$0.02 per 1M tokens.
    """

    def __init__(self, model: str = "text-embedding-3-small"):
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return 1536

    async def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise RuntimeError(
                "OpenAI embeddings require the openai package. "
                "Install with: uv add openai"
            )

        client = AsyncOpenAI()
        response = await client.embeddings.create(input=texts, model=self._model)
        return [item.embedding for item in response.data]


# --- Vector utilities (pure Python, no numpy) ---


def vector_to_bytes(vec: list[float]) -> bytes:
    """Pack a float list into bytes for SQLite BLOB storage."""
    return struct.pack(f"{len(vec)}f", *vec)


def bytes_to_vector(data: bytes) -> list[float]:
    """Unpack bytes back into a float list."""
    n = len(data) // 4
    return list(struct.unpack(f"{n}f", data))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sqrt(sum(x * x for x in a))
    norm_b = sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# --- Embedding storage and search ---


class EmbeddingStore:
    """Manages embedding storage and semantic search in SQLite."""

    def __init__(self, db: aiosqlite.Connection, provider: EmbeddingProvider):
        self._db = db
        self._provider = provider

    async def store_embeddings(
        self, entity_type: str, items: list[tuple[str, str]]
    ) -> None:
        """Generate and store embeddings for a batch of (entity_id, text) pairs."""
        if not items:
            return

        ids, texts = zip(*items)
        vectors = await self._provider.embed(list(texts))

        for entity_id, text, vec in zip(ids, texts, vectors):
            await self._db.execute(
                """INSERT OR REPLACE INTO embeddings
                   (entity_type, entity_id, text_content, vector, model)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    entity_type,
                    entity_id,
                    text,
                    vector_to_bytes(vec),
                    self._provider.model_name,
                ),
            )
        await self._db.commit()

    async def search(
        self, query: str, entity_type: str | None = None, limit: int = 10
    ) -> list[dict]:
        """Semantic search across stored embeddings."""
        # Embed the query
        query_vectors = await self._provider.embed([query])
        query_vec = query_vectors[0]

        # Load candidate vectors
        if entity_type:
            cursor = await self._db.execute(
                "SELECT entity_type, entity_id, text_content, vector FROM embeddings WHERE entity_type = ?",
                (entity_type,),
            )
        else:
            cursor = await self._db.execute(
                "SELECT entity_type, entity_id, text_content, vector FROM embeddings"
            )

        rows = await cursor.fetchall()

        # Score and rank
        results = []
        for row in rows:
            vec = bytes_to_vector(row["vector"])
            score = cosine_similarity(query_vec, vec)
            results.append({
                "entity_type": row["entity_type"],
                "entity_id": row["entity_id"],
                "text": row["text_content"],
                "score": score,
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
