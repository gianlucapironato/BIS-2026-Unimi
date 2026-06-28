from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import pm4py


ORG_GROUP_COL = "org:group"
TIMESTAMP_COL = "time:timestamp"

BASE_DIR = Path(__file__).resolve().parent

SEGMENT_INPUTS = {
    "segment_1st_clean": BASE_DIR / "log_1st_level_clean.xes",
    "segment_2nd": BASE_DIR / "log_2nd_level.xes",
    "segment_3rd": BASE_DIR / "log_3rd_level.xes",
}

def analyze_ping_pong_dates(log):
    """
    Detect A -> B -> A ping-pong handover patterns and collect:
    - frequency per date of the year (B -> A handover timestamp).
    """
    date_counts = defaultdict(int)

    for trace in log:
        handovers = []
        current_group = None

        for event in trace:
            group = event.get(ORG_GROUP_COL)
            timestamp = event.get(TIMESTAMP_COL)

            if group and timestamp and group != current_group:
                handovers.append({"group": group, "time": timestamp})
                current_group = group

        for i in range(len(handovers) - 2):
            team_a1 = handovers[i]["group"]
            team_b = handovers[i + 1]["group"]
            team_a2 = handovers[i + 2]["group"]

            if team_a1 == team_a2 and team_a1 != team_b:
                time_b = handovers[i + 1]["time"]
                time_a2 = handovers[i + 2]["time"]

                if time_b.date() == time_a2.date():
                    date_key = time_a2.date().isoformat()
                    date_counts[date_key] += 1

    return date_counts


def plot_yearly_distribution(date_counts, figure_title: str, ylabel: str, output_png_path: Path):
    sorted_dates = sorted(date_counts.keys())
    values = [date_counts[d] for d in sorted_dates]

    fig_width = max(10, min(28, len(sorted_dates) * 0.35))
    fig, ax = plt.subplots(figsize=(fig_width, 6))

    if not sorted_dates:
        ax.text(0.5, 0.5, "No ping-pongs found", ha="center", va="center")
        ax.set_xticks([])
    else:
        bars = ax.bar(sorted_dates, values, color="#E45756", edgecolor="black")
        
        max_value = max(values) if values else 0
        offset = max_value * 0.01 if max_value > 0 else 0.01
        
        for idx, bar in enumerate(bars):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + offset,
                f"{values[idx]}",
                ha="center",
                va="bottom",
                fontsize=8,
                fontweight="bold",
            )

        ax.set_xticks(range(len(sorted_dates)))
        ax.set_xticklabels(sorted_dates, rotation=70, ha="right", fontsize=9)
        
    ax.set_title(figure_title, fontsize=14, pad=15)
    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.grid(axis="y", linestyle="--", alpha=0.35)

    plt.tight_layout()
    
    output_png_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_png_path, dpi=220)
    plt.close(fig)


def main():
    overall_date_counts = defaultdict(int)

    for segment_name, input_xes_path in SEGMENT_INPUTS.items():
        if not input_xes_path.exists():
            print(f"Skipped {segment_name}: file not found -> {input_xes_path}")
            continue

        log = pm4py.read_xes(str(input_xes_path), return_legacy_log_object=True)
        date_counts = analyze_ping_pong_dates(log)
        
        for date_key, count in date_counts.items():
            overall_date_counts[date_key] += count

        print(f"Processed segment: {segment_name}")

    output_png_path = BASE_DIR / "pingpong_yearly_distribution.png"

    plot_yearly_distribution(
        date_counts=overall_date_counts,
        figure_title="Same-day ping-pongs over time",
        ylabel="Daily ping-pongs",
        output_png_path=output_png_path,
    )

    print(f"Yearly distribution chart saved to: {output_png_path}")


if __name__ == "__main__":
    main()
