from __future__ import annotations

import csv
import statistics
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
    "segment_1st_clean": "1st level (clean)",
    "segment_2nd": "2nd level",
    "segment_3rd": "3rd level",
}

WORST_PERCENTILE_BY_METRIC = {
    "frequency": 90,
    "total_lost_time_days": 90,
}

INITIATOR_WORST_PERCENTILE = 90

MIN_PAIRS_IN_PLOT = 5
MAX_PAIRS_IN_PLOT = 20
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

                duration_timedelta = handovers[i + 2]["time"] - handovers[i]["time"]
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


def save_csv(rows, output_csv_path: Path):
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)

    with output_csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "source_team",
                "target_team",
                "frequency",
                "avg_bounce_duration_days",
                "total_lost_time_days",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "source_team": row["source_team"],
                    "target_team": row["target_team"],
                    "frequency": row["frequency"],
                    "avg_bounce_duration_days": f"{row['avg_bounce_duration_days']:.6f}",
                    "total_lost_time_days": f"{row['total_lost_time_days']:.6f}",
                }
            )


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


def select_worst_pairs(rows, value_key: str, percentile: float, min_pairs: int, max_pairs: int):
    if not rows:
        return [], 0.0

    threshold = compute_percentile([row[value_key] for row in rows], percentile)

    filtered_rows = [row for row in rows if row[value_key] >= threshold]
    filtered_rows = sorted(filtered_rows, key=lambda row: row[value_key], reverse=True)

    if len(filtered_rows) < min_pairs:
        filtered_rows = sorted(rows, key=lambda row: row[value_key], reverse=True)[: min(min_pairs, len(rows))]

    if len(filtered_rows) > max_pairs:
        filtered_rows = filtered_rows[:max_pairs]

    return filtered_rows, threshold


def _plot_single_segment_distribution(ax, rows, value_key: str, segment_label: str, ylabel: str):
    percentile = WORST_PERCENTILE_BY_METRIC.get(value_key, 90)
    selected_rows, threshold = select_worst_pairs(
        rows=rows,
        value_key=value_key,
        percentile=percentile,
        min_pairs=MIN_PAIRS_IN_PLOT,
        max_pairs=MAX_PAIRS_IN_PLOT,
    )

    labels = [f"{row['source_team']} -> {row['target_team']}" for row in selected_rows]
    values = [row[value_key] for row in selected_rows]

    if values:
        bars = ax.bar(range(len(values)), values, color="#4C78A8")
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=70, ha="right", fontsize=8)

        max_value = max(values)
        offset = max_value * 0.01 if max_value > 0 else 0.01
        for idx, bar in enumerate(bars):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + offset,
                f"{values[idx]:.2f}",
                ha="center",
                va="bottom",
                fontsize=7,
            )
    else:
        ax.text(0.5, 0.5, "No ping-pong pairs detected", ha="center", va="center", transform=ax.transAxes)
        ax.set_xticks([])

    ax.set_title(segment_label)
    ax.set_xlabel("Ping-pong pair (A -> B)")
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", linestyle="--", alpha=0.35)

    if values:
        ax.text(
            0.99,
            0.97,
            f"Threshold: {threshold:.2f}",
            ha="right",
            va="top",
            transform=ax.transAxes,
            fontsize=8,
            bbox={"boxstyle": "round,pad=0.2", "facecolor": "white", "alpha": 0.7, "edgecolor": "#BBBBBB"},
        )


def plot_combined_distribution(segment_rows_map, value_key: str, figure_title: str, ylabel: str, output_png_path: Path):
    fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(18, 18))

    ordered_segments = ["segment_1st_clean", "segment_2nd", "segment_3rd"]
    for ax, segment_name in zip(axes, ordered_segments):
        rows = segment_rows_map.get(segment_name, [])
        segment_label = SEGMENT_LABELS.get(segment_name, segment_name)
        _plot_single_segment_distribution(ax, rows, value_key, segment_label, ylabel)

    fig.suptitle(figure_title, fontsize=16)
    plt.tight_layout(rect=(0, 0, 1, 0.98))

    output_png_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_png_path, dpi=220)
    plt.close(fig)


def plot_initiator_distribution(segment_rows_map, output_png_path: Path):
    initiator_counts = defaultdict(int)

    for rows in segment_rows_map.values():
        for row in rows:
            initiator_counts[row["source_team"]] += int(row["frequency"])

    sorted_items = sorted(initiator_counts.items(), key=lambda item: item[1], reverse=True)

    threshold = 0.0
    if sorted_items:
        threshold = compute_percentile([item[1] for item in sorted_items], INITIATOR_WORST_PERCENTILE)
        sorted_items = [item for item in sorted_items if item[1] >= threshold]

        if len(sorted_items) < MIN_INITIATORS_IN_PLOT:
            all_sorted = sorted(initiator_counts.items(), key=lambda item: item[1], reverse=True)
            sorted_items = all_sorted[: min(MIN_INITIATORS_IN_PLOT, len(all_sorted))]

        if len(sorted_items) > MAX_INITIATORS_IN_PLOT:
            sorted_items = sorted_items[:MAX_INITIATORS_IN_PLOT]

    labels = [item[0] for item in sorted_items]
    values = [item[1] for item in sorted_items]

    fig_width = max(12, min(28, len(labels) * 0.45 + 6))
    fig, ax = plt.subplots(figsize=(fig_width, 7))

    if values:
        bars = ax.bar(range(len(values)), values, color="#E45756")
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=70, ha="right", fontsize=8)

        max_value = max(values)
        offset = max_value * 0.01 if max_value > 0 else 0.01
        for idx, bar in enumerate(bars):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + offset,
                f"{values[idx]}",
                ha="center",
                va="bottom",
                fontsize=7,
            )
    else:
        ax.text(
            0.5,
            0.5,
            "No ping-pong initiators detected",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_xticks([])

    ax.set_title("Ping-pong patterns started by initiator group")
    ax.set_xlabel("Initiator group")
    ax.set_ylabel("Number of started ping-pong patterns")
    ax.grid(axis="y", linestyle="--", alpha=0.35)

    if values:
        ax.text(
            0.99,
            0.97,
            f"Threshold: {threshold:.2f}",
            ha="right",
            va="top",
            transform=ax.transAxes,
            fontsize=8,
            bbox={"boxstyle": "round,pad=0.2", "facecolor": "white", "alpha": 0.7, "edgecolor": "#BBBBBB"},
        )

    plt.tight_layout()

    output_png_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_png_path, dpi=220)
    plt.close(fig)


def process_segment(segment_name: str, input_xes_path: Path):
    log = pm4py.read_xes(str(input_xes_path), return_legacy_log_object=True)
    freq_map, durations_map = analyze_ping_pong_handover(log)
    rows = build_rows(freq_map, durations_map)

    output_csv_path = BASE_DIR / f"pingpong_stats_{segment_name}.csv"

    save_csv(rows, output_csv_path)

    print(f"Processed segment: {segment_name}")
    print(f"  Input XES: {input_xes_path}")
    print(f"  CSV: {output_csv_path}")

    return rows


def main():
    segment_rows_map = {}

    for segment_name, input_xes_path in SEGMENT_INPUTS.items():
        if not input_xes_path.exists():
            print(f"Skipped {segment_name}: file not found -> {input_xes_path}")
            segment_rows_map[segment_name] = []
            continue

        segment_rows_map[segment_name] = process_segment(segment_name, input_xes_path)

    frequency_png_path = BASE_DIR / "pingpong_frequency_distribution_all_segments.png"
    total_lost_time_png_path = BASE_DIR / "pingpong_total_lost_time_distribution_all_segments.png"
    initiator_png_path = BASE_DIR / "pingpong_initiator_distribution_all_segments.png"

    plot_combined_distribution(
        segment_rows_map=segment_rows_map,
        value_key="frequency",
        figure_title="Ping-pong frequency by pair",
        ylabel="Bounce frequency",
        output_png_path=frequency_png_path,
    )

    plot_combined_distribution(
        segment_rows_map=segment_rows_map,
        value_key="total_lost_time_days",
        figure_title="Total lost time by pair",
        ylabel="Total lost time (days)",
        output_png_path=total_lost_time_png_path,
    )

    plot_initiator_distribution(
        segment_rows_map=segment_rows_map,
        output_png_path=initiator_png_path,
    )

    print(f"Combined frequency chart: {frequency_png_path}")
    print(f"Combined lost-time chart: {total_lost_time_png_path}")
    print(f"Initiator distribution chart: {initiator_png_path}")


    print("\nComputing average trace durations by ping-pong presence...")
    stats_data = []

    for segment_name, input_xes_path in SEGMENT_INPUTS.items():
        if not input_xes_path.exists():
            continue

        log = pm4py.read_xes(str(input_xes_path), return_legacy_log_object=True)

        with_pp_durations = []
        without_pp_durations = []

        for trace in log:
            if len(trace) < 2:
                continue

            handovers = []
            current_group = None
            for event in trace:
                group = event.get(ORG_GROUP_COL)
                timestamp = event.get(TIMESTAMP_COL)
                if group and timestamp and group != current_group:
                    handovers.append({"group": group, "time": timestamp})
                    current_group = group

            has_ping_pong = False
            for i in range(len(handovers) - 2):
                if handovers[i]["group"] == handovers[i + 2]["group"] and handovers[i]["group"] != handovers[i + 1]["group"]:
                    has_ping_pong = True
                    break

            start_time = trace[0][TIMESTAMP_COL]
            end_time = trace[-1][TIMESTAMP_COL]
            duration_days = (end_time - start_time).total_seconds() / (24 * 3600)

            if has_ping_pong:
                with_pp_durations.append(duration_days)
            else:
                without_pp_durations.append(duration_days)

        mean_with = sum(with_pp_durations) / len(with_pp_durations) if with_pp_durations else 0.0
        mean_without = sum(without_pp_durations) / len(without_pp_durations) if without_pp_durations else 0.0
        median_with = statistics.median(with_pp_durations) if with_pp_durations else 0.0
        median_without = statistics.median(without_pp_durations) if without_pp_durations else 0.0
        
        label = SEGMENT_LABELS.get(segment_name, segment_name)
        stats_data.append({
            "Segment": label,
            "Mean Duration w/ Ping-Pong (days)": mean_with,
            "Median Duration w/ Ping-Pong (days)": median_with,
            "Mean Duration w/o Ping-Pong (days)": mean_without,
            "Median Duration w/o Ping-Pong (days)": median_without,
            "Count w/ Ping-Pong": len(with_pp_durations),
            "Count w/o Ping-Pong": len(without_pp_durations)
        })

    if stats_data:
        stats_csv_path = BASE_DIR / "pingpong_trace_durations_comparison.csv"
        stats_tex_path = BASE_DIR / "pingpong_trace_durations_comparison.tex"

        with stats_csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=stats_data[0].keys())
            writer.writeheader()
            for row in stats_data:
                row_copy = row.copy()
                row_copy["Mean Duration w/ Ping-Pong (days)"] = f"{row['Mean Duration w/ Ping-Pong (days)']:.2f}"
                row_copy["Median Duration w/ Ping-Pong (days)"] = f"{row['Median Duration w/ Ping-Pong (days)']:.2f}"
                row_copy["Mean Duration w/o Ping-Pong (days)"] = f"{row['Mean Duration w/o Ping-Pong (days)']:.2f}"
                row_copy["Median Duration w/o Ping-Pong (days)"] = f"{row['Median Duration w/o Ping-Pong (days)']:.2f}"
                writer.writerow(row_copy)

        with stats_tex_path.open("w", encoding="utf-8") as f:
            f.write("\\begin{table}[h]\n")
            f.write("\\centering\n")
            f.write("\\begin{tabular}{lrrrrrr}\n")
            f.write("\\hline\n")
            f.write("Segment & Mean w/ PP (d) & Med w/ PP (d) & Mean w/o PP (d) & Med w/o PP (d) & Traces w/ PP & Traces w/o PP \\\\\n")
            f.write("\\hline\n")
            for row in stats_data:
                f.write(f"{row['Segment']} & {row['Mean Duration w/ Ping-Pong (days)']:.2f} & {row['Median Duration w/ Ping-Pong (days)']:.2f} & {row['Mean Duration w/o Ping-Pong (days)']:.2f} & {row['Median Duration w/o Ping-Pong (days)']:.2f} & {row['Count w/ Ping-Pong']} & {row['Count w/o Ping-Pong']} \\\\\n")
            f.write("\\hline\n")
            f.write("\\end{tabular}\n")
            f.write("\\caption{Comparison of trace durations with and without ping-pong handovers.}\n")
            f.write("\\label{tab:pingpong_duration_comparison}\n")
            f.write("\\end{table}\n")

        print(f"Ping-pong duration comparison CSV: {stats_csv_path}")
        print(f"Ping-pong duration comparison TEX: {stats_tex_path}")


if __name__ == "__main__":
    main()
