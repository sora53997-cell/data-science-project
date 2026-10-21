"""Analyze seasonal tourist mobility networks and produce portfolio visuals."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


SEASONS = ["Spring", "Summer", "Autumn", "Winter"]
COLORS = {
    "Spring": "#2A9D8F",
    "Summer": "#E9C46A",
    "Autumn": "#E76F51",
    "Winter": "#457B9D",
}


def read_data(data_dir: Path) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    edges: dict[str, pd.DataFrame] = {}
    nodes: list[pd.DataFrame] = []

    for season in SEASONS:
        edge_path = data_dir / f"Edges_Travels_in_{season}.csv"
        node_path = data_dir / f"Nodes_Travels_in_{season}.csv"
        if not edge_path.exists():
            raise FileNotFoundError(f"Missing required file: {edge_path}")

        frame = pd.read_csv(edge_path)
        expected_edge_columns = {"Source", "Target", "Weight"}
        if set(frame.columns) != expected_edge_columns:
            raise ValueError(f"Unexpected columns in {edge_path.name}: {list(frame.columns)}")
        edges[season] = frame

        if node_path.exists():
            nodes.append(pd.read_csv(node_path))

    if not nodes:
        raise FileNotFoundError("No seasonal node files were found.")

    node_frame = pd.concat(nodes, ignore_index=True).drop_duplicates("ID")
    return edges, node_frame


def weighted_flow(edges: pd.DataFrame) -> pd.Series:
    outgoing = edges[["Source", "Weight"]].rename(columns={"Source": "ID"})
    incoming = edges[["Target", "Weight"]].rename(columns={"Target": "ID"})
    return (
        pd.concat([outgoing, incoming], ignore_index=True)
        .groupby("ID")["Weight"]
        .sum()
        .sort_values(ascending=False)
    )


def build_outputs(
    edges_by_season: dict[str, pd.DataFrame], nodes: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    season_rows = []
    seasonal_scores = []

    for season in SEASONS:
        edges = edges_by_season[season]
        scores = weighted_flow(edges)
        used_nodes = set(edges["Source"]) | set(edges["Target"])
        season_rows.append(
            {
                "Season": season,
                "ActiveAttractions": len(used_nodes),
                "ObservedRoutes": len(edges),
                "RecordedTransitions": int(edges["Weight"].sum()),
                "MeanRouteWeight": edges["Weight"].mean(),
                "Top10FlowShare": scores.head(10).sum() / scores.sum(),
                "Top100FlowShare": scores.head(100).sum() / scores.sum(),
            }
        )
        seasonal_scores.append(scores.rename(season))

    season_summary = pd.DataFrame(season_rows)
    score_by_season = pd.concat(seasonal_scores, axis=1).fillna(0).astype(int)

    all_edges = (
        pd.concat(edges_by_season.values(), ignore_index=True)
        .groupby(["Source", "Target"], as_index=False)["Weight"]
        .sum()
    )
    scores = weighted_flow(all_edges).rename("WeightedFlow").reset_index()
    top_attractions = scores.merge(nodes, on="ID", how="left")
    for season in SEASONS:
        top_attractions[season] = top_attractions["ID"].map(score_by_season[season]).fillna(0).astype(int)

    mapped_scores = scores.merge(nodes[["ID", "City_EN"]], on="ID", how="left")
    top_cities = (
        mapped_scores.dropna(subset=["City_EN"])
        .groupby("City_EN", as_index=False)["WeightedFlow"]
        .sum()
        .sort_values("WeightedFlow", ascending=False)
    )
    return season_summary, top_attractions, top_cities, all_edges


def save_top_attractions_chart(top_attractions: pd.DataFrame, figure_dir: Path) -> None:
    chart = top_attractions.dropna(subset=["Name_EN"]).head(15).sort_values("WeightedFlow")
    colors = ["#264653"] * len(chart)
    colors[-1] = "#D1495B"

    fig, ax = plt.subplots(figsize=(11, 7.5))
    bars = ax.barh(chart["Name_EN"], chart["WeightedFlow"], color=colors)
    ax.bar_label(bars, fmt="{:,.0f}", padding=5, fontsize=9)
    ax.set_xlabel("Weighted flow (incoming + outgoing recorded transitions)")
    ax.set_ylabel("")
    ax.set_xlim(0, chart["WeightedFlow"].max() * 1.15)
    ax.grid(axis="x", alpha=0.22)
    fig.suptitle(
        "Tourist Mobility Is Concentrated Around a Few Landmark Hubs",
        x=0.12,
        y=0.985,
        ha="left",
        fontsize=17,
        fontweight="bold",
    )
    fig.text(
        0.12,
        0.945,
        "Top 15 attractions in the reconstructed full network",
        color="#555555",
        fontsize=11,
    )
    sns.despine(ax=ax)
    fig.tight_layout(rect=(0, 0, 1, 0.91))
    fig.savefig(figure_dir / "top_attractions.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def save_season_chart(season_summary: pd.DataFrame, figure_dir: Path) -> None:
    colors = [COLORS[season] for season in season_summary["Season"]]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))

    bars = axes[0].bar(
        season_summary["Season"], season_summary["RecordedTransitions"], color=colors
    )
    axes[0].bar_label(bars, labels=[f"{value / 1000:.1f}k" for value in season_summary["RecordedTransitions"]], padding=4)
    axes[0].set_title("Recorded transitions")
    axes[0].set_ylabel("Number of attraction-to-attraction movements")
    axes[0].grid(axis="y", alpha=0.22)

    bars = axes[1].bar(
        season_summary["Season"],
        season_summary["Top100FlowShare"] * 100,
        color=colors,
    )
    axes[1].bar_label(
        bars,
        labels=[f"{value:.1f}%" for value in season_summary["Top100FlowShare"] * 100],
        padding=4,
    )
    axes[1].set_title("Share captured by the top 100 attractions")
    axes[1].set_ylabel("Share of total weighted flow (%)")
    axes[1].set_ylim(0, season_summary["Top100FlowShare"].max() * 120)
    axes[1].grid(axis="y", alpha=0.22)

    for ax in axes:
        sns.despine(ax=ax)
    fig.suptitle("Season Changes Both Network Activity and Concentration", x=0.06, ha="left", fontsize=17, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(figure_dir / "seasonal_network_summary.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def save_core_map(top_attractions: pd.DataFrame, figure_dir: Path) -> None:
    mapped = top_attractions.dropna(
        subset=["Name_EN", "Longitude_GCJ02", "Latitude_GCJ02"]
    ).head(180).copy()
    label_data = mapped.drop_duplicates("City_EN").head(10)
    sizes = 18 + 380 * np.sqrt(mapped["WeightedFlow"] / mapped["WeightedFlow"].max())

    fig, ax = plt.subplots(figsize=(11.5, 7.5))
    scatter = ax.scatter(
        mapped["Longitude_GCJ02"],
        mapped["Latitude_GCJ02"],
        s=sizes,
        c=mapped["WeightedFlow"],
        cmap="YlOrRd",
        alpha=0.72,
        edgecolor="white",
        linewidth=0.6,
    )
    for index, (_, row) in enumerate(label_data.iterrows()):
        horizontal = 8 if index % 2 == 0 else -8
        alignment = "left" if horizontal > 0 else "right"
        ax.annotate(
            row["Name_EN"],
            (row["Longitude_GCJ02"], row["Latitude_GCJ02"]),
            xytext=(horizontal, 8 + (index % 3) * 6),
            textcoords="offset points",
            fontsize=8,
            color="#23303B",
            ha=alignment,
            arrowprops={"arrowstyle": "-", "color": "#78838C", "lw": 0.6},
        )

    ax.set_xlim(73, 135)
    ax.set_ylim(17, 54)
    ax.set_xlabel("Longitude (GCJ-02)")
    ax.set_ylabel("Latitude (GCJ-02)")
    fig.suptitle(
        "Core Tourist Attractions Span China but Form Regional Clusters",
        x=0.10,
        y=0.985,
        ha="left",
        fontsize=17,
        fontweight="bold",
    )
    fig.text(
        0.10,
        0.945,
        "Top 180 attractions by weighted flow; bubble size and color represent flow",
        color="#555555",
        fontsize=11,
    )
    ax.grid(alpha=0.18)
    colorbar = fig.colorbar(scatter, ax=ax, pad=0.02)
    colorbar.set_label("Weighted flow")
    sns.despine(ax=ax)
    fig.tight_layout(rect=(0, 0, 1, 0.91))
    fig.savefig(figure_dir / "core_attractions_map.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def write_findings(
    season_summary: pd.DataFrame,
    top_attractions: pd.DataFrame,
    all_edges: pd.DataFrame,
    output_dir: Path,
) -> None:
    top = top_attractions.dropna(subset=["Name_EN"]).iloc[0]
    summer = season_summary.set_index("Season").loc["Summer"]
    winter = season_summary.set_index("Season").loc["Winter"]
    activity_difference = summer["RecordedTransitions"] / winter["RecordedTransitions"] - 1
    all_scores = weighted_flow(all_edges)
    top_100_share = all_scores.head(100).sum() / all_scores.sum()

    text = f"""# Key Findings

1. **Summer was the busiest season.** The network recorded {summer['RecordedTransitions']:,.0f} attraction-to-attraction transitions in summer, {activity_difference:.1%} more than winter ({winter['RecordedTransitions']:,.0f}).
2. **Winter mobility was more concentrated.** The top 100 attractions captured {winter['Top100FlowShare']:.1%} of winter weighted flow, compared with {season_summary['Top100FlowShare'].min():.1%} in the least concentrated season.
3. **{top['Name_EN']} was the strongest hub.** It recorded a reconstructed annual weighted flow of {top['WeightedFlow']:,.0f}, ahead of {top_attractions.dropna(subset=['Name_EN']).iloc[1]['Name_EN']}.
4. **A small group of destinations shaped a large share of observed movement.** The top 100 attractions accounted for {top_100_share:.1%} of full-network weighted flow.

These are descriptive patterns in travel-blog data, not population estimates. The source overrepresents people who publish travel blogs and popular destinations.
"""
    (output_dir / "key_findings.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    project_root = Path(__file__).resolve().parents[1]
    parser.add_argument("--data-dir", type=Path, default=project_root / "data" / "raw")
    parser.add_argument("--output-dir", type=Path, default=project_root / "results")
    parser.add_argument("--figure-dir", type=Path, default=project_root / "figures")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.figure_dir.mkdir(parents=True, exist_ok=True)

    sns.set_theme(style="whitegrid", context="notebook")
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.titleweight": "bold",
            "axes.titlesize": 16,
            "axes.labelsize": 10,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )

    edges_by_season, nodes = read_data(args.data_dir)
    season_summary, top_attractions, top_cities, all_edges = build_outputs(
        edges_by_season, nodes
    )

    season_summary.to_csv(args.output_dir / "season_summary.csv", index=False)
    top_attractions.head(250).to_csv(args.output_dir / "top_attractions.csv", index=False)
    top_cities.head(100).to_csv(args.output_dir / "top_cities.csv", index=False)
    save_top_attractions_chart(top_attractions, args.figure_dir)
    save_season_chart(season_summary, args.figure_dir)
    save_core_map(top_attractions, args.figure_dir)
    write_findings(season_summary, top_attractions, all_edges, args.output_dir)
    print(f"Analysis complete. Results: {args.output_dir}")
    print(f"Figures: {args.figure_dir}")


if __name__ == "__main__":
    main()
