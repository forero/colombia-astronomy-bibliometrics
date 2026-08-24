"""Heuristic merging of ADS author-name variants that refer to the same person.

ADS author strings for the same person vary in how much of the given name is
spelled out -- "Forero-Romero, J. E.", "Forero-Romero, Jaime E.",
"Forero-Romero, Jaime" -- and occasionally carry a typo in the source
metadata ("Jamie E." for "Jaime E."). There is no author-id (ORCID) in this
export to disambiguate properly, so this uses a standard bibliometric
heuristic instead: two name strings are merged when they share the same
(accent-stripped) surname and one's initials are a prefix of the other's.
This is conservative by construction (it never merges different surnames or
conflicting initials) but can still occasionally over-merge two different
people who share a surname and have only an initial on record, or
under-merge someone who publishes under two different surname spellings.
"""
from __future__ import annotations

import unicodedata
from collections import Counter, defaultdict


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _split_name(name: str) -> tuple[str, str]:
    surname, _, given = name.partition(",")
    return surname.strip(), given.strip()


def _normalize_surname(surname: str) -> str:
    surname = _strip_accents(surname).lower()
    surname = surname.replace("-", " ").replace(".", " ")
    return " ".join(surname.split())


def _initials(given: str) -> str:
    given = _strip_accents(given).upper()
    words = given.replace("-", " ").replace(".", " ").split()
    return "".join(w[0] for w in words if w)


def _full_word_tokens(name: str) -> frozenset[str]:
    """Spelled-out (non-initial) name words, regardless of surname/given split.

    Catches compound-surname records where ADS puts a different split point
    each time -- e.g. "Enea Romano, Antonio" (surname "Enea Romano") vs.
    "Romano, Antonio Enea" (surname "Romano" only) both yield
    {enea, romano, antonio}.
    """
    surname, given = _split_name(name)
    text = _strip_accents(f"{surname} {given}").lower()
    words = text.replace("-", " ").replace(".", " ").split()
    return frozenset(w for w in words if len(w) > 1)


class _UnionFind:
    def __init__(self, items: list[str]) -> None:
        self.parent = {item: item for item in items}

    def find(self, x: str) -> str:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def build_canonical_name_map(names: list[str]) -> dict[str, str]:
    """Map each raw author-name string to a canonical name for its cluster.

    Names are grouped by normalized surname, then unioned within each group
    when one's initials are a prefix of the other's. The canonical name for
    a cluster is its member with the most fully spelled-out given name,
    breaking ties by which spelling occurs more often -- a rare metadata
    typo ("Jamie E." for "Jaime E.") should not win just because it happens
    to sort alphabetically after the correct spelling.
    """
    frequency = Counter(names)
    unique_names = list(dict.fromkeys(names))
    parsed = {name: _split_name(name) for name in unique_names}

    by_surname: dict[str, list[str]] = defaultdict(list)
    for name, (surname, _) in parsed.items():
        by_surname[_normalize_surname(surname)].append(name)

    uf = _UnionFind(unique_names)
    for group in by_surname.values():
        keyed = [(name, _initials(parsed[name][1])) for name in group]
        for i in range(len(keyed)):
            name_a, initials_a = keyed[i]
            for j in range(i + 1, len(keyed)):
                name_b, initials_b = keyed[j]
                if initials_a.startswith(initials_b) or initials_b.startswith(initials_a):
                    uf.union(name_a, name_b)

    # Second pass: merge records that spell out the same full name words but
    # split them differently between surname and given name (compound
    # surnames written inconsistently, e.g. "Enea Romano, Antonio" vs.
    # "Romano, Antonio Enea"). Require >= 2 shared full words to keep this
    # conservative.
    by_tokens: dict[frozenset[str], list[str]] = defaultdict(list)
    for name in unique_names:
        tokens = _full_word_tokens(name)
        if len(tokens) >= 2:
            by_tokens[tokens].append(name)
    for group in by_tokens.values():
        for name in group[1:]:
            uf.union(group[0], name)

    clusters: dict[str, list[str]] = defaultdict(list)
    for name in unique_names:
        clusters[uf.find(name)].append(name)

    canonical_map: dict[str, str] = {}
    for members in clusters.values():
        canonical = max(members, key=lambda n: _completeness_key(n, frequency))
        for name in members:
            canonical_map[name] = canonical
    return canonical_map


def _completeness_key(name: str, frequency: Counter) -> tuple[int, int, int, str]:
    """Sort key preferring the most fully spelled-out, most common given name.

    Ranks by how many full (non-initial) words the given name has -- not by
    raw string length, since a garbled ADS split like "Acevedo, D. D.
    Herrera" can be a longer string than the correct "Herrera Acevedo,
    Daniel David" without being more complete. Ties (same completeness) fall
    back to whichever spelling is more common in the data, and only then to
    alphabetical order, so a one-off typo doesn't win a tie against the
    correct spelling just because it happens to sort later.
    """
    _, given = _split_name(name)
    words = given.replace("-", " ").replace(".", " ").split()
    full_word_count = sum(1 for w in words if len(w) > 1)
    return (full_word_count, len(given), frequency[name], name)
