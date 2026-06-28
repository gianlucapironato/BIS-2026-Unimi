from pathlib import Path

import pm4py


BASE_DIR = Path(__file__).resolve().parent
INPUT_XES_PATH  = BASE_DIR / "log_1st_level.xes"
OUTPUT_XES_PATH = BASE_DIR / "log_1st_level_clean.xes"

EVENT_COUNT_THRESHOLD   = 3
SECONDS_PER_DAY         = 24 * 60 * 60


def trace_duration_days(trace) -> float:
    from pandas import to_datetime
    first_ts = to_datetime(trace[0]["time:timestamp"], utc=True)
    last_ts  = to_datetime(trace[-1]["time:timestamp"], utc=True)
    return (last_ts - first_ts).total_seconds() / SECONDS_PER_DAY


log = pm4py.read_xes(str(INPUT_XES_PATH), return_legacy_log_object=True)

cleaned_log = type(log)(
    attributes=dict(log.attributes),
    extensions=dict(log.extensions),
    classifiers=dict(log.classifiers),
    omni_present=dict(log.omni_present),
    properties=dict(log.properties),
)

n_removed = 0
for trace in log:
    duration = trace_duration_days(trace)
    n_events = len(trace)
    if n_events <= EVENT_COUNT_THRESHOLD:
        n_removed += 1
    else:
        cleaned_log.append(trace)

pm4py.write_xes(cleaned_log, str(OUTPUT_XES_PATH))

n_input  = len(log)
n_output = len(cleaned_log)

print(f"Input  : {INPUT_XES_PATH.name}")
print(f"Output : {OUTPUT_XES_PATH.name}")
print("-" * 40)
print(f"Input traces    : {n_input}")
print(f"Removed traces  : {n_removed}  (events <= {EVENT_COUNT_THRESHOLD})")
print(f"Output traces   : {n_output}")
