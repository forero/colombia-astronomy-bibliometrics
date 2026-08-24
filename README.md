# Colombian Astronomy Bibliometrics

A bibliometric analysis of astronomy/astrophysics publications with Colombian
institutional affiliation, built from [NASA ADS](https://ui.adsabs.harvard.edu/)
export files. The figure and table set is adapted from the methodology in
Forero-Romero (2024), *"Astronomy in Colombia: a bibliometric perspective"*
([arXiv:2403.02255](https://arxiv.org/abs/2403.02255)).

## Data

`data/raw/` holds two pairs of ADS exports, both for the same underlying
query/result set:

- `export-ads.txt` / `export-ads-1.txt` — the tagged `%R/%T/%A/...` custom
  format, concatenated into `data/raw/combined_ads_export.txt` (724 unique
  records, no overlapping bibcodes between the two files). Carries bibcode,
  title, authors, per-author affiliations, journal, volume, date, page,
  keywords, abstract, publisher, URL, DOI, and arXiv id.
- `export-custom.txt` / `export-custom-1.txt` — a second ADS export template,
  same 724 records in the same order, adding a `num_citations` column that
  the tagged format doesn't carry. It has no bibcode, so citation counts are
  matched back onto the tagged records purely by row position (verified by
  comparing titles at each index — 718/724 match exactly, the rest differ
  only in markup/quoting). See `src/parse_citations.py`.

## Pipeline

```
data/raw/combined_ads_export.txt ──┐
                                    │  src/parse_ads.py (tagged-format parser)
data/raw/export-custom*.txt ───────┤  src/parse_citations.py (citation counts)
                                    ▼
                          src/build_dataset.py
                                    ▼
data/processed/publications.csv   (one row per publication, incl. num_citations)
data/processed/authorships.csv    (one row per author × publication,
                                    with institution match + Colombian flag)
                                    │  src/plots.py
                                    ▼
output/figures/*.png
output/tables/*.csv, *.md
```

### Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python3 src/build_dataset.py   # parse raw exports -> data/processed/*.csv
python3 src/plots.py           # -> output/figures/*.png, output/tables/*
```

## Institution matching

ADS affiliation strings are free text typed by authors, so institution
identification is heuristic: `src/institutions.py` matches known Colombian
university names/abbreviations (Spanish and the English forms ADS sometimes
normalizes to, e.g. "National University of Colombia" for Universidad
Nacional) against each affiliation string. ~97% of affiliation strings that
mention "Colombia" match a specific institution; the rest fall into an
"Other Colombian institution" bucket. Extend the pattern list in that file as
new variants turn up.

Author- and institution-level rankings (top authors, top institutions,
co-authorship network) are restricted to authorships with a Colombian
affiliation, so they aren't swamped by the hundreds of non-Colombian members
of huge international collaborations (DESI, LIGO/Virgo/KAGRA, Pierre Auger)
that a Colombian group also belongs to.

## Author name matching

There's no author-id (ORCID) in this export, and the same person shows up
under several ADS name-string variants across records — different levels of
given-name detail ("Forero-Romero, J. E." vs. "Forero-Romero, Jaime E."),
occasional metadata typos ("Jamie E." for "Jaime E."), and inconsistent
compound-surname splits ("Enea Romano, Antonio" vs. "Romano, Antonio Enea").
`src/name_matching.py` merges these heuristically among Colombian-affiliated
authorships: names with the same surname are merged when one's initials are
a prefix of the other's, and names are also merged when they spell out the
same full given/surname words regardless of which side of the comma they
land on. The cluster's most fully-spelled-out variant is used as the display
name. This is conservative by construction but can still occasionally
over-merge two different people who share a surname and are only ever
recorded with a bare initial, or under-merge someone who publishes under
genuinely different name spellings.

## Known limitations

- **2027 is excluded from all analysis.** At the time of writing there is a
  single in-press 2027 record (already assigned a bibcode) — too sparse a
  bucket to be meaningful in year-based trends, and it would otherwise show
  up as a one-off drop in every time series. `build_dataset.py` drops it
  before writing `publications.csv`/`authorships.csv`.
- **Institution matching is substring-based**, not a controlled ROR/GRID
  lookup, and Colombian secondary schools / non-academic institutions that
  happen to add "Colombia" to their affiliation string are counted the same
  as universities.
- **Author lists are truncated at 200** by this ADS export template for the
  handful of huge collaboration papers (DESI, LIGO/Virgo/KAGRA, Pierre
  Auger — several have thousands of real authors). `n_authors` for those
  records is a floor, not the true count, which caps the right edge of
  Fig. 2 (avg. authors/year) and Fig. 10 (citations vs. authors) at 200.
- **Citation counts are a single ADS snapshot** (as of the export date), not
  a per-year citation history, so "citations per year since publication" in
  Fig. 10/Table 1 is total citations divided by paper age, not an observed
  citation rate curve like the reference paper's Web-of-Science-derived
  figures.

## Outputs

**Figures** (`output/figures/`):
1. `fig1_publications_over_time.png` — cumulative and per-year publication counts (log scale)
2. `fig2_avg_authors_per_year.png` — mean/median authors per publication by year
3. `fig3_authors_distribution.png` — log-log histogram of authorship size
4. `fig4_top_institutions.png` — top 20 Colombian institutions by publication count
5. `fig5_top_authors.png` — top 20 Colombian-affiliated authors by publication count
6. `fig6_top_journals.png` — top 15 journals
7. `fig7_top_keywords.png` — top 25 keywords
8. `fig8_coauthorship_network.png` — co-authorship network among Colombian-affiliated authors with ≥5 publications
9. `fig9_citations_per_year.png` — total and mean citations by publication year
10. `fig10_citations_vs_authors.png` — citation rate vs. collaboration size, with marginal histograms and Pearson r

**Tables** (`output/tables/`): `table1_institutions` (adds total citations and
h-index per institution), `table2_top_authors`, `table3_journals`,
`table4_top_cited` (top 10 most-cited articles) — all CSV + Markdown — plus
`summary_stats.md`.

As of the current data snapshot: 723 publications (1980–2026; the sole 2027
in-press record is excluded, see Known limitations), spanning 56 journals,
about 380 unique authors (after name matching) with a Colombian affiliation,
26,550 total citations, and an overall h-index of 65. The most-cited paper is
the 2017 multi-messenger neutron-star-merger discovery (GW170817), with 4,140
citations.
