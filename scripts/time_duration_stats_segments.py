import pm4py
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

SEGMENT_INPUTS = {
    "1st level": BASE_DIR / "log_1st_level.xes",
    "2nd level": BASE_DIR / "log_2nd_level.xes",
    "3rd level": BASE_DIR / "log_3rd_level.xes",
}

def analyze_durations(segment_inputs=None, output_filename="lead_time_distribution_uncleaned.png", title_text="Incident lead times by support tier"):
    if segment_inputs is None:
        segment_inputs = SEGMENT_INPUTS
        
    data = []
    
    for segment_name, input_path in segment_inputs.items():
        if not input_path.exists():
            continue
            
        log = pm4py.read_xes(str(input_path), return_legacy_log_object=True)
        
        durations_days = []
        for trace in log:
            if len(trace) > 1:
                start_time = trace[0]["time:timestamp"]
                end_time = trace[-1]["time:timestamp"]
                
                duration = (end_time - start_time).total_seconds() / (24 * 3600)
                
                if duration <= 0:
                    duration = 1 / (24 * 3600)
                    
                durations_days.append(duration)
        
        df_segment = pd.DataFrame({
            "Segment": segment_name,
            "Duration (Days)": durations_days
        })
        
        mean_dur = df_segment["Duration (Days)"].mean()
        median_dur = df_segment["Duration (Days)"].median()
        
        print(f"--- {segment_name} ---")
        print(f"Valid traces: {len(df_segment)}")
        print(f"Mean: {mean_dur:.2f} days")
        print(f"Median: {median_dur:.4f} days\n")
        
        data.append(df_segment)
        
    if not data:
        return
        
    df_all = pd.concat(data, ignore_index=True)
    
    plt.figure(figsize=(10, 6))
    
    segments = df_all["Segment"].unique()
    plot_data = [df_all[df_all["Segment"] == seg]["Duration (Days)"] for seg in segments]
    
    box = plt.boxplot(plot_data, tick_labels=segments, patch_artist=True, showmeans=True)
    
    for patch in box['boxes']:
        patch.set_facecolor('#acc2d9')
        
    for median in box['medians']:
        median.set(color='black', linewidth=1.5)
        
    for i, data_series in enumerate(plot_data):
        mean_val = data_series.mean()
        median_val = data_series.median()
        
        plt.text(i + 1.15, median_val, f'Med: {median_val:.1f}', va='center', fontsize=9, color='black')
        plt.text(i + 1.15, mean_val, f'Mean: {mean_val:.1f}', va='center', fontsize=9, color='green')
    
    plt.yscale("log")
    import matplotlib.ticker as ticker
    formatter = ticker.ScalarFormatter()
    formatter.set_scientific(False)
    plt.gca().yaxis.set_major_formatter(formatter)
    
    plt.title(title_text)
    plt.ylabel("Lead time (days, log scale)")
    plt.xlabel("Support tier")
    
    plt.grid(axis='y', which='both', linestyle='--', alpha=0.5)
    
    output_png_path = BASE_DIR / output_filename
    plt.tight_layout()
    plt.savefig(output_png_path, dpi=300)
    plt.close()

def plot_first_segment_distribution(input_path=None):
    if input_path is None:
        input_path = SEGMENT_INPUTS["1st level"]
        
    if not input_path.exists():
        print(f"File not found: {input_path}")
        return
        
    print(f"Generating detailed distribution plot for 1st level uncleaned...")
    log = pm4py.read_xes(str(input_path), return_legacy_log_object=True)
    
    durations_days = []
    for trace in log:
        if len(trace) > 1:
            start_time = trace[0]["time:timestamp"]
            end_time = trace[-1]["time:timestamp"]
            
            duration = (end_time - start_time).total_seconds() / (24 * 3600)
            
            if duration <= 0:
                duration = 1 / (24 * 3600)
                
            durations_days.append(duration)
            
    df = pd.Series(durations_days)
    mean_val = df.mean()
    median_val = df.median()
    
    plt.figure(figsize=(12, 6))
    
    plt.hist(durations_days, bins=100, orientation='horizontal', color='#acc2d9', edgecolor='black', alpha=0.7)
    
    plt.axhline(mean_val, color='red', linestyle='dashed', linewidth=1.5, label=f'mean: {mean_val:.2f} days')
    plt.axhline(median_val, color='green', linestyle='dashed', linewidth=1.5, label=f'median: {median_val:.2f} days')
    
    plt.title("lead time distribution (1st level uncleaned)")
    plt.ylabel("lead time (days)")
    plt.xlabel("number of traces (log scale)")
    plt.xscale("log")
    
    import matplotlib.ticker as ticker
    formatter = ticker.ScalarFormatter()
    formatter.set_scientific(False)
    plt.gca().xaxis.set_major_formatter(formatter)
    
    plt.legend()
    plt.grid(axis='x', linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    output_png_path = BASE_DIR / "distribution_1st_level_uncleaned.png"
    plt.savefig(output_png_path, dpi=300)
    plt.close()
    print(f"Distribution plot saved to {output_png_path}\n")

if __name__ == "__main__":
    analyze_durations()
    
    plot_first_segment_distribution()
    
    CLEAN_SEGMENT_INPUTS = {
        "1st level": BASE_DIR / "log_1st_level_clean.xes",
        "2nd level": BASE_DIR / "log_2nd_level.xes",
        "3rd level": BASE_DIR / "log_3rd_level.xes",
    }
    
    analyze_durations(
        segment_inputs=CLEAN_SEGMENT_INPUTS,
        output_filename="lead_time_distribution_cleaned.png",
        title_text="Incident lead times by support tier (cleaned)"
    )