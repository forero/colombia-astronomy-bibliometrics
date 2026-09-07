"""Recover full author lists for records truncated at 200 authors by the ADS export.

The ADS export template used for `data/raw/` caps author lists at 200, so any
publication with exactly 200 authors in `data/processed/` is almost certainly a
large collaboration whose list was cut. This script queries the ADS API for
those bibcodes and rewrites the affected rows of `authorships.csv` and the
author counts in `publications.csv`.

Needs an ADS API token, taken from $ADS_DEV_KEY or ~/.ads/dev_key.
"""

import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from institutions import match_institution  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PUBS = ROOT / "data/processed/publications.csv"
AUTHORSHIPS = ROOT / "data/processed/authorships.csv"
CACHE = ROOT / "data/raw/ads_full_authors.json"

API = "https://api.adsabs.harvard.edu/v1/search/query"
TRUNCATION_LIMIT = 200
BATCH = 10  # bibcodes per query; author lists are long, so keep rows small


def read_token():
    token = os.environ.get("ADS_DEV_KEY", "").strip()
    if token:
        return token
    keyfile = Path.home() / ".ads/dev_key"
    if keyfile.exists():
        return keyfile.read_text().strip()
    sys.exit(
        "No ADS token found. Set $ADS_DEV_KEY or write it to ~/.ads/dev_key.\n"
        "Get one at https://ui.adsabs.harvard.edu/user/settings/token"
    )


def truncated_bibcodes():
    with PUBS.open(newline="", encoding="utf-8") as fh:
        return [
            row["bibcode"]
            for row in csv.DictReader(fh)
            if int(row["n_authors"]) >= TRUNCATION_LIMIT
        ]


def query(token, bibcodes):
    """Fetch author + affiliation lists for a batch of bibcodes."""
    q = " OR ".join(f'bibcode:"{b}"' for b in bibcodes)
    params = urllib.parse.urlencode(
        {"q": q, "fl": "bibcode,author,aff,author_count", "rows": len(bibcodes)}
    )
    req = urllib.request.Request(
        f"{API}?{params}", headers={"Authorization": f"Bearer {token}"}
    )
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.load(resp)["response"]["docs"]
        except urllib.error.HTTPError as exc:
            if exc.code == 429:  # rate limited: back off and retry
                time.sleep(5 * (attempt + 1))
                continue
            sys.exit(f"ADS API error {exc.code}: {exc.read().decode()[:400]}")
        except urllib.error.URLError as exc:
            time.sleep(5 * (attempt + 1))
            last = exc
    sys.exit(f"ADS API unreachable: {last}")


def fetch_all(token, bibcodes):
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    todo = [b for b in bibcodes if b not in cache]
    for i in range(0, len(todo), BATCH):
        batch = todo[i : i + BATCH]
        for doc in query(token, batch):
            cache[doc["bibcode"]] = doc
        print(f"  fetched {min(i + BATCH, len(todo))}/{len(todo)}", file=sys.stderr)
        time.sleep(1)  # be polite to the API
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
    missing = [b for b in bibcodes if b not in cache]
    if missing:
        print(f"WARNING: ADS returned nothing for {len(missing)}: {missing}", file=sys.stderr)
    return cache


def rebuild_authorships(cache, bibcodes):
    """Replace the truncated author blocks, keeping every other row untouched."""
    with AUTHORSHIPS.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames
        rows = list(reader)

    targets = set(bibcodes) & set(cache)
    new_blocks = {}
    for bibcode in targets:
        doc = cache[bibcode]
        authors = doc.get("author", [])
        affs = doc.get("aff", []) + [""] * len(authors)
        block = []
        for pos, (author, aff) in enumerate(zip(authors, affs), start=1):
            aff = "" if aff == "-" else aff
            institution, is_colombian = match_institution(aff)
            block.append(
                {
                    "bibcode": bibcode,
                    "position": pos,
                    "author": author,
                    "affiliation_raw": aff,
                    "institution": institution,
                    "is_colombian": is_colombian,
                }
            )
        new_blocks[bibcode] = block

    out, seen = [], set()
    for row in rows:
        b = row["bibcode"]
        if b in new_blocks:
            if b not in seen:  # emit the full block where the old one started
                out.extend(new_blocks[b])
                seen.add(b)
            continue
        out.append(row)

    with AUTHORSHIPS.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out)
    return new_blocks


def update_publications(new_blocks):
    with PUBS.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames
        rows = list(reader)

    for row in rows:
        block = new_blocks.get(row["bibcode"])
        if block is None:
            continue
        row["n_authors"] = len(block)
        row["n_colombian_authors"] = sum(1 for r in block if r["is_colombian"])

    with PUBS.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    token = read_token()
    bibcodes = truncated_bibcodes()
    print(f"{len(bibcodes)} truncated records to recover", file=sys.stderr)
    cache = fetch_all(token, bibcodes)
    new_blocks = rebuild_authorships(cache, bibcodes)
    update_publications(new_blocks)
    for bibcode, block in sorted(new_blocks.items()):
        n_col = sum(1 for r in block if r["is_colombian"])
        print(f"{bibcode}\t{len(block)} authors\t{n_col} colombian")


if __name__ == "__main__":
    main()
