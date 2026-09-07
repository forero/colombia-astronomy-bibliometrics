"""Generate figures and tables for the Colombian astronomy bibliometric analysis.

Adapted from the figure/table set in Forero-Romero (2024), "Astronomy in
Colombia: a bibliometric perspective" (arXiv:2403.02255), using ADS citation
counts (data/raw/export-custom*.txt) matched onto the tagged bibliographic
export -- see build_dataset.py. The paper's cross-country figures (global
publication rankings, highly-cited-articles-vs-total-publications by nation)
need bibliometric data for every other country, which is out of scope here.

Usage:
    python src/plots.py
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

from name_matching import build_canonical_name_map

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
FIG_DIR = ROOT / "output" / "figures"
TABLE_DIR = ROOT / "output" / "tables"
CURRENT_YEAR = date.today().year

plt.rcParams.update(
    {
        "figure.dpi": 150,
        "savefig.dpi": 150,
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    pubs = pd.read_csv(PROCESSED / "publications.csv")
    authors = pd.read_csv(PROCESSED / "authorships.csv")

    # Merge ADS name-string variants ("Forero-Romero, J. E." / "Forero-Romero,
    # Jaime E.") that refer to the same person -- see name_matching.py. Only
    # done among Colombian-affiliated authorships, since that's the subset
    # used for author-level rankings and the co-authorship network.
    colombian_names = authors.loc[authors["is_colombian"], "author"].tolist()
    canonical_map = build_canonical_name_map(colombian_names)
    authors["author_canonical"] = authors["author"].map(lambda n: canonical_map.get(n, n))

    return pubs, authors


def h_index(citation_counts) -> int:
    counts = sorted(citation_counts, reverse=True)
    h = 0
    for rank, c in enumerate(counts, start=1):
        if c >= rank:
            h = rank
        else:
            break
    return h


def _strip_markup(text: str) -> str:
    import re

    return re.sub(r"<[^>]+>", "", str(text))


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------


def fig_cumulative_and_annual(pubs: pd.DataFrame) -> None:
    by_year = pubs.groupby("year").size().sort_index()
    years = by_year.index.to_numpy()
    counts = by_year.to_numpy()
    cumulative = np.cumsum(counts)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

    ax1.plot(years, cumulative, marker="o", ms=3, color="#1f5aa6")
    ax1.set_yscale("log")
    ax1.set_xlabel("Year")
    ax1.set_ylabel("Cumulative publications (log scale)")
    ax1.set_title("Cumulative publication trajectory")

    ax2.bar(years, counts, color="#1f5aa6", width=0.8)
    ax2.set_yscale("log")
    ax2.set_xlabel("Year")
    ax2.set_ylabel("Publications (log scale)")
    ax2.set_title("Publications per year")

    fig.suptitle("Colombian-affiliated astronomy publications in ADS", y=1.02)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig1_publications_over_time.png", bbox_inches="tight")
    plt.close(fig)


def fig_avg_authors_per_year(pubs: pd.DataFrame) -> None:
    stats = pubs.groupby("year")["n_authors"].agg(["mean", "median", "count"])
    stats = stats[stats["count"] >= 1]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(stats.index, stats["mean"], marker="o", ms=3, label="Mean", color="#1f5aa6")
    ax.plot(stats.index, stats["median"], marker="s", ms=3, label="Median", color="#c0392b")
    ax.set_xlabel("Year")
    ax.set_ylabel("Authors per publication")
    ax.set_title("Average authorship size per year")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig2_avg_authors_per_year.png", bbox_inches="tight")
    plt.close(fig)


def fig_authors_distribution(pubs: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    max_authors = pubs["n_authors"].max()
    bins = np.logspace(0, np.log10(max_authors + 1), 30)
    ax.hist(pubs["n_authors"], bins=bins, color="#1f5aa6", edgecolor="white")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Authors per publication (log scale)")
    ax.set_ylabel("Number of publications (log scale)")
    ax.set_title("Distribution of authorship size")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig3_authors_distribution.png", bbox_inches="tight")
    plt.close(fig)


def fig_citations_per_year(pubs: pd.DataFrame) -> None:
    stats = pubs.dropna(subset=["num_citations"]).groupby("year")["num_citations"].agg(
        ["sum", "mean", "count"]
    )

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

    ax1.bar(stats.index, stats["sum"], color="#1f5aa6", width=0.8)
    ax1.set_yscale("log")
    ax1.set_xlabel("Publication year")
    ax1.set_ylabel("Total citations (log scale)")
    ax1.set_title("Total citations by publication year")

    ax2.plot(stats.index, stats["mean"], marker="o", ms=3, color="#c0392b")
    ax2.set_xlabel("Publication year")
    ax2.set_ylabel("Mean citations per publication")
    ax2.set_title("Mean citations per publication, by year")

    fig.suptitle(
        f"Citations accumulated as of {CURRENT_YEAR}: older papers have had more time to be cited",
        y=1.02,
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig9_citations_per_year.png", bbox_inches="tight")
    plt.close(fig)


def fig_citations_vs_authors(pubs: pd.DataFrame) -> float:
    df = pubs.dropna(subset=["num_citations", "n_authors", "year"]).copy()
    df["years_since_pub"] = (CURRENT_YEAR - df["year"] + 1).clip(lower=1)
    df["citation_rate"] = df["num_citations"] / df["years_since_pub"]

    log_authors = np.log10(df["n_authors"])
    log_rate = np.log10(df["citation_rate"] + 0.1)
    pearson_r = float(np.corrcoef(log_authors, log_rate)[0, 1])

    fig = plt.figure(figsize=(7, 7))
    grid = fig.add_gridspec(4, 4, hspace=0.05, wspace=0.05)
    ax = fig.add_subplot(grid[1:4, 0:3])
    ax_top = fig.add_subplot(grid[0, 0:3], sharex=ax)
    ax_right = fig.add_subplot(grid[1:4, 3], sharey=ax)

    ax.scatter(df["n_authors"], df["citation_rate"], s=15, alpha=0.5, color="#1f5aa6")
    ax.set_xscale("log")
    ax.set_yscale("symlog", linthresh=1)
    ax.set_xlabel("Authors per publication (log scale)")
    ax.set_ylabel("Citations per year since publication")

    ax_top.hist(df["n_authors"], bins=np.logspace(0, np.log10(df["n_authors"].max() + 1), 25),
                color="#1f5aa6", alpha=0.7)
    ax_top.set_xscale("log")
    ax_top.tick_params(labelbottom=False)
    ax_top.set_yticks([])

    ax_right.hist(
        df["citation_rate"],
        bins=np.logspace(-1, np.log10(df["citation_rate"].max() + 1), 25),
        orientation="horizontal",
        color="#1f5aa6",
        alpha=0.7,
    )
    ax_right.set_yscale("symlog", linthresh=1)
    ax_right.tick_params(labelleft=False)
    ax_right.set_xticks([])

    ax_top.set_title(f"Citation rate vs. collaboration size (Pearson r = {pearson_r:.2f}, log–log)")
    fig.savefig(FIG_DIR / "fig10_citations_vs_authors.png", bbox_inches="tight")
    plt.close(fig)
    return pearson_r


def _plot_institution_ranking(table: pd.DataFrame, path: Path, title: str, color: str) -> None:
    """Horizontal bars of h-index in ranking order (h, then pubs, then citations).

    The bar length is the h-index because that is the primary sort key; the
    publication count is annotated on each bar so the second key stays visible.
    """
    fig, ax = plt.subplots(figsize=(8, 7))
    rows = table[::-1]
    ax.barh(rows["Institution"], rows["h_index"], color=color)
    for y, (h, n) in enumerate(zip(rows["h_index"], rows["n_publications"])):
        ax.text(h + 0.4, y, f"{n} pubs.", va="center", fontsize=8, color="#555555")
    ax.set_xlim(0, table["h_index"].max() * 1.18)
    ax.set_xlabel("h-index")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def fig_top_institutions(authors: pd.DataFrame, pubs: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    table = _institution_stats(authors, pubs, top_n)
    _plot_institution_ranking(
        table,
        FIG_DIR / "fig4_top_institutions.png",
        f"Top {top_n} Colombian institutions by h-index",
        "#1f5aa6",
    )
    return table


def fig_top_authors(authors: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    # Restrict to authors with a Colombian affiliation, otherwise this is
    # dominated by non-Colombian members of huge international collaborations
    # (DESI, LIGO/Virgo/KAGRA) that a Colombian-affiliated author also belongs to.
    colombian = authors[authors["is_colombian"]]
    counts = (
        colombian.groupby("author_canonical")["bibcode"]
        .nunique()
        .sort_values(ascending=False)
    )
    top = counts.head(top_n)

    fig, ax = plt.subplots(figsize=(8, 7))
    ax.barh(top.index[::-1], top.to_numpy()[::-1], color="#1f5aa6")
    ax.set_xlabel("Publications")
    ax.set_title(f"Top {top_n} authors by publication count (Colombian-affiliated)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig5_top_authors.png", bbox_inches="tight")
    plt.close(fig)
    return counts


def fig_top_journals(pubs: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    counts = pubs["journal"].value_counts().head(top_n)

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(counts.index[::-1], counts.to_numpy()[::-1], color="#1f5aa6")
    ax.set_xlabel("Publications")
    ax.set_title(f"Top {top_n} journals")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig6_top_journals.png", bbox_inches="tight")
    plt.close(fig)
    return counts


def fig_top_keywords(pubs: pd.DataFrame, top_n: int = 25) -> pd.DataFrame:
    all_kw = (
        pubs["keywords"]
        .dropna()
        .str.split(";")
        .explode()
        .str.strip()
        .str.lower()
    )
    # Drop bare numeric tokens: some records list AAS Unified Astronomy
    # Thesaurus concept IDs (e.g. "1378") alongside the text keywords.
    all_kw = all_kw[(all_kw != "") & ~all_kw.str.fullmatch(r"\d+")]
    counts = all_kw.value_counts().head(top_n)

    fig, ax = plt.subplots(figsize=(9, 8))
    ax.barh(counts.index[::-1], counts.to_numpy()[::-1], color="#1f5aa6")
    ax.set_xlabel("Occurrences")
    ax.set_title(f"Top {top_n} keywords")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig7_top_keywords.png", bbox_inches="tight")
    plt.close(fig)
    return counts


def fig_coauthorship_network(authors: pd.DataFrame, min_pubs: int = 5) -> None:
    """Co-authorship network among prolific, Colombian-affiliated authors."""
    colombian = authors[authors["is_colombian"]]
    pub_counts = colombian.groupby("author_canonical")["bibcode"].nunique()
    core_authors = set(pub_counts[pub_counts >= min_pubs].index)
    if len(core_authors) < 2:
        return

    g = nx.Graph()
    for author, n in pub_counts[pub_counts >= min_pubs].items():
        g.add_node(author, n_pubs=int(n))

    subset = colombian[colombian["author_canonical"].isin(core_authors)]
    for _, group in subset.groupby("bibcode"):
        coauthors = list(dict.fromkeys(group["author_canonical"]))
        for i in range(len(coauthors)):
            for j in range(i + 1, len(coauthors)):
                a, b = coauthors[i], coauthors[j]
                if g.has_edge(a, b):
                    g[a][b]["weight"] += 1
                else:
                    g.add_edge(a, b, weight=1)

    if g.number_of_edges() == 0:
        return

    fig, ax = plt.subplots(figsize=(10, 10))
    pos = nx.spring_layout(g, seed=42, k=0.6)
    sizes = [80 + 20 * g.nodes[n]["n_pubs"] for n in g.nodes]
    weights = [g[u][v]["weight"] for u, v in g.edges]
    nx.draw_networkx_edges(g, pos, ax=ax, alpha=0.3, width=[0.4 * w for w in weights])
    nx.draw_networkx_nodes(g, pos, ax=ax, node_size=sizes, node_color="#1f5aa6", alpha=0.85)
    labels = {n: n.split(",")[0] for n in g.nodes}
    nx.draw_networkx_labels(g, pos, labels=labels, ax=ax, font_size=7)
    ax.set_title(
        f"Co-authorship network: Colombian-affiliated authors with ≥{min_pubs} publications"
    )
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig8_coauthorship_network.png", bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


# Institution rankings are ordered by h-index first, since it is the least
# gameable of the three by a single large-collaboration paper, with publication
# count and then total citations as tie-breakers. Table columns follow the same
# order so the ranking key is readable left to right.
INSTITUTION_RANK_KEYS = ["h_index", "n_publications", "total_citations"]


def _institution_stats(authors: pd.DataFrame, pubs: pd.DataFrame, top_n: int) -> pd.DataFrame:
    """Per-institution stats, ranked by h-index, then publications, then citations."""
    colombian = authors[
        authors["is_colombian"] & (authors["institution"] != "Other Colombian institution")
    ]
    grouped = colombian.groupby("institution").agg(
        n_publications=("bibcode", "nunique"),
        n_unique_authors=("author_canonical", "nunique"),
    )
    merged = colombian.merge(pubs[["bibcode", "year", "num_citations"]], on="bibcode")
    years = merged.groupby("institution")["year"].agg(first_year="min", last_year="max")

    # One row per (institution, bibcode) so a paper with several co-authors at
    # the same institution doesn't have its citations counted more than once.
    per_pub = merged.drop_duplicates(["institution", "bibcode"])
    citation_stats = per_pub.groupby("institution")["num_citations"].agg(
        total_citations="sum", h_index=h_index
    )
    citation_stats["total_citations"] = citation_stats["total_citations"].astype(int)

    table = (
        grouped.join(years)
        .join(citation_stats)
        .sort_values(INSTITUTION_RANK_KEYS, ascending=False)
        .head(top_n)
        .reset_index()
        .rename(columns={"institution": "Institution"})
    )
    return table[
        ["Institution", *INSTITUTION_RANK_KEYS, "n_unique_authors", "first_year", "last_year"]
    ]


def table_institutions(authors: pd.DataFrame, pubs: pd.DataFrame, top_n: int = 25) -> pd.DataFrame:
    table = _institution_stats(authors, pubs, top_n)
    table.to_csv(TABLE_DIR / "table1_institutions.csv", index=False)
    _write_markdown(table, TABLE_DIR / "table1_institutions.md", "Top Colombian institutions")
    return table


COLOMBIA_LED_MIN_SHARE = 0.10


def colombia_led(pubs: pd.DataFrame, min_share: float = COLOMBIA_LED_MIN_SHARE) -> pd.DataFrame:
    """Publications where Colombians are at least `min_share` of the author list.

    Table 1 conflates two different things: work led from Colombia, and
    membership in a large international collaboration. A single Colombian
    coauthor on a 3,000-author DESI paper adds a publication and its full
    citation count to their institution's row, exactly like a three-author paper
    written entirely in Bogota.

    Filtering on the Colombian *share* of the author list separates them, and is
    preferable to a cap on author count: it is dimensionless, so it does not go
    stale as collaborations keep growing, and it keeps genuinely
    Colombia-heavy large papers that a size cut would throw away (e.g. the 2020
    Arrokoth stellar-occultation paper, 133 authors of whom 15 are Colombian).

    A size cut has no natural threshold to pick anyway: the author-count
    histogram's only visible gap is at 80-100 authors, which separates large
    consortium papers from enormous ones rather than isolating Colombia-led
    work. The 31-80 band is almost entirely DESI technical papers carrying a
    single Colombian coauthor (mean Colombian share 2%).
    """
    share = pubs["n_colombian_authors"] / pubs["n_authors"]
    return pubs[share >= min_share]


def table_institutions_colombia_led(
    authors: pd.DataFrame, pubs: pd.DataFrame, top_n: int = 25
) -> pd.DataFrame:
    """Table 1's ranking over Colombia-led publications only."""
    led = colombia_led(pubs)
    led_authors = authors[authors["bibcode"].isin(set(led["bibcode"]))]
    table = _institution_stats(led_authors, led, top_n)
    table.to_csv(TABLE_DIR / "table5_institutions_colombia_led.csv", index=False)
    _write_markdown(
        table,
        TABLE_DIR / "table5_institutions_colombia_led.md",
        f"Top Colombian institutions, publications >= "
        f"{COLOMBIA_LED_MIN_SHARE:.0%} Colombian-authored",
    )
    return table


def fig_top_institutions_colombia_led(
    authors: pd.DataFrame, pubs: pd.DataFrame, top_n: int = 20
) -> pd.DataFrame:
    """Fig. 4's ranking over Colombia-led publications only."""
    led = colombia_led(pubs)
    led_authors = authors[authors["bibcode"].isin(set(led["bibcode"]))]
    table = _institution_stats(led_authors, led, top_n)
    _plot_institution_ranking(
        table,
        FIG_DIR / "fig11_top_institutions_colombia_led.png",
        f"Top {top_n} Colombian institutions by h-index, papers "
        f"\u2265{COLOMBIA_LED_MIN_SHARE:.0%} Colombian-authored",
        "#a6541f",
    )
    return table


def _top_cited(pubs: pd.DataFrame, authors: pd.DataFrame, top_n: int) -> pd.DataFrame:
    colombian = authors[
        authors["is_colombian"] & (authors["institution"] != "Other Colombian institution")
    ]
    inst_map = colombian.groupby("bibcode")["institution"].agg(
        lambda s: "; ".join(sorted(set(s)))
    )

    top = pubs.sort_values("num_citations", ascending=False).head(top_n).copy()
    top["title"] = top["title"].map(_strip_markup)
    top["colombian_institutions"] = top["bibcode"].map(inst_map).fillna("")
    cols = [
        "bibcode",
        "title",
        "year",
        "journal",
        "num_citations",
        "n_authors",
        "colombian_institutions",
    ]
    return top[cols]


def table_top_cited(pubs: pd.DataFrame, authors: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    table = _top_cited(pubs, authors, top_n)
    table.to_csv(TABLE_DIR / "table4_top_cited.csv", index=False)
    _write_markdown(table, TABLE_DIR / "table4_top_cited.md", "Top 10 most-cited articles")
    return table


def table_top_citation_rate(
    pubs: pd.DataFrame, authors: pd.DataFrame, top_n: int = 10
) -> pd.DataFrame:
    """Most-cited-per-year articles.

    Table 4 ranks on raw citation totals, which favours older papers simply
    because they have had longer to accumulate. Dividing by the paper's age is
    a crude age control (see the caveat on Fig. 10: it is a snapshot divided by
    years, not an observed citation-rate curve), but it surfaces recent work
    that the raw ranking buries.
    """
    df = pubs.dropna(subset=["num_citations", "year"]).copy()
    years_since_pub = (CURRENT_YEAR - df["year"] + 1).clip(lower=1)
    df["citations_per_year"] = (df["num_citations"] / years_since_pub).round(1)

    top = df.sort_values("citations_per_year", ascending=False).head(top_n)
    table = _top_cited(top, authors, top_n).merge(
        df[["bibcode", "citations_per_year"]], on="bibcode"
    )
    # Put the ranking key next to the citation total it is derived from.
    cols = table.columns.tolist()
    cols.insert(cols.index("num_citations") + 1, cols.pop(cols.index("citations_per_year")))
    table = table[cols].sort_values("citations_per_year", ascending=False)
    table.to_csv(TABLE_DIR / "table7_top_citation_rate.csv", index=False)
    _write_markdown(
        table, TABLE_DIR / "table7_top_citation_rate.md", "Top 10 articles by citations per year"
    )
    return table


def table_top_cited_colombia_led(
    pubs: pd.DataFrame, authors: pd.DataFrame, top_n: int = 10
) -> pd.DataFrame:
    """Most-cited papers among the Colombia-led ones.

    Table 4 is nine-tenths DESI and LIGO/Virgo/KAGRA; this view shows which
    Colombia-led papers draw the most citations on their own.
    """
    table = _top_cited(colombia_led(pubs), authors, top_n)
    table.to_csv(TABLE_DIR / "table6_top_cited_colombia_led.csv", index=False)
    _write_markdown(
        table,
        TABLE_DIR / "table6_top_cited_colombia_led.md",
        f"Top {top_n} most-cited articles, publications >= "
        f"{COLOMBIA_LED_MIN_SHARE:.0%} Colombian-authored",
    )
    return table


def table_top_authors(authors: pd.DataFrame, pubs: pd.DataFrame, top_n: int = 25) -> pd.DataFrame:
    # Restrict to authors with a Colombian affiliation -- see fig_top_authors.
    colombian = authors[authors["is_colombian"]]
    merged = colombian.merge(pubs[["bibcode", "year", "num_citations"]], on="bibcode")

    grouped = merged.groupby("author_canonical").agg(
        n_publications=("bibcode", "nunique"),
        first_year=("year", "min"),
        last_year=("year", "max"),
    )
    # Total citations, counted once per unique publication per author.
    per_pub = merged.drop_duplicates(["author_canonical", "bibcode"])
    total_citations = (
        per_pub.groupby("author_canonical")["num_citations"].sum().rename("total_citations")
    )

    primary_inst = (
        merged[merged["institution"].notna()]
        .groupby("author_canonical")["institution"]
        .agg(lambda s: s.value_counts().idxmax() if len(s) else None)
        .rename("primary_institution")
    )
    table = (
        grouped.join(total_citations)
        .join(primary_inst)
        .sort_values("n_publications", ascending=False)
        .head(top_n)
        .reset_index()
        .rename(columns={"author_canonical": "Author"})
    )
    table["primary_institution"] = table["primary_institution"].fillna("")
    table["total_citations"] = table["total_citations"].fillna(0).astype(int)
    table.to_csv(TABLE_DIR / "table2_top_authors.csv", index=False)
    _write_markdown(
        table,
        TABLE_DIR / "table2_top_authors.md",
        "Top Colombian-affiliated authors by publication count",
    )
    return table


def table_journals(pubs: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    counts = pubs["journal"].value_counts().head(top_n)
    table = counts.rename_axis("Journal").reset_index(name="n_publications")
    table.to_csv(TABLE_DIR / "table3_journals.csv", index=False)
    _write_markdown(table, TABLE_DIR / "table3_journals.md", "Top journals")
    return table


def table_summary(pubs: pd.DataFrame, authors: pd.DataFrame) -> None:
    colombian = authors[authors["is_colombian"]]
    most_cited = pubs.loc[pubs["num_citations"].idxmax()]
    summary = {
        "Total publications": len(pubs),
        "Year range": f"{int(pubs['year'].min())}–{int(pubs['year'].max())}",
        "Total unique authors": authors["author"].nunique(),
        "Unique authors with a Colombian affiliation": colombian["author_canonical"].nunique(),
        "Unique journals": pubs["journal"].nunique(),
        "Unique Colombian institutions identified": colombian.loc[
            colombian["institution"] != "Other Colombian institution", "institution"
        ].nunique(),
        "Mean authors per publication": round(pubs["n_authors"].mean(), 2),
        "Median authors per publication": int(pubs["n_authors"].median()),
        "Total citations": int(pubs["num_citations"].sum()),
        "Overall h-index": h_index(pubs["num_citations"]),
        "Most-cited paper": f"{_strip_markup(most_cited['title'])} "
        f"({int(most_cited['year'])}, {int(most_cited['num_citations'])} citations)",
    }
    lines = ["# Summary statistics", ""]
    for k, v in summary.items():
        lines.append(f"- **{k}:** {v}")
    (TABLE_DIR / "summary_stats.md").write_text("\n".join(lines) + "\n")


def _write_markdown(df: pd.DataFrame, path: Path, title: str) -> None:
    lines = [f"# {title}", ""]
    lines.append("| " + " | ".join(df.columns) + " |")
    lines.append("| " + " | ".join(["---"] * len(df.columns)) + " |")
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(v) for v in row.to_list()) + " |")
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)

    pubs, authors = load_data()

    fig_cumulative_and_annual(pubs)
    fig_avg_authors_per_year(pubs)
    fig_authors_distribution(pubs)
    fig_citations_per_year(pubs)
    fig_citations_vs_authors(pubs)
    fig_top_institutions(authors, pubs)
    fig_top_authors(authors)
    fig_top_journals(pubs)
    fig_top_keywords(pubs)
    fig_coauthorship_network(authors)
    fig_top_institutions_colombia_led(authors, pubs)

    table_institutions(authors, pubs)
    table_institutions_colombia_led(authors, pubs)
    table_top_authors(authors, pubs)
    table_top_cited(pubs, authors)
    table_top_cited_colombia_led(pubs, authors)
    table_top_citation_rate(pubs, authors)
    table_journals(pubs)
    table_summary(pubs, authors)

    print(f"Figures written to {FIG_DIR}")
    print(f"Tables written to {TABLE_DIR}")


if __name__ == "__main__":
    main()
