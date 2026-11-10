"""Two tenants never see each other's content (DECISIONS ADR-015).

Real SQLite + ChromaDB. Both tenants upload the *same* file, so a missing
filter anywhere would show up as the other tenant's chunk IDs.
"""

import pytest
from fastapi.testclient import TestClient

from cadis.api.deps import Principal, get_principal
from cadis.ingest.pipeline import HANDLERS
from cadis.jobs.worker import Worker
from cadis.main import create_app
from cadis.retrieval import search
from cadis.storage import repositories
from cadis.storage.db import session_scope
from conftest import EVAL_DOCS

ALICE = Principal("tenant-a", "alice")
BOB = Principal("tenant-b", "bob")


@pytest.fixture
def world(v2_chroma):
    app = create_app()
    who = {"p": ALICE}
    app.dependency_overrides[get_principal] = lambda: who["p"]
    with TestClient(app) as client:
        def as_(p):
            who["p"] = p
            return client

        data = {}
        for p in (ALICE, BOB):
            c = as_(p)
            col = c.post("/collections", json={"name": f"{p.tenant_id} docs"}).json()
            files = [("files", (n, (EVAL_DOCS / n).read_bytes())) for n in ("supply.txt", "legal.txt")]
            if p is BOB:
                files.append(("files", ("energy.txt", (EVAL_DOCS / "energy.txt").read_bytes())))
            items = c.post(f"/collections/{col['id']}/documents", files=files).json()
            data[p] = {"col": col["id"], "docs": [i["document_id"] for i in items],
                       "jobs": [i["job_id"] for i in items]}
        Worker(HANDLERS, "w").drain()
        yield as_, data


def chunk_ids_of(collection_id):
    with session_scope() as s:
        from sqlalchemy import select

        from cadis.storage.tables import Chunk
        return set(s.scalars(select(Chunk.id).where(Chunk.collection_id == collection_id)))


def allowed(p):
    with session_scope() as s:
        return repositories.allowed_collection_ids(s, p.tenant_id, p.user_id)


def test_allowed_collections_are_per_tenant(world):
    _, data = world
    assert allowed(ALICE) == [data[ALICE]["col"]]
    assert allowed(BOB) == [data[BOB]["col"]]


@pytest.mark.parametrize("question", [
    "What is the price per unit?", "Harlow Ridge battery storage", "termination notice Meridian",
])
def test_search_never_returns_another_tenants_chunks(world, question):
    _, data = world
    alices = chunk_ids_of(data[ALICE]["col"])
    for fn in (search.dense_search, search.keyword_search):
        hits = fn(question, allowed(ALICE), k=50)
        assert all(h.chunk_id in alices for h in hits), fn.__name__
    # Bob's energy report exists only in Bob's collection.
    assert search.keyword_search("Harlow Ridge battery", allowed(ALICE)) == []
    assert search.keyword_search("Harlow Ridge battery", allowed(BOB))


def test_empty_allowed_list_means_nothing(world):
    assert search.dense_search("price", []) == []
    assert search.keyword_search("price", []) == []
    with session_scope() as s:
        with pytest.raises(ValueError):
            repositories.current_chunks(s, ["x"], None)


def test_api_hides_other_tenants_resources(world):
    as_, data = world
    a, b = data[ALICE], data[BOB]
    bob = as_(BOB)
    assert [c["id"] for c in bob.get("/collections").json()] == [b["col"]]
    assert bob.get(f"/collections/{a['col']}").status_code == 404
    assert bob.get(f"/collections/{a['col']}/documents").status_code == 404
    assert bob.post(f"/collections/{a['col']}/documents",
                    files=[("files", ("x.txt", b"sneaky"))]).status_code == 404
    for doc_id in a["docs"]:
        assert bob.get(f"/documents/{doc_id}").status_code == 404
        assert bob.get(f"/documents/{doc_id}/sections").status_code == 404
        assert bob.post(f"/documents/{doc_id}/reingest").status_code == 404
        assert bob.delete(f"/documents/{doc_id}").status_code == 404
    for job_id in a["jobs"]:
        assert bob.get(f"/jobs/{job_id}").status_code == 404
        assert bob.get(f"/jobs/{job_id}/events").status_code == 404
    # Alice still has everything.
    alice = as_(ALICE)
    assert all(alice.get(f"/documents/{d}").json()["status"] == "READY" for d in a["docs"])
