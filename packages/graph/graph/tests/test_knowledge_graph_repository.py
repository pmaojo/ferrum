import sqlite3
from typing import Callable

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from adapters.repositories.sqlalchemy_knowledge_graph_repository import (
    SQLAlchemyKnowledgeGraphRepository,
    Base,
)
from adapters.repositories.knowledge_graph_repository_adapter import (
    RawSQLKnowledgeGraphRepository,
)
from domain.entities import KnowledgeGraph, ScientificDomain


def _sqlalchemy_repo() -> SQLAlchemyKnowledgeGraphRepository:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return SQLAlchemyKnowledgeGraphRepository(Session())


def _raw_repo() -> RawSQLKnowledgeGraphRepository:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE knowledge_graphs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            domain TEXT NOT NULL,
            ontology_version_id TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL,
            node_count INTEGER NOT NULL,
            edge_count INTEGER NOT NULL,
            is_public BOOLEAN NOT NULL
        )
        """
    )
    conn.commit()
    return RawSQLKnowledgeGraphRepository(conn)


@pytest.mark.parametrize("factory", [_sqlalchemy_repo, _raw_repo])
def test_repository_crud(factory: Callable[[], object]):
    repo = factory()
    kg = KnowledgeGraph.create(
        name="Test",
        tenant_id="t1",
        domain=ScientificDomain.BIOLOGY,
        ontology_version_id="onto1",
    )
    kg.update_counts(1, 2)

    created = repo.create(kg)
    assert created.id == kg.id

    fetched = repo.get_by_id(kg.id, kg.tenant_id)
    assert fetched is not None
    assert fetched.name == "Test"

    kg.name = "Updated"
    repo.update(kg)
    assert repo.get_by_id(kg.id, kg.tenant_id).name == "Updated"

    kgs, total = repo.list_by_tenant(kg.tenant_id)
    assert total == 1
    assert kgs[0].id == kg.id

    assert repo.delete_by_id(kg.id, kg.tenant_id)
    assert repo.get_by_id(kg.id, kg.tenant_id) is None
