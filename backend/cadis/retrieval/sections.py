"""Find the sections a question names (DECISIONS ADR-028).

"Find the dataset information from Methodology and the results from
Experiments" → two targets, each a set of section IDs (the matched sections
and everything under them, in every visible document that has them).

Matching works on word stems (first five letters), so "Methods" matches
"Methodology" and "Experiments" matches "Experimental Results" only when the
words line up. Numbering ("3.2", "8.") is ignored. To avoid treating ordinary
words as section names ("what were the results", "enrolled in the trial"),
a match needs a cue right next to it:
  * *from / in / under / within / according to / section / chapter / part /
    clause / heading* directly before it (only "the", "to", "of" may sit in
    between): "from the Methodology", "according to the Facilities section";
  * or *section / chapter / part / clause / heading* directly after it:
    "the Storage section", "the study design part".
Measured on the eval set with 732 Wikipedia articles as distractors (whose
sections are called "History", "Release", "Reception" …), a looser rule —
any cue within three words, or a capitalised name — fired on 24 of 60
questions that name no section.

Targets are used as a *soft* filter by ``retrieve``: filtered searches are
fused with the unfiltered one, so a wrong match lowers precision a little but
never hides an answer.
"""

import re
import threading
from collections import OrderedDict, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cadis.storage.tables import Document, Section

_WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*|\d+(?:\.\d+)*")
_NUMBERING = re.compile(r"^\s*(?:\d{1,3}(?:\.\d{1,3}){0,4}|[IVXLC]{1,6})[.)]?\s+")
_STOP = frozenset("""a an and of the for to on in at by with or vs its their our your
this that these those""".split())
_CUE_BEFORE = frozenset("from in under within according section chapter part clause heading".split())
_GLUE = frozenset("the to of".split())          # may stand between a cue and the name
_CUE_NOUN = frozenset("section sections chapter part clause heading".split())
MAX_SECTIONS_PER_TARGET = 25


def stem(word: str) -> str:
    w = word.lower().strip("'’-")
    w = w[:-2] if w.endswith("'s") or w.endswith("’s") else w
    return w[:5] if len(w) > 5 else w


@dataclass
class SectionTarget:
    phrase: str                                        # words as written in the question
    section_ids: list[str] = field(default_factory=list)   # matched + descendants
    matched_ids: list[str] = field(default_factory=list)   # the matched sections themselves
    titles: list[str] = field(default_factory=list)


@dataclass
class _Title:
    id: str
    document_id: str
    title: str
    stems: tuple[str, ...]


def _title_stems(title: str) -> tuple[str, ...]:
    words = _WORD.findall(_NUMBERING.sub("", title))
    return tuple(stem(w) for w in words if w.lower() not in _STOP and not w[0].isdigit())


def _question_tokens(question: str):
    """[(stem, original word, is_stopword, index_in_all_words)]"""
    out = []
    for i, m in enumerate(_WORD.finditer(question)):
        w = m.group()
        out.append((stem(w), w, w.lower() in _STOP, i))
    return out


def _has_cue(tokens, start: int, end: int) -> bool:
    i = start - 1
    while i >= 0 and tokens[i][1].lower() in _GLUE:
        i -= 1
    if i >= 0 and tokens[i][1].lower() in _CUE_BEFORE:
        return True
    return end < len(tokens) and tokens[end][1].lower() in _CUE_NOUN


_MAX_TITLE_WORDS = 8


class _StemLookup:
    """stems → titles, for exact titles and for long titles (3+ words) missing
    their last word ("Data Center" for "Data Center Migration")."""

    def __init__(self, titles: Sequence[_Title]):
        self.map: dict[tuple[str, ...], list[_Title]] = defaultdict(list)
        partial: dict[tuple[str, ...], list[_Title]] = defaultdict(list)
        for t in titles:
            if t.stems and len(t.stems) <= _MAX_TITLE_WORDS:
                self.map[t.stems].append(t)
                if len(t.stems) >= 3:
                    partial[t.stems[:-1]].append(t)
        for key, group in partial.items():
            if key not in self.map:                    # an exact title always wins
                self.map[key] = group

    def get(self, key):
        return self.map.get(key)


def find_mentions(question: str, titles) -> list[tuple[str, list[_Title]]]:
    """[(phrase, matching titles)] for each section name mentioned in the question."""
    tokens = _question_tokens(question)
    content = [(n, t) for n, t in enumerate(tokens) if not t[2]]   # positions of content words
    stems = [t[0] for _, t in content]

    lookup = titles if isinstance(titles, _StemLookup) else _StemLookup(titles)

    found = []        # (start_token, end_token, phrase, titles)
    for i in range(len(stems)):
        for n in range(1, min(_MAX_TITLE_WORDS, len(stems) - i) + 1):
            group = lookup.get(tuple(stems[i:i + n]))
            if not group:
                continue
            start, end = content[i][0], content[i + n - 1][0] + 1
            if _has_cue(tokens, start, end):
                found.append((start, end, " ".join(t[1] for t in tokens[start:end]), group))

    # Longest match wins where matches overlap ("Customers and Partnerships"
    # beats "Customers"); matches of the same span are merged.
    found.sort(key=lambda f: (-(f[1] - f[0]), f[0]))
    kept: list[tuple[int, int, str, list[_Title]]] = []
    for start, end, phrase, group in found:
        same = next((k for k in kept if k[0] == start and k[1] == end), None)
        if same is not None:
            same[3].extend(t for t in group if t not in same[3])
            continue
        if any(start < k[1] and k[0] < end for k in kept):
            continue
        kept.append((start, end, phrase, list(group)))
    kept.sort(key=lambda k: k[0])
    return [(phrase, group) for _, _, phrase, group in kept]


@dataclass
class _TitleIndex:
    titles: list[_Title]
    children: dict[str, list[str]]
    lookup: "_StemLookup" = None

    def __post_init__(self):
        self.lookup = _StemLookup(self.titles)

    def subtree(self, sid: str) -> list[str]:
        out, stack = [], [sid]
        while stack:
            cur = stack.pop()
            out.append(cur)
            stack.extend(self.children.get(cur, []))
        return out


_cache: "OrderedDict[tuple, _TitleIndex]" = OrderedDict()
_cache_lock = threading.Lock()
_CACHE_SIZE = 16


def _title_index(session: Session, allowed: list[str], document_ids) -> _TitleIndex:
    """Section titles of the visible current versions, stemmed once and cached
    until a document in these collections is added, changed or deleted."""
    n, latest = session.execute(select(func.count(Document.id), func.max(Document.updated_at))
                                .where(Document.collection_id.in_(allowed))).one()
    key = (tuple(sorted(allowed)), tuple(sorted(document_ids or ())), n, latest)
    with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]

    q = (select(Section.id, Section.document_id, Section.title, Section.parent_id, Section.level)
         .join(Document, Document.id == Section.document_id)
         .where(Section.version == Document.current_version,
                Document.collection_id.in_(allowed), Section.collection_id.in_(allowed)))
    if document_ids:
        q = q.where(Section.document_id.in_(list(document_ids)))
    rows = session.execute(q).all()
    children: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        if r.parent_id:
            children[r.parent_id].append(r.id)
    index = _TitleIndex([_Title(r.id, r.document_id, r.title, _title_stems(r.title))
                         for r in rows if r.level > 0], dict(children))
    with _cache_lock:
        _cache[key] = index
        while len(_cache) > _CACHE_SIZE:
            _cache.popitem(last=False)
    return index


def resolve(session: Session, question: str, allowed_collection_ids: Sequence[str],
            document_ids: Sequence[str] | None = None,
            candidate_documents: set[str] | None = None) -> list[SectionTarget]:
    """Section targets named in the question.

    ``candidate_documents``: if given, only sections of these documents are
    kept (``retrieve`` passes the documents found by the unfiltered search).
    A named section is meant to narrow down a relevant document; a phrase
    like "in the control group" must not pull in an unrelated article that
    happens to have a "Control" section. Targets left with no section are
    dropped."""
    allowed = list(allowed_collection_ids)
    if not allowed:
        return []
    index = _title_index(session, allowed, document_ids)
    targets = []
    for phrase, group in find_mentions(question, index.lookup):
        if candidate_documents is not None:
            group = [t for t in group if t.document_id in candidate_documents]
        group = group[:MAX_SECTIONS_PER_TARGET]
        if not group:
            continue
        ids: list[str] = []
        for t in group:
            ids.extend(s for s in index.subtree(t.id) if s not in ids)
        targets.append(SectionTarget(phrase, ids, [t.id for t in group],
                                     sorted({t.title for t in group})))
    return targets
