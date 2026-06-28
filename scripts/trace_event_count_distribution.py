from pathlib import Path

import matplotlib.pyplot as plt
import pm4py


BASE_DIR = Path(__file__).resolve().parent
INPUT_XES_PATH = BASE_DIR / "BPI_Challenge_2013_incidents.xes"
OUTPUT_TXT_PATH = BASE_DIR / "trace_event_count_distribution.txt"
OUTPUT_PNG_PATH = BASE_DIR / "trace_event_count_distribution.png"
CASE_COL_DEFAULT = "case:concept:name"


def main() -> None:
    df = pm4py.read_xes(str(INPUT_XES_PATH))

    case_col = CASE_COL_DEFAULT if CASE_COL_DEFAULT in df.columns else next(
        c for c in df.columns if c.startswith("case:")
    )

    trace_lengths = df.groupby(case_col).size()
    distribution = trace_lengths.value_counts().sort_index()

    with OUTPUT_TXT_PATH.open("w", encoding="utf-8") as f:
        f.write("numero_eventi\tnumero_trace\n")
        for n_events, n_traces in distribution.items():
            f.write(f"{int(n_events)}\t{int(n_traces)}\n")

    plt.figure(figsize=(10, 5))
    plt.bar(distribution.index.astype(int), distribution.values.astype(int), color="steelblue")
    plt.title("Distribuzione trace per numero di eventi")
    plt.xlabel("Numero di eventi nella trace")
    plt.ylabel("Numero di trace")
    plt.tight_layout()
    plt.savefig(OUTPUT_PNG_PATH, dpi=150)
    plt.show()

    print(f"Table saved to: {OUTPUT_TXT_PATH}")
    print(f"Chart saved to: {OUTPUT_PNG_PATH}")


if __name__ == "__main__":
    main()