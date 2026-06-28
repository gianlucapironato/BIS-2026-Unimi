from pathlib import Path

import matplotlib.pyplot as plt
import pm4py


BASE_DIR = Path(__file__).resolve().parent
INPUT_XES_PATH = BASE_DIR / "BPI_Challenge_2013_incidents.xes"
OUTPUT_1ST_XES_PATH = BASE_DIR / "log_1st_level.xes"
OUTPUT_2ND_XES_PATH = BASE_DIR / "log_2nd_level.xes"
OUTPUT_3RD_XES_PATH = BASE_DIR / "log_3rd_level.xes"
OUTPUT_CHART_OLD_PATH = BASE_DIR / "escalation_frequency.png"

INPUT_1ST_CLEAN_XES_PATH = BASE_DIR / "log_1st_level_clean.xes"
OUTPUT_CHART_CLEANED_PATH = BASE_DIR / "escalation_frequency_cleaned.png"

ORG_GROUP_COL = "org:group"


def compute_percentages(n_1st: int, n_2nd: int, n_3rd: int) -> dict[str, float]:
    n_total = n_1st + n_2nd + n_3rd
    n_escalated = n_2nd + n_3rd

    p_1st = (n_1st / n_total) * 100 if n_total else 0.0
    p_2nd = (n_2nd / n_total) * 100 if n_total else 0.0
    p_3rd = (n_3rd / n_total) * 100 if n_total else 0.0
    p_escalated = (n_escalated / n_total) * 100 if n_total else 0.0
    p_3rd_among_escalated = (n_3rd / n_escalated) * 100 if n_escalated else 0.0

    return {
        "n_total": n_total,
        "n_escalated": n_escalated,
        "p_1st": p_1st,
        "p_2nd": p_2nd,
        "p_3rd": p_3rd,
        "p_escalated": p_escalated,
        "p_3rd_among_escalated": p_3rd_among_escalated,
    }


def print_stats_block(title: str, n_1st: int, n_2nd: int, n_3rd: int, stats: dict[str, float]) -> None:
    print()
    print(title)
    print("-" * 40)
    print(f"Total traces: {stats['n_total']}")
    print(f"First-line only traces: {n_1st} ({stats['p_1st']:.2f}%)")
    print(f"Second-line traces: {n_2nd} ({stats['p_2nd']:.2f}%)")
    print(f"Third-line traces: {n_3rd} ({stats['p_3rd']:.2f}%)")
    print(f"Escalated traces (2nd and/or 3rd): {stats['n_escalated']} ({stats['p_escalated']:.2f}%)")
    print(f"Third-line share among escalated traces: {stats['p_3rd_among_escalated']:.2f}%")


def plot_escalation_chart(title: str, stats: dict[str, float], output_path: Path) -> None:
    labels = [
        "First-line only",
        "Escalated (2nd and/or 3rd)",
        "Second-line",
        "Third-line",
    ]
    values = [stats["p_1st"], stats["p_escalated"], stats["p_2nd"], stats["p_3rd"]]
    colors = ["#4C78A8", "#F58518", "#54A24B", "#E45756"]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(labels, values, color=colors)
    ax.set_title(title)
    ax.set_ylabel("Percentage of traces (%)")
    ax.set_ylim(0, max(values) * 1.2 if values else 100)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.5,
            f"{value:.2f}%",
            ha="center",
            va="bottom",
        )

    plt.xticks(rotation=10)
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.show()

    print(f"Saved chart: {output_path}")

source_log = pm4py.read_xes(str(INPUT_XES_PATH), return_legacy_log_object=True)

first_level_log = type(source_log)(
    attributes=dict(source_log.attributes),
    extensions=dict(source_log.extensions),
    classifiers=dict(source_log.classifiers),
    omni_present=dict(source_log.omni_present),
    properties=dict(source_log.properties),
)
second_level_log = type(source_log)(
    attributes=dict(source_log.attributes),
    extensions=dict(source_log.extensions),
    classifiers=dict(source_log.classifiers),
    omni_present=dict(source_log.omni_present),
    properties=dict(source_log.properties),
)
third_level_log = type(source_log)(
    attributes=dict(source_log.attributes),
    extensions=dict(source_log.extensions),
    classifiers=dict(source_log.classifiers),
    omni_present=dict(source_log.omni_present),
    properties=dict(source_log.properties),
)

for trace in source_log:
    has_2nd = False
    has_3rd = False

    for event in trace:
        group_value = str(event.get(ORG_GROUP_COL, "")).lower()
        if "3rd" in group_value:
            has_3rd = True
        if "2nd" in group_value:
            has_2nd = True

    if has_3rd:
        third_level_log.append(trace)
    elif has_2nd:
        second_level_log.append(trace)
    else:
        first_level_log.append(trace)

pm4py.write_xes(first_level_log, str(OUTPUT_1ST_XES_PATH))
pm4py.write_xes(second_level_log, str(OUTPUT_2ND_XES_PATH))
pm4py.write_xes(third_level_log, str(OUTPUT_3RD_XES_PATH))

print(f"Created: {OUTPUT_1ST_XES_PATH}")
print(f"Created: {OUTPUT_2ND_XES_PATH}")
print(f"Created: {OUTPUT_3RD_XES_PATH}")

n_1st_old = len(first_level_log)
n_2nd_old = len(second_level_log)
n_3rd_old = len(third_level_log)
stats_old = compute_percentages(n_1st_old, n_2nd_old, n_3rd_old)

print_stats_block("Escalation frequency statistics (original segments)", n_1st_old, n_2nd_old, n_3rd_old, stats_old)
plot_escalation_chart("Incident escalation frequencies", stats_old, OUTPUT_CHART_OLD_PATH)


if not INPUT_1ST_CLEAN_XES_PATH.exists():
    print()
    print(f"Cleaned first-level log not found: {INPUT_1ST_CLEAN_XES_PATH}")
    print("Run cleaning.py first, then re-run this script to compute cleaned escalation frequencies.")
else:
    cleaned_first_level_log = pm4py.read_xes(str(INPUT_1ST_CLEAN_XES_PATH), return_legacy_log_object=True)
    second_level_log = pm4py.read_xes(str(OUTPUT_2ND_XES_PATH), return_legacy_log_object=True)
    third_level_log = pm4py.read_xes(str(OUTPUT_3RD_XES_PATH), return_legacy_log_object=True)

    print()
    print(f"Input: {INPUT_1ST_CLEAN_XES_PATH}")
    print(f"Input: {OUTPUT_2ND_XES_PATH}")
    print(f"Input: {OUTPUT_3RD_XES_PATH}")

    n_1st_clean = len(cleaned_first_level_log)
    n_2nd_clean = len(second_level_log)
    n_3rd_clean = len(third_level_log)
    stats_clean = compute_percentages(n_1st_clean, n_2nd_clean, n_3rd_clean)

    print_stats_block(
        "Escalation frequency statistics (using cleaned level-1 segment)",
        n_1st_clean,
        n_2nd_clean,
        n_3rd_clean,
        stats_clean,
    )
    plot_escalation_chart(
        "Incident escalation frequencies (using cleaned level-1 segment)",
        stats_clean,
        OUTPUT_CHART_CLEANED_PATH,
    )

