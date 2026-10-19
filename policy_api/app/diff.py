"""Clause-level diff between two versions of a policy."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from .documents import Clause, terms_defined

RENUMBER_MATCH = 0.6  # similarity needed to treat a moved clause as the same clause


@dataclass
class Change:
    number: str
    kind: str  # modified | added | removed | renumbered
    heading: str
    old_text: str
    new_text: str
    terms: list[str] = field(default_factory=list)
    old_number: str | None = None

    @property
    def label(self) -> str:
        title = f" ({self.heading})" if self.heading else ""
        return {
            "modified": f"§{self.number} changed{title}",
            "added": f"§{self.number} was added{title}",
            "removed": f"§{self.number} was removed{title}",
            "renumbered": f"§{self.old_number} is now §{self.number}{title}",
        }[self.kind]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _sort_key(number: str) -> tuple[int, ...]:
    return tuple(int(p) if p.isdigit() else 0 for p in number.split("~")[0].split("."))


def _change(kind: str, old: Clause | None, new: Clause | None) -> Change:
    old_text = old.text if old else ""
    new_text = new.text if new else ""
    terms = sorted(set(terms_defined(old_text)) | set(terms_defined(new_text)))
    number = new.number if new else old.number  # type: ignore[union-attr]
    old_number = old.number if old and new and old.number != new.number else None
    heading = (new or old).heading  # type: ignore[union-attr]
    return Change(number, kind, heading, old_text, new_text, terms, old_number)


def diff_clauses(old: list[Clause], new: list[Clause]) -> list[Change]:
    old_by = {c.number: c for c in old}
    new_by = {c.number: c for c in new}
    changes: list[Change] = []

    for c in new:
        o = old_by.get(c.number)
        if o and _norm(o.text) != _norm(c.text):
            changes.append(_change("modified", o, c))

    unmatched_old = [c for c in old if c.number not in new_by]
    unmatched_new = [c for c in new if c.number not in old_by]
    for n in list(unmatched_new):
        best, score = None, 0.0
        for o in unmatched_old:
            s = SequenceMatcher(None, _norm(o.text), _norm(n.text)).ratio()
            if s > score:
                best, score = o, s
        if best is not None and score >= RENUMBER_MATCH:
            unmatched_old.remove(best)
            unmatched_new.remove(n)
            same = _norm(best.text) == _norm(n.text)
            changes.append(_change("renumbered" if same else "modified", best, n))

    changes += [_change("added", None, n) for n in unmatched_new]
    changes += [_change("removed", o, None) for o in unmatched_old]
    return sorted(changes, key=lambda ch: _sort_key(ch.number))
