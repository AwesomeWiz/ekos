"""Download/warm the configured BGE model without inserting any test documents."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.knowledge_runtime import get_embedding_service  # noqa: E402


if __name__ == "__main__":
    service = get_embedding_service()
    print({"embedding_model": service.model_name, "dimensions": len(service.embed("repository branches"))})
