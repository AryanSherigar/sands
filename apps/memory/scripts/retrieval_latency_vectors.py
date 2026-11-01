"""Deterministic 768-dim hash vectors shared by the document and query fakes."""

import hashlib

EMBEDDING_DIM = 768
DIGEST_BYTES = 32
BLOCK_COUNT = EMBEDDING_DIM // DIGEST_BYTES
BYTE_CENTER = 127.5


def vector_for(text: str) -> list[float]:
    values: list[float] = []
    for block in range(BLOCK_COUNT):
        digest = hashlib.sha256(f"{block}:{text}".encode()).digest()
        values.extend((byte - BYTE_CENTER) / BYTE_CENTER for byte in digest)
    return values


class HashDocumentEmbedder:
    async def embed_documents(
        self, texts: list[str], deadline_monotonic: float | None = None
    ) -> list[list[float]]:
        return [vector_for(text) for text in texts]


async def embed_query(text: str) -> list[float]:
    return vector_for(text)
