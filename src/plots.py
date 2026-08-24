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
    ax1.set_xlabel("Year")
    ax1.set_ylabel("Cumulative publications")
    ax1.set_title("Cumulative publication trajectory")

    ax2.bar(years, counts, color="#1f5aa6", width=0.8)
    ax2.set_xlabel("Year")
    ax2.set_ylabel("Publications")
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
        f"Citations accumulated as of {CURRENT_YEAR} — older papers have had more time to be cited",
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


def fig_top_institutions(authors: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    colombian = authors[authors["is_colombian"]]
    counts = (
        colombian[colombian["institution"] != "Other Colombian institution"]
        .groupby("institution")["bibcode"]
        .nunique()
        .sort_values(ascending=False)
    )
    top = counts.head(top_n)

    fig, ax = plt.subplots(figsize=(8, 7))
    ax.barh(top.index[::-1], top.to_numpy()[::-1], color="#1f5aa6")
    ax.set_xlabel("Publications")
    ax.set_title(f"Top {top_n} Colombian institutions by publication count")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig4_top_institutions.png", bbox_inches="tight")
    plt.close(fig)
    return counts


def fig_top_authors(authors: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    # Restrict to authors with a Colombian affiliation, otherwise this is
    # dominated by non-Colombian members of huge international collaborations
    # (DESI, LIGO/Virgo/KAGRA) that a Colombian-affiliated author also belongs to.
    colombian = authors[authors["is_colombian"]]
    counts = colombian.groupby("author")["bibcode"].nunique().sort_values(ascending=False)
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
    pub_counts = colombian.groupby("author")["bibcode"].nunique()
    core_authors = set(pub_counts[pub_counts >= min_pubs].index)
    if len(core_authors) < 2:
        return

    g = nx.Graph()
    for author, n in pub_counts[pub_counts >= min_pubs].items():
        g.add_node(author, n_pubs=int(n))

    subset = colombian[colombian["author"].isin(core_authors)]
    for _, group in subset.groupby("bibcode"):
        coauthors = list(dict.fromkeys(group["author"]))
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
        f"Co-authorship network — Colombian-affiliated authors with ≥{min_pubs} publications"
    )
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig8_coauthorship_network.png", bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


def table_institutions(authors: pd.DataFrame, pubs: pd.DataFrame, top_n: int = 25) -> pd.DataFrame:
    colombian = authors[
        authors["is_colombian"] & (authors["institution"] != "Other Colombian institution")
    ]
    grouped = colombian.groupby("institution").agg(
        n_publications=("bibcode", "nunique"),
        n_unique_authors=("author", "nunique"),
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
        .sort_values("n_publications", ascending=False)
        .head(top_n)
    )
    table = table.reset_index().rename(columns={"institution": "Institution"})
    table.to_csv(TABLE_DIR / "table1_institutions.csv", index=False)
    _write_markdown(table, TABLE_DIR / "table1_institutions.md", "Top Colombian institutions")
    return table


def table_top_cited(pubs: pd.DataFrame, authors: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
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
    table = top[cols]
    table.to_csv(TABLE_DIR / "table4_top_cited.csv", index=False)
    _write_markdown(table, TABLE_DIR / "table4_top_cited.md", "Top 10 most-cited articles")
    return table


def table_top_authors(authors: pd.DataFrame, pubs: pd.DataFrame, top_n: int = 25) -> pd.DataFrame:
    # Restrict to authors with a Colombian affiliation -- see fig_top_authors.
    colombian = authors[authors["is_colombian"]]
    merged = colombian.merge(pubs[["bibcode", "year", "num_citations"]], on="bibcode")

    grouped = merged.groupby("author").agg(
        n_publications=("bibcode", "nunique"),
        first_year=("year", "min"),
        last_year=("year", "max"),
    )
    # Total citations, counted once per unique publication per author.
    per_pub = merged.drop_duplicates(["author", "bibcode"])
    total_citations = per_pub.groupby("author")["num_citations"].sum().rename("total_citations")

    primary_inst = (
        merged[merged["institution"].notna()]
        .groupby("author")["institution"]
        .agg(lambda s: s.value_counts().idxmax() if len(s) else None)
        .rename("primary_institution")
    )
    table = (
        grouped.join(total_citations)
        .join(primary_inst)
        .sort_values("n_publications", ascending=False)
        .head(top_n)
        .reset_index()
        .rename(columns={"author": "Author"})
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
        "Unique authors with a Colombian affiliation": colombian["author"].nunique(),
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
    fig_top_institutions(authors)
    fig_top_authors(authors)
    fig_top_journals(pubs)
    fig_top_keywords(pubs)
    fig_coauthorship_network(authors)

    table_institutions(authors, pubs)
    table_top_authors(authors, pubs)
    table_top_cited(pubs, authors)
    table_journals(pubs)
    table_summary(pubs, authors)

    print(f"Figures written to {FIG_DIR}")
    print(f"Tables written to {TABLE_DIR}")


if __name__ == "__main__":
    main()
