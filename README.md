# Colombian Astronomy Bibliometrics

A bibliometric analysis of astronomy/astrophysics publications with Colombian
institutional affiliation, built from [NASA ADS](https://ui.adsabs.harvard.edu/)
export files. The figure and table set is adapted from the methodology in
Forero-Romero (2024), *"Astronomy in Colombia: a bibliometric perspective"*
([arXiv:2403.02255](https://arxiv.org/abs/2403.02255)).

## Data

`data/raw/` holds two ADS "custom format" exports (`export-ads.txt`,
`export-ads-1.txt`), concatenated into `data/raw/combined_ads_export.txt`
(724 unique records, no overlapping bibcodes between the two source files).

Each record carries: bibcode, title, authors, per-author affiliations,
journal, volume, date, page, keywords, abstract, publisher, URL, DOI, and
arXiv id. **There is no citation-count field in this export type**, so
citation-based figures from the reference paper (annual citations, citation
rate vs. collaboration size, highly-cited-article counts, cross-country
comparisons) are not reproduced here — everything below is derived only from
publication metadata.

## Pipeline

```
data/raw/combined_ads_export.txt
        │  src/parse_ads.py   (tagged-format parser)
        ▼
data/processed/publications.csv   (one row per publication)
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

## Known limitations

- **No citation data** — see above.
- **Author name disambiguation is not attempted.** The same person can appear
  under several ADS name-string variants (initials vs. full name, occasional
  typos in the source metadata), so per-author publication counts and the
  co-authorship network undercount some individuals. Resolving this properly
  needs ORCID-linked ADS records, which aren't in a plain custom-format
  export.
- **Institution matching is substring-based**, not a controlled ROR/GRID
  lookup, and Colombian secondary schools / non-academic institutions that
  happen to add "Colombia" to their affiliation string are counted the same
  as universities.

## Outputs

**Figures** (`output/figures/`):
1. `fig1_publications_over_time.png` — cumulative and per-year publication counts
2. `fig2_avg_authors_per_year.png` — mean/median authors per publication by year
3. `fig3_authors_distribution.png` — log-log histogram of authorship size
4. `fig4_top_institutions.png` — top 20 Colombian institutions by publication count
5. `fig5_top_authors.png` — top 20 authors by publication count
6. `fig6_top_journals.png` — top 15 journals
7. `fig7_top_keywords.png` — top 25 keywords
8. `fig8_coauthorship_network.png` — co-authorship network among Colombian-affiliated authors with ≥5 publications

**Tables** (`output/tables/`): `table1_institutions`, `table2_top_authors`,
`table3_journals` (CSV + Markdown), and `summary_stats.md`.

As of the current data snapshot: 724 publications (1980–2027, including
in-press/forthcoming items already assigned a bibcode), spanning 57 journals
and about 500 unique authors with a Colombian affiliation.
