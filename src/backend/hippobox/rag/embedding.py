from openai import OpenAI

from hippobox.core.settings import SETTINGS


class Embedding:
    def __init__(self):
        self.client = OpenAI(api_key=SETTINGS.OPENAI_API_KEY)
        self.model = SETTINGS.EMBEDDING_MODEL

    def embed(self, text: str) -> list[float]:
        if not text or not isinstance(text, str):
            raise ValueError("Text input must be a non-empty string.")

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
            )
            return response.data[0].embedding

        except Exception:
            raise

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts or not isinstance(texts, list):
            raise ValueError("Input must be a non-empty list of strings.")

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts,
            )
            return [item.embedding for item in response.data]

        except Exception:
            raise
