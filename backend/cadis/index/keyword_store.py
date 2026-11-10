"""Keyword (BM25) search over SQLite FTS5 (DECISIONS ADR-008).

The FTS5 index is kept in step with the ``chunk`` table by triggers (see the
first migration), so there is no separate upsert or delete here: writing or
deleting chunks updates the index in the same transaction. This module only
turns a question into a safe FTS5 query and runs the search.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.orm import Session

from cadis.storage import repositories

_WORD = re.compile(r"[\w][\w'’-]*", re.UNICODE)
_STOPWORDS = frozenset("""
a an and are as at be by did do does for from had has have how i in is it its of on or
that the their there these this to was were what when where which who whom why will
with would you your can could should may might than then them they he she his her
""".split())


def to_match_query(question: str) -> str:
    """Quote every content word and OR them together.

    Quoting stops user text from being read as FTS5 syntax (``NEAR``, ``-``,
    ``:``, ``*``, unbalanced quotes), so no question can cause a query error.
    """
    words, seen = [], set()
    for w in _WORD.findall(question.lower()):
        w = w.strip("'’-")
        if not w or w in _STOPWORDS or w in seen:
            continue
        seen.add(w)
        words.append('"' + w.replace('"', '""') + '"')
    return " OR ".join(words)


@dataclass
class KeywordHit:
    id: str
    score: float          # BM25, higher = better
    document_id: str
    section_path: str


class SqliteKeywordStore:
    def search(self, session: Session, question: str, allowed_collection_ids: Sequence[str],
               k: int, document_ids: Sequence[str] | None = None) -> list[KeywordHit]:
        match = to_match_query(question)
        rows = repositories.keyword_search(session, match, allowed_collection_ids, k, document_ids)
        return [KeywordHit(c.id, score, c.document_id, c.section_path) for c, score in rows]
