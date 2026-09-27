"""Load teammate services on demand; ordinary auth startup needs no model download."""

from functools import lru_cache
from pathlib import Path
from threading import Lock

from config.settings import settings

_model_lock = Lock()


@lru_cache(maxsize=1)
def _chroma(path: str):
    from vector_db.chroma_service import ChromaService

    return ChromaService(path=path)


@lru_cache(maxsize=1)
def _embeddings(model: str, cache: str):
    from embeddings.bge_embeddings import BGEEmbeddingService

    return BGEEmbeddingService(model_name=model, cache_folder=cache)


def get_chroma_service():
    return _chroma(settings.CHROMA_PATH)


def get_embedding_service():
    # Do not put model weights in backend/models when a legacy Chroma path is used.
    cache = str(Path(__file__).resolve().parents[1] / "data" / "models")
    with _model_lock:
        return _embeddings(settings.EMBEDDING_MODEL, cache)
