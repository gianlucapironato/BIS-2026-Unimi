from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pm4py


BASE_DIR = Path(__file__).resolve().parent
INPUT_XES_PATH = BASE_DIR / "log_1st_level.xes"
OUTPUT_XES_PATH = BASE_DIR / "log_1st_level_only_3events.xes"
TARGET_LENGTH = 3



log = pm4py.read_xes(str(INPUT_XES_PATH), return_legacy_log_object=True)


filtered_log = type(log)(
    attributes=dict(log.attributes),
    extensions=dict(log.extensions),
    classifiers=dict(log.classifiers),
    omni_present=dict(log.omni_present),
    properties=dict(log.properties),
)

for trace in log:
    if len(trace) == TARGET_LENGTH:
        filtered_log.append(trace)

pm4py.write_xes(filtered_log, str(OUTPUT_XES_PATH))

n_input = len(log)
n_output = len(filtered_log)
p_output = (n_output / n_input * 100) if n_input else 0.0

print(f"Created: {OUTPUT_XES_PATH}")
print()
print("3-event trace extraction")
print("-" * 40)
print(f"Input traces : {n_input}")
print(f"Output traces: {n_output}")
print(f"Percentage   : {p_output:.2f}%")


def trace_duration_days(trace) -> float:
    first_ts = pd.to_datetime(trace[0]["time:timestamp"], utc=True)
    last_ts = pd.to_datetime(trace[-1]["time:timestamp"], utc=True)
    return (last_ts - first_ts).total_seconds() / (24 * 60 * 60)


if n_output:
    durations_days = pd.Series([trace_duration_days(trace) for trace in filtered_log], name="duration_days")

    print()
    print("Duration distribution (3-event traces)")
    print("-" * 40)
    print(f"Min days : {durations_days.min():.4f}")
    print(f"Max days : {durations_days.max():.4f}")
    print(f"Mean days: {durations_days.mean():.4f}")
    print(f"Median   : {durations_days.median():.4f}")
    print(f"Std days : {durations_days.std():.4f}")

    fig, (ax_hist, ax_box) = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("Duration distribution - 3-event traces (1st level)", fontsize=12)

    bins = min(40, max(10, int(len(durations_days) ** 0.5)))
    ax_hist.hist(durations_days, bins=bins, color="steelblue", edgecolor="white", linewidth=0.3)
    ax_hist.axvline(
        durations_days.mean(),
        color="red",
        linestyle="--",
        linewidth=1.3,
        label=f"Mean={durations_days.mean():.3f} days",
    )
    ax_hist.axvline(
        durations_days.median(),
        color="orange",
        linestyle="--",
        linewidth=1.3,
        label=f"Median={durations_days.median():.3f} days",
    )
    ax_hist.set_xlabel("Trace duration (days)")
    ax_hist.set_ylabel("Number of traces")
    ax_hist.legend(fontsize=8)

    ax_box.boxplot(
        durations_days.tolist(),
        orientation="vertical",
        patch_artist=True,
        boxprops=dict(facecolor="steelblue", color="navy", alpha=0.7),
        medianprops=dict(color="orange", linewidth=2),
        flierprops=dict(marker=".", markersize=3, alpha=0.4),
    )
    ax_box.set_ylabel("Trace duration (days)")
    ax_box.set_xticks([])

    plt.tight_layout()
    plot_path = BASE_DIR / "dist_time_3event_traces_from_1st_level.png"
    fig.savefig(plot_path, dpi=150)
    plt.show()

    print(f"Plot saved : {plot_path}")
else:
    print("No 3-event traces found; duration distribution plot skipped.")
