import logging
from pathlib import Path

from qdrant_client import QdrantClient as QClient
from qdrant_client.http.models import PointStruct
from qdrant_client.models import models

from hippobox.core.settings import SETTINGS

log = logging.getLogger("qdrant")

NO_LIMIT = 999999999


class Qdrant:
    def __init__(self):
        self.prefix = "hp"
        self.mode = SETTINGS.QDRANT_MODE.lower()

        if self.mode == "local":
            storage_path: Path = SETTINGS.QDRANT_LOCAL_PATH
            storage_path.mkdir(parents=True, exist_ok=True)
            log.info(f"Using LOCAL storage: {storage_path}")

            self.client = QClient(path=str(storage_path))

        elif self.mode == "docker":
            url = SETTINGS.QDRANT_URL
            log.info(f"Using REMOTE/DOCKER: {url}")
            self.client = QClient(url=url)

        else:
            raise ValueError(f"Invalid QDRANT_MODE: {self.mode}")

    def _full_name(self, name: str):
        return f"{self.prefix}_{name}"

    def _create_points(self, items: list[dict]):
        return [
            PointStruct(
                id=item["id"],
                vector=item["vector"],
                payload={"text": item["text"], "metadata": item["metadata"]},
            )
            for item in items
        ]

    def create_collection(self, name: str, dim: int):
        cname = self._full_name(name)

        self.client.create_collection(
            collection_name=cname,
            vectors_config=models.VectorParams(
                size=dim,
                distance=models.Distance.COSINE,
                on_disk=True,
            ),
            hnsw_config=models.HnswConfigDiff(m=16),
        )

        self.client.create_payload_index(
            collection_name=cname,
            field_name="metadata.id",
            field_schema=models.KeywordIndexParams(
                type=models.KeywordIndexType.KEYWORD,
                on_disk=True,
            ),
        )

        log.info(f"Collection created: {cname}")

    def has_collection(self, name: str) -> bool:
        cname = self._full_name(name)
        return self.client.collection_exists(cname)

    def delete_collection(self, name: str):
        cname = self._full_name(name)
        return self.client.delete_collection(collection_name=cname)

    def insert(self, name: str, items: list[dict]):
        dim = len(items[0]["vector"])
        if not self.has_collection(name):
            self.create_collection(name, dim)

        points = self._create_points(items)
        cname = self._full_name(name)

        self.client.upload_points(cname, points)

    def upsert(self, name: str, items: list[dict]):
        dim = len(items[0]["vector"])
        if not self.has_collection(name):
            self.create_collection(name, dim)

        points = self._create_points(items)
        cname = self._full_name(name)

        return self.client.upsert(cname, points)

    def delete(self, name: str, ids: list[str]):
        cname = self._full_name(name)
        return self.client.delete(
            collection_name=cname,
            points_selector=models.PointIdsList(points=ids),
        )

    def search(self, name: str, vector: list[float], limit: int = 5):
        cname = self._full_name(name)
        result = self.client.query_points(
            collection_name=cname,
            query=vector,
            limit=limit,
        )

        points = result.points
        return {
            "ids": [p.id for p in points],
            "documents": [p.payload.get("text") for p in points],
            "metadatas": [p.payload.get("metadata") for p in points],
            "scores": [p.score for p in points],
        }

    def query(self, name: str, filter_dict: dict):
        cname = self._full_name(name)

        conditions = [
            models.FieldCondition(
                key=f"metadata.{k}",
                match=models.MatchValue(value=v),
            )
            for k, v in filter_dict.items()
        ]

        scroll_res = self.client.scroll(
            collection_name=cname,
            scroll_filter=models.Filter(should=conditions),
            limit=NO_LIMIT,
        )

        points = scroll_res[0]
        return {
            "ids": [p.id for p in points],
            "documents": [p.payload.get("text") for p in points],
            "metadatas": [p.payload.get("metadata") for p in points],
        }

    def reset(self):
        col_list = self.client.get_collections().collections
        for col in col_list:
            if col.name.startswith(self.prefix):
                self.client.delete_collection(col.name)
                log.info(f"Deleted: {col.name}")
