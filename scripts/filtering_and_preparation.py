import pm4py
import pandas as pd
import matplotlib.pyplot as plt

BASE = r"c:\Users\biole\Desktop\BIS 2026 @ Unimi\scripts"

LOGS = {
    "Complete":             rf"{BASE}\BPI_Challenge_2013_incidents.xes",
    "Only 1st level":       rf"{BASE}\log_1st_level.xes",
    "Reaches 2nd level":    rf"{BASE}\log_2nd_level.xes",
    "Reaches 3rd level":    rf"{BASE}\log_3rd_level.xes",
}

CASE_COL = "case:concept:name"


def load_trace_lengths(path: str) -> pd.Series:
    df = pm4py.read_xes(path)
    col = CASE_COL if CASE_COL in df.columns else next(c for c in df.columns if c.startswith("case:"))
    return df.groupby(col).size()


def print_stats(label: str, s: pd.Series) -> None:
    print(f"\n=== {label} ===")
    print(f"  Total traces : {len(s)}")
    print(f"  Total events : {s.sum()}")
    print(f"  Min    : {s.min()}")
    print(f"  Max    : {s.max()}")
    print(f"  Mean   : {s.mean():.2f}")
    print(f"  Median : {s.median():.1f}")
    print(f"  Std    : {s.std():.2f}")
    print(f"  Q1     : {s.quantile(0.25):.1f}")
    print(f"  Q3     : {s.quantile(0.75):.1f}")
    print(f"  Q95    : {s.quantile(0.95):.1f}")


def plot_distribution(ax_hist, ax_box, s: pd.Series, title: str, color: str) -> None:
    max_val = int(s.max())
    ax_hist.hist(s, bins=range(1, max_val + 2), color=color, edgecolor="white", linewidth=0.3)
    ax_hist.axvline(s.mean(),   color="red",    linestyle="--", linewidth=1.3, label=f"Mean={s.mean():.1f}")
    ax_hist.axvline(s.median(), color="orange", linestyle="--", linewidth=1.3, label=f"Median={s.median():.0f}")
    ax_hist.set_title(title, fontsize=10)
    ax_hist.set_xlabel("Number of events per trace")
    ax_hist.set_ylabel("Number of traces")
    ax_hist.legend(fontsize=8)

    ax_box.boxplot(
        s.tolist(), orientation="vertical", patch_artist=True,
        boxprops=dict(facecolor=color, color="navy", alpha=0.7),
        medianprops=dict(color="orange", linewidth=2),
        flierprops=dict(marker=".", markersize=3, alpha=0.4),
    )
    ax_box.set_ylabel("Number of events per trace")
    ax_box.set_xticks([])


print("Loading logs...")
data: dict[str, pd.Series] = {}
for label, path in LOGS.items():
    print(f"  {label}: {path.split(chr(92))[-1]}")
    data[label] = load_trace_lengths(path)
    print_stats(label, data[label])

fig1, (ax_h, ax_b) = plt.subplots(1, 2, figsize=(14, 5))
fig1.suptitle("Complete dataset - Volvo IT Incidents", fontsize=12)
plot_distribution(ax_h, ax_b, data["Complete"], "Complete histogram", "steelblue")
plt.tight_layout()
fig1.savefig(rf"{BASE}\dist_complete.png", dpi=150)


SEGMENT_LABELS = ["Only 1st level", "Reaches 2nd level", "Reaches 3rd level"]
COLORS  = ["#2ca02c", "#ff7f0e", "#d62728"]
TITLES  = [
    "1st level (not escalated)",
    "2nd level (escalated once)",
    "3rd level (escalated twice)",
]

fig2, axes = plt.subplots(2, 3, figsize=(17, 9))
fig2.suptitle("Trace length distribution by escalation level", fontsize=13)
for col, (lbl, color, title) in enumerate(zip(SEGMENT_LABELS, COLORS, TITLES)):
    plot_distribution(axes[0, col], axes[1, col], data[lbl], title, color)
plt.tight_layout()
fig2.savefig(rf"{BASE}\dist_segments.png", dpi=150)

plt.show()
print("\nPlots saved:")
print(f"  scripts/dist_complete.png")
print(f"  scripts/dist_segments.png")
