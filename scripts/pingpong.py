import pm4py
from collections import defaultdict


BASE = r"c:\Users\biole\Desktop\BIS 2026 @ Unimi\scripts"

log = pm4py.read_xes(rf"{BASE}\log_2nd_level.xes", return_legacy_log_object=True)

ORG_GROUP_COL = "org:group"
TIMESTAMP_COL = "time:timestamp"

def analyze_ping_pong(log):
    ping_pong_freq = defaultdict(int)
    ping_pong_durations = defaultdict(list)
    
    for trace in log:
        handovers = []
        current_group = None
        
        for event in trace:
            group = event.get(ORG_GROUP_COL)
            timestamp = event.get(TIMESTAMP_COL)
            
            if group and group != current_group:
                handovers.append({
                    "group": group, 
                    "time": timestamp
                })
                current_group = group
                
        for i in range(len(handovers) - 2):
            team_a1 = handovers[i]["group"]
            team_b  = handovers[i+1]["group"]
            team_a2 = handovers[i+2]["group"]
            
            if team_a1 == team_a2 and team_a1 != team_b:
                pair = (team_a1, team_b)
                
                ping_pong_freq[pair] += 1
                
                duration_timedelta = handovers[i+2]["time"] - handovers[i+1]["time"]
                duration_days = duration_timedelta.total_seconds() / (24 * 3600)
                
                ping_pong_durations[pair].append(duration_days)

    return ping_pong_freq, ping_pong_durations

freq, durations = analyze_ping_pong(log)

print("Top Ping-Pong Pairs (A -> B -> A):")
sorted_freq = sorted(freq.items(), key=lambda x: x[1], reverse=True)

for pair, count in sorted_freq[:10]:
    avg_duration = sum(durations[pair]) / len(durations[pair])
    print(f"Team {pair[0]} <-> Team {pair[1]} | Frequency: {count} times | Average bounce duration: {avg_duration:.2f} days")