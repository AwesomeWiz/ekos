import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import os
import sys

# Ensure backend directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.base import Base, get_db
from models.role import Role
from models.organization import Organization
from models.user import User
from auth.security import hash_password
from main import app, init_db
from services.demo_seed import seed_demo
from config.settings import settings
from services import knowledge_runtime
from unittest.mock import Mock


@pytest.fixture(autouse=True)
def isolated_knowledge_runtime(tmp_path, monkeypatch):
    """Use real temporary Chroma storage, but never download a model in unit tests."""
    monkeypatch.setattr(settings, "CHROMA_PATH", str(tmp_path / "chroma"))
    embeddings = Mock()
    embeddings.embed.side_effect = lambda text: [1.0, float(len(text) % 7), 0.5]
    embeddings.embed_many.side_effect = lambda texts: [embeddings.embed(text) for text in texts]
    monkeypatch.setattr(knowledge_runtime, "_embeddings", lambda *_args: embeddings)
    return embeddings

# Create in-memory SQLite database engine for fast, isolated testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    # Initialize DB schema & seed data
    init_db(target_engine=engine)
    session = TestingSessionLocal()
    seed_demo(session, include_connector=False)
    
    yield session
    
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()
