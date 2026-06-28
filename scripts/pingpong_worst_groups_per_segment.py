from __future__ import annotations

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

SEGMENT_LABELS = {
    "segment_1st_clean": "First-level (clean)",
    "segment_2nd": "Second-level",
    "segment_3rd": "Third-level",
}

INITIATOR_WORST_PERCENTILE = 90

MIN_INITIATORS_IN_PLOT = 5
MAX_INITIATORS_IN_PLOT = 20


def analyze_ping_pong_handover(log):
    """
    Detect A -> B -> A ping-pong handover patterns and collect:
    - frequency per (A, B) pair
    - bounce durations in days per pair
    """
    ping_pong_freq = defaultdict(int)
    ping_pong_durations = defaultdict(list)

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
                pair = (str(team_a1), str(team_b))
                ping_pong_freq[pair] += 1

                duration_timedelta = handovers[i + 2]["time"] - handovers[i + 1]["time"]
                duration_days = duration_timedelta.total_seconds() / (24 * 3600)
                ping_pong_durations[pair].append(duration_days)

    return ping_pong_freq, ping_pong_durations


def build_rows(freq_map, durations_map):
    rows = []

    for pair, frequency in sorted(freq_map.items(), key=lambda item: item[1], reverse=True):
        durations = durations_map[pair]
        total_lost_time_days = sum(durations)
        avg_bounce_duration_days = total_lost_time_days / len(durations) if durations else 0.0

        rows.append(
            {
                "source_team": pair[0],
                "target_team": pair[1],
                "frequency": frequency,
                "avg_bounce_duration_days": avg_bounce_duration_days,
                "total_lost_time_days": total_lost_time_days,
            }
        )

    return rows


def compute_percentile(values, percentile: float) -> float:
    if not values:
        return 0.0

    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return float(sorted_values[0])

    rank = (percentile / 100.0) * (len(sorted_values) - 1)
    lower_index = int(rank)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    weight = rank - lower_index

    return float(sorted_values[lower_index] + (sorted_values[upper_index] - sorted_values[lower_index]) * weight)


def plot_single_segment_initiators(rows, segment_label: str, output_png_path: Path):
    initiator_counts = defaultdict(int)
    for row in rows:
        initiator_counts[row["source_team"]] += int(row["frequency"])

    sorted_items = sorted(initiator_counts.items(), key=lambda item: item[1], reverse=True)

    threshold = 0.0
    if sorted_items:
        threshold = compute_percentile([item[1] for item in sorted_items], INITIATOR_WORST_PERCENTILE)
        filtered_items = [item for item in sorted_items if item[1] >= threshold]

        if len(filtered_items) < MIN_INITIATORS_IN_PLOT:
            filtered_items = sorted_items[: min(MIN_INITIATORS_IN_PLOT, len(sorted_items))]

        if len(filtered_items) > MAX_INITIATORS_IN_PLOT:
            filtered_items = filtered_items[:MAX_INITIATORS_IN_PLOT]
    else:
        filtered_items = []

    labels = [item[0] for item in filtered_items]
    values = [item[1] for item in filtered_items]

    fig_width = max(10, min(20, len(labels) * 0.5 + 4))
    fig, ax = plt.subplots(figsize=(fig_width, 7))

    if values:
        bars = ax.bar(range(len(values)), values, color="#E45756")
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9)

        max_value = max(values)
        offset = max_value * 0.01 if max_value > 0 else 0.01
        for idx, bar in enumerate(bars):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + offset,
                f"{values[idx]}",
                ha="center",
                va="bottom",
                fontsize=9,
            )
    else:
        ax.text(0.5, 0.5, "No initiator detected in this segment", ha="center", va="center", transform=ax.transAxes)
        ax.set_xticks([])

    ax.set_title(f"Worst Initiator Groups (P{INITIATOR_WORST_PERCENTILE}+) - {segment_label}")
    ax.set_xlabel("Initiator Group")
    ax.set_ylabel("Number of triggers (Ping-Pong)")
    ax.grid(axis="y", linestyle="--", alpha=0.35)

    if values:
        ax.text(
            0.99,
            0.97,
            f"Threshold (P{INITIATOR_WORST_PERCENTILE}): {threshold:.2f}",
            ha="right",
            va="top",
            transform=ax.transAxes,
            fontsize=9,
            bbox={"boxstyle": "round,pad=0.2", "facecolor": "white", "alpha": 0.7, "edgecolor": "#BBBBBB"},
        )

    plt.tight_layout()

    output_png_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_png_path, dpi=220)
    plt.close(fig)


def process_and_plot_segment(segment_name: str, input_xes_path: Path):
    print(f"Processing segment: {segment_name}...")
    log = pm4py.read_xes(str(input_xes_path), return_legacy_log_object=True)
    
    freq_map, durations_map = analyze_ping_pong_handover(log)
    rows = build_rows(freq_map, durations_map)

    segment_label = SEGMENT_LABELS.get(segment_name, segment_name)
    output_png_path = BASE_DIR / f"initiators_{segment_name}.png"
    
    plot_single_segment_initiators(rows, segment_label, output_png_path)
    print(f" -> Chart saved: {output_png_path}\n")


def main():
    for segment_name, input_xes_path in SEGMENT_INPUTS.items():
        if not input_xes_path.exists():
            print(f"Skipped {segment_name}: file not found -> {input_xes_path}\n")
            continue

        process_and_plot_segment(segment_name, input_xes_path)
        
    print("Processing completed.")


if __name__ == "__main__":
    main()