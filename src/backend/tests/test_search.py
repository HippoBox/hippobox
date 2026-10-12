import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from hippobox.rag.qdrant import Qdrant
from hippobox.services.knowledge import Knowledges, KnowledgeService


def test_ownership_filters_before_limit_with_legacy_payloads(monkeypatch):
    vector = Qdrant.__new__(Qdrant)
    vector.prefix = "hp"
    vector.client = QdrantClient(":memory:")
    vector.client.create_collection("hp_knowledge", vectors_config=VectorParams(size=2, distance=Distance.COSINE))
    vector.client.upsert(
        "hp_knowledge",
        points=[
            PointStruct(id=1, vector=[1.0, 0.0], payload={"metadata": {}}),
            PointStruct(id=2, vector=[0.8, 0.2], payload={"metadata": {}}),
        ],
    )
    # The other user's closer result must not consume this user's limit.
    results = vector.search("knowledge", [1.0, 0.0], limit=1, allowed_ids=[2])
    assert results["ids"] == [2]
    vector.client.close()

    candidates = [SimpleNamespace(id=2, topic="work", tags=["api"]), SimpleNamespace(id=3, topic="home", tags=[])]
    monkeypatch.setattr(Knowledges, "get_list", AsyncMock(return_value=candidates))

    class Search:
        def search(self, name, vector, limit, allowed_ids):
            assert allowed_ids == [2]
            return {"ids": []}

    service = KnowledgeService(SimpleNamespace(embed=lambda text: [1.0, 0.0]), Search(), True)
    assert asyncio.run(service.search(42, "query", topic="work", tag="api")) == []
