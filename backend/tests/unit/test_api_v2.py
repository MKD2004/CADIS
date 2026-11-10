"""V2 HTTP API: collections, uploads, documents, sections, jobs (Phase 1)."""

import io

import pytest
from fastapi.testclient import TestClient

from cadis.ingest.pipeline import HANDLERS
from cadis.jobs.worker import Worker
from cadis.main import create_app
from conftest import EVAL_DOCS
from fakes import make_pdf


@pytest.fixture
def client(v2):
    with TestClient(create_app()) as c:
        yield c


def drain():
    return Worker(HANDLERS, "test-worker").drain()


def upload(client, col_id, *names):
    files = [("files", (n, (EVAL_DOCS / n).read_bytes(), "text/plain")) for n in names]
    return client.post(f"/collections/{col_id}/documents", files=files)


@pytest.fixture
def col(client):
    return client.post("/collections", json={"name": "Contracts"}).json()


def test_create_and_list_collections(client):
    r = client.post("/collections", json={"name": "Contracts"})
    assert r.status_code == 201 and r.json()["document_count"] == 0
    assert [c["name"] for c in client.get("/collections").json()] == ["Contracts"]
    assert client.post("/collections", json={"name": ""}).status_code == 422


def test_upload_returns_202_and_jobs_finish(client, col):
    r = upload(client, col["id"], "energy.txt", "supply.txt")
    assert r.status_code == 202
    items = r.json()
    assert [i["filename"] for i in items] == ["energy.txt", "supply.txt"]
    assert all(i["job_id"] and not i["duplicate"] for i in items)
    assert client.get(f"/jobs/{items[0]['job_id']}").json()["status"] == "PENDING"

    assert drain() == 2
    job = client.get(f"/jobs/{items[0]['job_id']}").json()
    assert job["status"] == "COMPLETED" and job["progress"] == 1.0 and job["stage"] == "done"
    doc = client.get(f"/documents/{items[0]['document_id']}").json()
    assert doc["status"] == "READY" and doc["current_version"] == 1
    assert doc["title"].startswith("Northern Grid Authority")
    assert doc["latest_job"]["id"] == items[0]["job_id"]
    assert client.get(f"/collections/{col['id']}").json()["document_count"] == 2


def test_sections_endpoint_returns_the_tree(client, col):
    doc_id = upload(client, col["id"], "energy.txt").json()[0]["document_id"]
    assert client.get(f"/documents/{doc_id}/sections").json() == []   # not ingested yet
    drain()
    sections = client.get(f"/documents/{doc_id}/sections").json()
    assert sections[0]["level"] == 0 and sections[0]["path"] == ""
    assert [s["path"] for s in sections[1:4]] == ["Foreword", "Targets", "Generation"]
    assert all(s["chunk_count"] >= 1 for s in sections[1:])
    assert all(s["parent_id"] == sections[0]["id"] for s in sections[1:])


def test_duplicate_upload_is_detected(client, col):
    first = upload(client, col["id"], "energy.txt").json()[0]
    again = upload(client, col["id"], "energy.txt").json()[0]
    assert again["duplicate"] and again["document_id"] == first["document_id"]
    assert again["job_id"] == first["job_id"]
    assert len(client.get(f"/collections/{col['id']}/documents").json()) == 1
    # The same file in another collection is a separate document.
    other = client.post("/collections", json={"name": "Other"}).json()
    assert not upload(client, other["id"], "energy.txt").json()[0]["duplicate"]


@pytest.mark.parametrize("name, content, status", [
    ("virus.exe", b"MZ", 415),
    ("fake.pdf", b"not a pdf", 415),
    ("empty.txt", b"", 422),
])
def test_bad_uploads_are_rejected(client, col, name, content, status):
    r = client.post(f"/collections/{col['id']}/documents", files=[("files", (name, content))])
    assert r.status_code == status
    assert client.get(f"/collections/{col['id']}/documents").json() == []


def test_too_large_upload_is_rejected(client, col, monkeypatch):
    from cadis.config import get_settings
    monkeypatch.setattr(get_settings(), "max_upload_mb", 0)
    r = client.post(f"/collections/{col['id']}/documents", files=[("files", ("a.txt", b"x"))])
    assert r.status_code == 413


def test_one_bad_file_rejects_the_whole_batch(client, col):
    files = [("files", ("ok.txt", b"Some text.")), ("files", ("bad.exe", b"MZ"))]
    assert client.post(f"/collections/{col['id']}/documents", files=files).status_code == 415
    assert client.get(f"/collections/{col['id']}/documents").json() == []


def test_pdf_upload_is_ingested(client, col):
    r = client.post(f"/collections/{col['id']}/documents",
                    files=[("files", ("r.pdf", make_pdf("Revenue grew in 2025."), "application/pdf"))])
    drain()
    doc = client.get(f"/documents/{r.json()[0]['document_id']}").json()
    assert doc["status"] == "READY" and doc["pages"] == 1


def test_file_without_text_fails_permanently(client, col):
    r = client.post(f"/collections/{col['id']}/documents",
                    files=[("files", ("blank.txt", b"   \n\n  "))])
    drain()
    item = r.json()[0]
    job = client.get(f"/jobs/{item['job_id']}").json()
    assert job["status"] == "FAILED" and job["attempts"] == 1 and "no text" in job["error"]
    doc = client.get(f"/documents/{item['document_id']}").json()
    assert doc["status"] == "FAILED" and "no text" in doc["error"]
    # Manual retry puts it back in the queue.
    assert client.post(f"/jobs/{item['job_id']}/retry").json()["status"] == "PENDING"
    assert client.post(f"/jobs/{item['job_id']}/retry").status_code == 409


def test_reingest_creates_a_new_version(client, col, v2):
    doc_id = upload(client, col["id"], "trial2.txt").json()[0]["document_id"]
    drain()
    v1_ids = set(v2.ids_for_document(doc_id))
    r = client.post(f"/documents/{doc_id}/reingest")
    assert r.status_code == 202
    assert client.post(f"/documents/{doc_id}/reingest").json()["job_id"] == r.json()["job_id"]
    drain()
    assert client.get(f"/documents/{doc_id}").json()["current_version"] == 2
    v2_ids = v2.ids_for_document(doc_id)
    assert len(v2_ids) == len(v1_ids) and not v1_ids & v2_ids     # old vectors removed


def test_delete_document(client, col, v2):
    doc_id = upload(client, col["id"], "supply.txt").json()[0]["document_id"]
    drain()
    assert v2.ids_for_document(doc_id)
    assert client.delete(f"/documents/{doc_id}").status_code == 204
    assert client.get(f"/documents/{doc_id}").status_code == 404
    assert not v2.ids_for_document(doc_id)
    assert client.delete(f"/documents/{doc_id}").status_code == 404


def test_unknown_ids_are_404(client):
    assert client.get("/collections/nope").status_code == 404
    assert client.get("/collections/nope/documents").status_code == 404
    assert client.get("/documents/nope").status_code == 404
    assert client.get("/jobs/nope").status_code == 404
    r = client.post("/collections/nope/documents", files=[("files", ("a.txt", b"x"))])
    assert r.status_code == 404


def test_job_events_stream_ends_when_job_is_done(client, col):
    job_id = upload(client, col["id"], "energy.txt").json()[0]["job_id"]
    drain()
    body = client.get(f"/jobs/{job_id}/events").text
    assert body.startswith("retry:") and '"status": "COMPLETED"' in body


def test_v1_endpoints_still_work_beside_v2(client):
    r = client.post("/api/extract", files={"file": ("a.txt", io.BytesIO(b"Hello V1"), "text/plain")})
    assert r.status_code == 200 and r.json()["text"] == "Hello V1"


def test_v2_answers_503_when_storage_failed(monkeypatch, v2):
    import cadis.main as main

    def broken(app):
        raise OSError("disk is read-only")

    monkeypatch.setattr(main, "_start_v2", broken)
    with TestClient(main.create_app()) as c:
        r = c.get("/collections")
        assert r.status_code == 503 and "read-only" in r.json()["detail"]
        assert c.get("/health").status_code == 200
