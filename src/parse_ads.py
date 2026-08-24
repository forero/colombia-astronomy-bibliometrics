"""Parser for ADS 'custom format' tagged exports (%R, %T, %A, %F, ... records).

Records are separated by blank lines. Each field starts with '%<letter> '
and may wrap onto following lines that do NOT start with '%'; those
continuation lines belong to the previous field and are joined back in
(the exporter hard-wraps long lines at a fixed column).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


AFFIL_RE = re.compile(r"([A-Z]{1,2})\(((?:[^()]|\([^()]*\))*)\)")


@dataclass
class Publication:
    bibcode: str = ""
    title: str = ""
    authors: list[str] = field(default_factory=list)
    affiliations: list[str] = field(default_factory=list)  # aligned with authors
    journal: str = ""
    volume: str = ""
    year: int | None = None
    month: int | None = None
    page: str = ""
    keywords: list[str] = field(default_factory=list)
    abstract: str = ""
    publisher: str = ""
    url: str = ""
    doi: str = ""
    arxiv_id: str = ""
    num_citations: int | None = None  # filled in by build_dataset.py, not parsed here


def _split_records(text: str) -> list[str]:
    # Records are separated by one or more blank lines.
    raw_records = re.split(r"\n\s*\n", text)
    return [r for r in raw_records if r.strip()]


_WORD_HYPHEN_BREAK = re.compile(r"\S-$")


def _join_continuations(record: str) -> list[str]:
    """Rejoin wrapped lines so each list entry is one full '%X ...' field.

    The exporter hard-wraps at a fixed column with no soft-hyphenation: a
    line that ends in "<non-space>-" was broken mid-word at a hyphen that is
    part of the original text (e.g. "Forero-\nRomero", "Font-\nRibera",
    "non-\nGaussianities") and must be rejoined with no space. A line ending
    in "<space>-" (a dash used as punctuation, e.g. an address range "18A -\n12")
    is an ordinary word-wrap break and needs a space when rejoined.
    """
    lines = record.split("\n")
    fields: list[str] = []
    for line in lines:
        if line.startswith("%"):
            fields.append(line)
        elif fields:
            prev = fields[-1].rstrip()
            sep = "" if _WORD_HYPHEN_BREAK.search(prev) else " "
            fields[-1] = prev + sep + line.strip()
    return fields


def _parse_affiliations(raw: str) -> dict[str, str]:
    """Parse '%F AA(inst1), AB(inst2), ...' into {'AA': 'inst1', ...}."""
    return {code: inst.strip() for code, inst in AFFIL_RE.findall(raw)}


def _author_codes(n_authors: int) -> list[str]:
    """AA, AB, ..., AZ, BA, BB, ... matching ADS's affiliation lettering."""
    codes = []
    for i in range(n_authors):
        first = chr(ord("A") + i // 26)
        second = chr(ord("A") + i % 26)
        codes.append(first + second)
    return codes


def parse_record(record: str) -> Publication | None:
    fields = _join_continuations(record)
    pub = Publication()
    affil_map: dict[str, str] = {}

    for line in fields:
        tag, _, value = line.partition(" ")
        value = value.strip()
        if tag == "%R":
            pub.bibcode = value
        elif tag == "%T":
            pub.title = value
        elif tag == "%A":
            pub.authors = [a.strip() for a in value.split(";") if a.strip()]
        elif tag == "%F":
            affil_map = _parse_affiliations(value)
        elif tag == "%J":
            pub.journal = value
        elif tag == "%V":
            pub.volume = value
        elif tag == "%D":
            m = re.match(r"(?:(\d{1,2})/)?(\d{4})", value)
            if m:
                pub.month = int(m.group(1)) if m.group(1) else None
                pub.year = int(m.group(2))
        elif tag == "%P":
            pub.page = value
        elif tag == "%K":
            pub.keywords = [k.strip() for k in value.split(",") if k.strip()]
        elif tag == "%B":
            pub.abstract = value
        elif tag == "%H":
            pub.publisher = value
        elif tag == "%U":
            pub.url = value
        elif tag == "%Y":
            if value.upper().startswith("DOI:"):
                pub.doi = value.split(":", 1)[1].strip()
            elif "eprintid" in value.lower():
                pub.arxiv_id = value.split(":", 1)[1].strip()

    if not pub.bibcode:
        return None

    codes = _author_codes(len(pub.authors))
    pub.affiliations = [affil_map.get(code, "") for code in codes]
    return pub


def parse_file(path: str | Path) -> list[Publication]:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return [
        pub
        for record in _split_records(text)
        if (pub := parse_record(record)) is not None
    ]
