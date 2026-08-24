"""Parse the combined ADS export into tidy CSVs for analysis.

Usage:
    python src/build_dataset.py

Reads data/raw/combined_ads_export.txt (bibliographic metadata) and the
data/raw/export-custom*.txt pair (citation counts, matched back in by row
position -- see parse_citations.py), and writes:
    data/processed/publications.csv  (one row per publication)
    data/processed/authorships.csv   (one row per author x publication)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

from institutions import match_institution
from parse_ads import parse_file
from parse_citations import load_citation_counts, load_titles

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
RAW_PATH = RAW_DIR / "combined_ads_export.txt"
CITATION_PATHS = [RAW_DIR / "export-custom.txt", RAW_DIR / "export-custom-1.txt"]
OUT_DIR = ROOT / "data" / "processed"


def _normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", title.lower())


def _load_citations() -> list[int]:
    counts: list[int] = []
    for path in CITATION_PATHS:
        counts.extend(load_citation_counts(path))
    return counts


def _check_alignment(publications: list, citation_titles: list[str]) -> None:
    if len(publications) != len(citation_titles):
        print(
            f"WARNING: {len(publications)} bibliographic records vs "
            f"{len(citation_titles)} citation rows -- counts will misalign, "
            "skipping citation merge.",
            file=sys.stderr,
        )
        return
    mismatches = sum(
        1
        for pub, title in zip(publications, citation_titles)
        if _normalize_title(pub.title) != _normalize_title(title)
    )
    if mismatches:
        rate = mismatches / len(publications)
        print(
            f"NOTE: {mismatches}/{len(publications)} ({rate:.1%}) title "
            "mismatches between the tagged and citation exports at the same "
            "row position -- expected to be a handful of markup/quoting "
            "differences, not misalignment.",
            file=sys.stderr,
        )


def build() -> tuple[pd.DataFrame, pd.DataFrame]:
    publications = parse_file(RAW_PATH)

    citation_counts = _load_citations()
    citation_titles = []
    for path in CITATION_PATHS:
        citation_titles.extend(load_titles(path))
    has_citations = len(citation_counts) == len(publications)
    if has_citations:
        _check_alignment(publications, citation_titles)
        for pub, n_cit in zip(publications, citation_counts):
            pub.num_citations = n_cit
    else:
        _check_alignment(publications, citation_titles)
        for pub in publications:
            pub.num_citations = None

    # De-duplicate by bibcode in case the two source exports overlap.
    seen: set[str] = set()
    unique_pubs = []
    for pub in publications:
        if pub.bibcode in seen:
            continue
        seen.add(pub.bibcode)
        unique_pubs.append(pub)

    pub_rows = []
    author_rows = []
    for pub in unique_pubs:
        colombian_flags = []
        for position, (author, affil) in enumerate(
            zip(pub.authors, pub.affiliations), start=1
        ):
            institution, is_colombian = match_institution(affil)
            colombian_flags.append(is_colombian)
            author_rows.append(
                {
                    "bibcode": pub.bibcode,
                    "position": position,
                    "author": author,
                    "affiliation_raw": affil,
                    "institution": institution,
                    "is_colombian": is_colombian,
                }
            )

        pub_rows.append(
            {
                "bibcode": pub.bibcode,
                "title": pub.title,
                "year": pub.year,
                "month": pub.month,
                "journal": pub.journal,
                "volume": pub.volume,
                "page": pub.page,
                "n_authors": len(pub.authors),
                "n_colombian_authors": sum(colombian_flags),
                "num_citations": pub.num_citations,
                "keywords": "; ".join(pub.keywords),
                "doi": pub.doi,
                "arxiv_id": pub.arxiv_id,
                "url": pub.url,
            }
        )

    pubs_df = pd.DataFrame(pub_rows).sort_values(["year", "month"], na_position="last")
    authors_df = pd.DataFrame(author_rows)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pubs_df.to_csv(OUT_DIR / "publications.csv", index=False)
    authors_df.to_csv(OUT_DIR / "authorships.csv", index=False)

    return pubs_df, authors_df


if __name__ == "__main__":
    pubs_df, authors_df = build()
    n_with_citations = pubs_df["num_citations"].notna().sum()
    print(f"Parsed {len(pubs_df)} unique publications, {len(authors_df)} authorships")
    print(f"Citation counts available for {n_with_citations}/{len(pubs_df)} publications")
    print(f"Wrote {OUT_DIR / 'publications.csv'}")
    print(f"Wrote {OUT_DIR / 'authorships.csv'}")
