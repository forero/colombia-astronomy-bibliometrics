"""Parse the combined ADS export into tidy CSVs for analysis.

Usage:
    python src/build_dataset.py

Reads data/raw/combined_ads_export.txt and writes:
    data/processed/publications.csv  (one row per publication)
    data/processed/authorships.csv   (one row per author x publication)
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from institutions import match_institution
from parse_ads import parse_file

ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = ROOT / "data" / "raw" / "combined_ads_export.txt"
OUT_DIR = ROOT / "data" / "processed"


def build() -> tuple[pd.DataFrame, pd.DataFrame]:
    publications = parse_file(RAW_PATH)

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
    print(f"Parsed {len(pubs_df)} unique publications, {len(authors_df)} authorships")
    print(f"Wrote {OUT_DIR / 'publications.csv'}")
    print(f"Wrote {OUT_DIR / 'authorships.csv'}")
