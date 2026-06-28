from __future__ import annotations

import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import pm4py

BASE_DIR = Path(__file__).resolve().parent

ORIGINAL_LOG = BASE_DIR / "BPI_Challenge_2013_incidents.xes"

SEGMENT_LOGS = [
    BASE_DIR / "log_1st_level_clean.xes",
    BASE_DIR / "log_2nd_level.xes",
    BASE_DIR / "log_3rd_level.xes",
]

def get_daily_counts(df: pd.DataFrame) -> pd.Series:
    """Extract daily event counts from a dataframe."""
    
    timestamps = pd.to_datetime(df["time:timestamp"], utc=True)
    
    daily_counts = timestamps.dt.date.value_counts().sort_index()
    return daily_counts

def plot_daily_distribution(daily_counts: pd.Series, title: str, ylabel: str, output_path: Path, color: str):
    dates = [d.isoformat() for d in daily_counts.index]
    values = daily_counts.values

    
    fig_width = max(12, min(30, len(dates) * 0.15))
    fig, ax = plt.subplots(figsize=(fig_width, 6))

    if not dates:
        ax.text(0.5, 0.5, "No events found", ha="center", va="center")
        ax.set_xticks([])
    else:
        bars = ax.bar(dates, values, color=color, edgecolor="black", width=1.0, linewidth=0.5)
        
        if len(dates) <= 60:
            max_value = max(values) if len(values) > 0 else 0
            offset = max_value * 0.01 if max_value > 0 else 0.01
            for idx, bar in enumerate(bars):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + offset,
                    f"{values[idx]}",
                    ha="center",
                    va="bottom",
                    fontsize=6,
                    rotation=90
                )

        
        step = max(1, len(dates) // 50)
        ax.set_xticks(range(0, len(dates), step))
        ax.set_xticklabels([dates[i] for i in range(0, len(dates), step)], rotation=70, ha="right", fontsize=9)
        
    ax.set_title(title, fontsize=14, pad=15)
    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.grid(axis="y", linestyle="--", alpha=0.35)

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=220)
    plt.close(fig)

def main():
    print(f"Loading original log: {ORIGINAL_LOG.name}")
    if ORIGINAL_LOG.exists():
        df_original = pm4py.read_xes(str(ORIGINAL_LOG))
        original_counts = get_daily_counts(df_original)
        
        original_plot_path = BASE_DIR / "event_yearly_distribution_original.png"
        plot_daily_distribution(
            original_counts,
            title="Daily events (original dataset)",
            ylabel="Events",
            output_path=original_plot_path,
            color="#1f77b4" 
        )
        print(f"Chart saved: {original_plot_path}")
    else:
        print(f"File non trovato: {ORIGINAL_LOG.name}")

    
    segment_dfs = []
    for log_path in SEGMENT_LOGS:
        if log_path.exists():
            print(f"Loading segment log: {log_path.name}")
            df = pm4py.read_xes(str(log_path))
            segment_dfs.append(df)
        else:
            print(f"File not found: {log_path.name}")
            
    if segment_dfs:
        df_segments = pd.concat(segment_dfs, ignore_index=True)
        segments_counts = get_daily_counts(df_segments)
        
        segments_plot_path = BASE_DIR / "event_yearly_distribution_segments.png"
        plot_daily_distribution(
            segments_counts,
            title="Daily events (1st clean + 2nd + 3rd)",
            ylabel="Events",
            output_path=segments_plot_path,
            color="#2ca02c"
        )
        print(f"Chart saved: {segments_plot_path}")
    else:
        print("No segment logs found to plot.")

if __name__ == "__main__":
    main()
