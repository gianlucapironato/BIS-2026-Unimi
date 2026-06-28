import pm4py
import pandas as pd
import matplotlib.pyplot as plt

BASE = r"c:\Users\biole\Desktop\BIS 2026 @ Unimi\scripts"

LOGS = {
    "First-level only":      rf"{BASE}\log_1st_level.xes",
    "Escalated to level 2":  rf"{BASE}\log_2nd_level.xes",
    "Escalated to level 3":  rf"{BASE}\log_3rd_level.xes",
}

CASE_COL = "case:concept:name"
TIMESTAMP_COL = "time:timestamp"
SECONDS_PER_DAY = 24 * 60 * 60
SHORT_TRACE_THRESHOLD_DAYS = 0.01


def load_trace_durations_days(path: str) -> pd.Series:
    df = pm4py.read_xes(path)
    case_col = CASE_COL if CASE_COL in df.columns else next(c for c in df.columns if c.startswith("case:"))
    if TIMESTAMP_COL not in df.columns:
        raise KeyError(f"Colonna timestamp non trovata in {path}: attesa '{TIMESTAMP_COL}'")

    timestamps = pd.to_datetime(df[TIMESTAMP_COL], utc=True, errors="coerce")
    if timestamps.isna().any():
        raise ValueError(f"Sono presenti timestamp non validi in {path}")

    durations = (
        df.assign(**{TIMESTAMP_COL: timestamps})
          .groupby(case_col)[TIMESTAMP_COL]
          .agg(["min", "max"])
    )
    return (durations["max"] - durations["min"]).dt.total_seconds() / SECONDS_PER_DAY


def print_stats(label: str, s: pd.Series) -> None:
    print(f"\n=== {label} ===")
    print(f"  Total traces           : {len(s)}")
    print(f"  Minimum duration (days): {s.min():.2f}")
    print(f"  Maximum duration (days): {s.max():.2f}")
    print(f"  Mean duration (days)   : {s.mean():.2f}")
    print(f"  Median duration (days) : {s.median():.2f}")
    print(f"  Std. dev. (days)       : {s.std():.2f}")
    print(f"  Q1 (days)              : {s.quantile(0.25):.2f}")
    print(f"  Q3 (days)              : {s.quantile(0.75):.2f}")
    print(f"  95th percentile (days) : {s.quantile(0.95):.2f}")


def build_frequency_table(label: str, s: pd.Series) -> pd.DataFrame:
    day_counts = s.astype(int).value_counts().sort_index()
    table = pd.DataFrame({
        "segment": label,
        "duration_days_floor": day_counts.index,
        "trace_count": day_counts.values,
    })
    table["percentage"] = table["trace_count"] / table["trace_count"].sum() * 100
    table["cumulative_percentage"] = table["percentage"].cumsum()
    return table


def print_frequency_table(label: str, s: pd.Series) -> pd.DataFrame:
    table = build_frequency_table(label, s)
    display_table = table.copy()
    display_table["percentage"] = display_table["percentage"].map(lambda x: f"{x:.2f}")
    display_table["cumulative_percentage"] = display_table["cumulative_percentage"].map(lambda x: f"{x:.2f}")
    print(f"\nTabular duration distribution by integer days - {label}")
    print("(duration in days floored to the nearest integer)")
    print(display_table[["duration_days_floor", "trace_count", "percentage", "cumulative_percentage"]].to_string(index=False))
    return table


def plot_distribution(ax_hist, ax_box, s: pd.Series, title: str, color: str) -> None:
    bins = min(40, max(10, int(len(s) ** 0.5)))
    ax_hist.hist(s, bins=bins, color=color, edgecolor="white", linewidth=0.3)
    ax_hist.axvline(s.mean(), color="red", linestyle="--", linewidth=1.3, label=f"Mean={s.mean():.2f} days")
    ax_hist.axvline(s.median(), color="orange", linestyle="--", linewidth=1.3, label=f"Median={s.median():.2f} days")
    ax_hist.set_title(title, fontsize=10)
    ax_hist.set_xlabel("Trace duration (days)")
    ax_hist.set_ylabel("Trace count")
    ax_hist.legend(fontsize=8)

    ax_box.boxplot(
        s.tolist(), orientation="vertical", patch_artist=True,
        boxprops=dict(facecolor=color, color="navy", alpha=0.7),
        medianprops=dict(color="orange", linewidth=2),
        flierprops=dict(marker=".", markersize=3, alpha=0.4),
    )
    ax_box.set_ylabel("Trace duration (days)")
    ax_box.set_xticks([])


print("Loading event logs...")
data: dict[str, pd.Series] = {}
tables: list[pd.DataFrame] = []
for label, path in LOGS.items():
    print(f"  {label}: {path.split(chr(92))[-1]}")
    data[label] = load_trace_durations_days(path)
    print_stats(label, data[label])
    tables.append(print_frequency_table(label, data[label]))


SEGMENT_LABELS = ["First-level only", "Escalated to level 2", "Escalated to level 3"]
COLORS = ["#2ca02c", "#ff7f0e", "#d62728"]
TITLES = [
    "First level (non-escalated)",
    "Second level (single escalation)",
    "Third level (double escalation)",
]

fig, axes = plt.subplots(2, 3, figsize=(17, 9))
fig.suptitle("Trace duration distribution by escalation level", fontsize=13)
for col, (label, color, title) in enumerate(zip(SEGMENT_LABELS, COLORS, TITLES)):
    plot_distribution(axes[0, col], axes[1, col], data[label], title, color)

plt.tight_layout()
fig.savefig(rf"{BASE}\dist_time_segmenti.png", dpi=150)

frequency_table = pd.concat(tables, ignore_index=True)
frequency_table.to_csv(rf"{BASE}\dist_time.txt", sep="\t", index=False)

plt.show()
print("\nPlot saved:")
print("  scripts/dist_time_segmenti.png")
print("Tabular output saved:")
print("  scripts/dist_time.txt")

print(f"\nTrace count with duration < {SHORT_TRACE_THRESHOLD_DAYS} days:")
total_short = 0
for label in SEGMENT_LABELS:
    n_short = int((data[label] < SHORT_TRACE_THRESHOLD_DAYS).sum())
    total_short += n_short
    print(f"  {label}: {n_short}")
print(f"  Total: {total_short}")