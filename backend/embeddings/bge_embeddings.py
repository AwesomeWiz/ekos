class BGEEmbeddingService:
    def __init__(self, model_name: str = "BAAI/bge-base-en-v1.5", cache_folder: str | None = None):
        # Loading is deferred until indexing or a non-empty search needs the model.
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self.model = SentenceTransformer(model_name, cache_folder=cache_folder)

    def embed(self, text: str) -> list[float]:
        embedding = self.model.encode(
            text,
            normalize_embeddings=True,
        )

        return embedding.tolist()

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
        )

        return embeddings.tolist()
