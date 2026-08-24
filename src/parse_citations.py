"""Parser for the ADS "custom format" citation-count exports.

These files (`export-custom*.txt`) are a different ADS export template from
the tagged `%R/%T/%A/...` one in parse_ads.py: same result set, same sort
order, but as CSV rows with an extra num_citations column. The exporter has
a quirk where every data row is prefixed with the literal template string
"%ZHeader:'Authors,Year,Title,Affiliations,Citations'" glued directly onto
the CSV text with no separator, so that prefix has to be stripped before the
line can be parsed as CSV.

Because this format carries no bibcode/DOI, citation counts are matched back
to the tagged export purely by row position: export-custom.txt lists the
same records, in the same order, as export-ads.txt (and likewise for the
"(1)" pair) -- verified by comparing titles record-by-record. See
build_dataset.py for how the two sources are zipped together.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

_HEADER_PREFIX = "%ZHeader:'Authors,Year,Title,Affiliations,Citations'"


def load_citation_counts(path: str | Path) -> list[int]:
    lines = Path(path).read_text(encoding="utf-8", errors="replace").split("\n")
    counts: list[int] = []
    for line in lines[1:]:  # skip the CSV header line
        if not line.strip():
            continue
        line = line.replace(_HEADER_PREFIX, "", 1)
        row = next(csv.reader(io.StringIO(line)))
        counts.append(int(row[-1]))
    return counts


def load_titles(path: str | Path) -> list[str]:
    """Titles as recorded in the custom export, for row-alignment sanity checks."""
    lines = Path(path).read_text(encoding="utf-8", errors="replace").split("\n")
    titles: list[str] = []
    for line in lines[1:]:
        if not line.strip():
            continue
        line = line.replace(_HEADER_PREFIX, "", 1)
        row = next(csv.reader(io.StringIO(line)))
        titles.append(row[2] if len(row) > 2 else "")
    return titles
