"""Small, dependency-free BM25F ranking used by the retrieve and ask tools."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

# Letters that NFKD does not decompose into an ASCII base letter.
_TRANSLATE = str.maketrans(
    {
        "ø": "o",
        "æ": "ae",
        "œ": "oe",
        "ß": "ss",
        "ł": "l",
        "đ": "d",
        "ð": "d",
        "þ": "th",
        "ı": "i",
    }
)

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")

STOPWORDS = frozenset(
    """
    a about above after again all also am an and any are as at be because been before being
    below between both but by can could did do does doing down during each few for from further
    had has have having he her here hers him his how i if in into is it its itself just me more
    most my no nor not now of off on once only or other our ours out over own same she should so
    some such than that the their theirs them then there these they this those through to too
    under until up very was we were what when where which while who whom why will with would you
    your yours please tell show find give get know us let anything something everything
    """.split()
)

FIELD_BOOSTS = {"title": 2.5, "people": 0.8, "body": 1.0}
K1 = 1.2
B = 0.75


def normalize(text: str) -> str:
    """Lowercase and strip accents, so 'Østerdal' and 'Osterdal' compare equal."""
    text = text.lower().translate(_TRANSLATE)
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def stem(token: str) -> str:
    if token.isdigit() or len(token) <= 3:
        return token
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("ing") and len(token) > 5:
        return token[:-3]
    if token.endswith("ed") and len(token) > 4:
        return token[:-2]
    if token.endswith("es") and len(token) > 4 and token[-3] in "sxz":
        return token[:-2]
    if token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def tokenize(text: str) -> list[str]:
    """Tokenize text. Hyphenated codes such as 'PO-7781' yield the code and its parts."""
    tokens: list[str] = []
    for match in _TOKEN_RE.finditer(normalize(text)):
        word = match.group(0)
        if "-" in word:
            tokens.append(word)
            parts = word.split("-")
        else:
            parts = [word]
        for part in parts:
            if len(part) < 2 or part in STOPWORDS:
                continue
            tokens.append(stem(part))
    return tokens


def search_terms(query: str, limit: int = 10) -> list[str]:
    """Key terms of a query in their original spelling, for searchMetadata."""
    terms: list[str] = []
    seen: set[str] = set()
    for raw in re.findall(r"\w+(?:-\w+)*", query):
        norm = normalize(raw)
        if len(norm) < 2 or norm in STOPWORDS or norm in seen:
            continue
        seen.add(norm)
        terms.append(raw)
        if len(terms) >= limit:
            break
    return terms


@dataclass
class Doc:
    doc_id: str
    fields: dict[str, str]
    timestamp: float = 0.0
    tf: Counter = field(default_factory=Counter)
    length: float = 0.0

    def __post_init__(self) -> None:
        for name, text in self.fields.items():
            boost = FIELD_BOOSTS.get(name, 1.0)
            toks = tokenize(text or "")
            for tok in toks:
                self.tf[tok] += boost
            self.length += boost * len(toks)


class Index:
    """BM25F over a small corpus. Corpus statistics are computed per query over the
    documents the caller is allowed to see, so hidden items cannot influence scores."""

    def __init__(self, docs: list[Doc]):
        self.docs = {d.doc_id: d for d in docs}

    def search(self, query: str, allowed: set[str], top: int = 10) -> list[tuple[str, float]]:
        q_tokens = list(dict.fromkeys(tokenize(query)))
        candidates = [self.docs[d] for d in allowed if d in self.docs]
        if not q_tokens or not candidates:
            return []
        n = len(candidates)
        avgdl = sum(d.length for d in candidates) / n or 1.0
        df = {t: sum(1 for d in candidates if t in d.tf) for t in q_tokens}
        scored: list[tuple[float, float, str]] = []
        for doc in candidates:
            score = 0.0
            for tok in q_tokens:
                tf = doc.tf.get(tok, 0.0)
                if not tf:
                    continue
                idf = math.log(1 + (n - df[tok] + 0.5) / (df[tok] + 0.5))
                denom = tf + K1 * (1 - B + B * doc.length / avgdl)
                score += idf * tf * (K1 + 1) / denom
            if score > 0:
                scored.append((round(score, 6), doc.timestamp, doc.doc_id))
        # Higher score first; the newer item wins a tie.
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return [(doc_id, score) for score, _, doc_id in scored[:top]]
