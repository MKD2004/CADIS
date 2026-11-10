"""Storage layer: migrations, upserts, FTS5 triggers, cascades (ADR-006/008/014)."""

import pytest
from sqlalchemy import inspect

from cadis.index.keyword_store import to_match_query
from cadis.storage import repositories as repo
from cadis.storage.db import get_engine, session_scope
from cadis.storage.files import FileStore
from cadis.storage.tables import Document


def rows(doc_id, col_id, version=1, text="The monthly retainer is due on the first day."):
    sections = [{"id": f"s-{version}", "document_id": doc_id, "collection_id": col_id,
                 "version": version, "parent_id": None, "title": "Doc", "path": "", "level": 0,
                 "ordinal": 0, "page": 1, "char_start": 0, "char_end": len(text)}]
    chunks = [{"id": f"c-{version}", "document_id": doc_id, "collection_id": col_id,
               "version": version, "ordinal": 0, "page": 1, "page_end": 1,
               "section_id": f"s-{version}", "section_path": "Payment Terms", "char_start": 0,
               "char_end": len(text), "tokens": 9, "text": text, "prev_id": None, "next_id": None}]
    return sections, chunks


@pytest.fixture
def doc(v2):
    with session_scope() as s:
        col = repo.create_collection(s, "default", "C")
        d = repo.create_document(s, col.id, "a.txt", "b" * 64, 10)
        return d.id, col.id


def write(doc_id, col_id, version=1, **kw):
    with session_scope() as s:
        repo.write_version(s, doc_id, version, "text", *rows(doc_id, col_id, version, **kw))
        repo.set_document_fields(s, doc_id, current_version=version)


def kw(q, col_id):
    with session_scope() as s:
        return [c.id for c, _ in repo.keyword_search(s, to_match_query(q), [col_id], 10)]


def test_migrations_create_all_tables(v2):
    names = set(inspect(get_engine()).get_table_names())
    assert {"tenant", "collection", "membership", "document", "document_text", "section",
            "chunk", "analysis_result", "job", "entity", "mention", "chunk_fts",
            "alembic_version"} <= names


def test_writing_a_version_twice_does_not_duplicate(doc):
    doc_id, col_id = doc
    write(doc_id, col_id)
    write(doc_id, col_id)
    with session_scope() as s:
        assert repo.counts(s) == {"chunks": 1, "fts": 1, "sections": 1}


def test_fts_follows_updates_and_section_paths(doc):
    doc_id, col_id = doc
    write(doc_id, col_id)
    assert kw("retainer", col_id) == ["c-1"]
    assert kw("payment terms", col_id) == ["c-1"]          # heading words are indexed too
    write(doc_id, col_id, text="Completely different words now.")
    assert kw("retainer", col_id) == []
    assert kw("different", col_id) == ["c-1"]


def test_keyword_search_sees_only_the_current_version(doc):
    doc_id, col_id = doc
    write(doc_id, col_id, version=1)
    with session_scope() as s:
        repo.write_version(s, doc_id, 2, "t", *rows(doc_id, col_id, 2))   # not flipped yet
    assert kw("retainer", col_id) == ["c-1"]
    with session_scope() as s:
        repo.set_document_fields(s, doc_id, current_version=2)
    assert kw("retainer", col_id) == ["c-2"]


def test_deleting_a_document_cascades_to_everything(doc):
    doc_id, col_id = doc
    write(doc_id, col_id)
    with session_scope() as s:
        repo.create_job(s, "ingest", doc_id, 3)
    with session_scope() as s:
        s.delete(s.get(Document, doc_id))
    with session_scope() as s:
        assert repo.counts(s) == {"chunks": 0, "fts": 0, "sections": 0}
        assert repo.latest_job_for(s, doc_id) is None
    assert kw("retainer", col_id) == []


@pytest.mark.parametrize("question", [
    'NEAR(" -retainer*', "payment: AND OR NOT", '"""', "^ { } ( )", "what is it?", "",
])
def test_any_question_is_a_safe_fts_query(doc, question):
    doc_id, col_id = doc
    write(doc_id, col_id)
    kw(question, col_id)                                   # must not raise


def test_stopwords_are_dropped_and_words_quoted():
    assert to_match_query("What is the retainer's fee?") == '"retainer\'s" OR "fee"'


def test_content_queries_require_allowed_collections(doc):
    with session_scope() as s:
        for call in (lambda: repo.get_document(s, doc[0], None),
                     lambda: repo.list_documents(s, doc[1], None),
                     lambda: repo.keyword_search(s, '"x"', None, 5)):
            with pytest.raises(ValueError):
                call()
        assert repo.get_document(s, doc[0], []) is None


def test_file_store_dedupes_and_validates(tmp_path):
    fs = FileStore(tmp_path)
    a = fs.save(b"hello")
    assert fs.save(b"hello") == a and fs.read(a) == b"hello"
    assert len(list(tmp_path.iterdir())) == 1
    with pytest.raises(ValueError):
        fs.path("../../etc/passwd")
    fs.delete(a)
    assert not fs.exists(a)
