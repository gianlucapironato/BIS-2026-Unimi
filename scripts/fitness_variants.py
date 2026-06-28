import pm4py
import pandas as pd
import os

def get_cases_with_ping_pong(df, case_id_col='case:concept:name', org_group_col='org:group', time_col='time:timestamp'):
    """Identifies Case IDs of traces containing an A -> B -> A ping-pong pattern."""
    
    df_sorted = df.dropna(subset=[org_group_col]).sort_values(by=[case_id_col, time_col])
    
    cases_with_pp = set()
    
    for case_id, group_df in df_sorted.groupby(case_id_col):
        handovers = []
        current_group = None
        
        for group in group_df[org_group_col]:
            if group != current_group:
                handovers.append(group)
                current_group = group
                
        
        for i in range(len(handovers) - 2):
            team_a1 = handovers[i]
            team_b = handovers[i+1]
            team_a2 = handovers[i+2]
            
            if team_a1 == team_a2 and team_a1 != team_b:
                cases_with_pp.add(case_id)
                break 
                
    return cases_with_pp

def main():
    segment_paths = [
        "scripts/log_1st_level_clean.xes",
        "scripts/log_2nd_level.xes",
        "scripts/log_3rd_level.xes"
    ]
    
    dfs = []
    print("Reading and merging 3 segments (1st clean, 2nd, 3rd) to form the combined dataset...")
    for path in segment_paths:
        try:
            log = pm4py.read_xes(path, return_legacy_log_object=True)
        except:
            log = pm4py.read_xes(path)
        dfs.append(pm4py.convert_to_dataframe(log))
        
    df_combined = pd.concat(dfs, ignore_index=True)
    print(f"Merge completed. Combined dataset obtained with {len(df_combined)} total events.\n")
    
    case_id_col = 'case:concept:name'
    org_group_col = 'org:group'
    activity_col = 'concept:name'
    
    print("Identifying traces with ping-pong patterns (A -> B -> A)...")
    cases_with_pp = get_cases_with_ping_pong(df_combined, case_id_col, org_group_col, 'time:timestamp')
    
    all_case_ids = set(df_combined[case_id_col].unique())
    cases_without_pp = all_case_ids - cases_with_pp
    
    print(f" - Traces WITH ping-pong: {len(cases_with_pp)}")
    print(f" - Traces WITHOUT ping-pong (to use as Reference): {len(cases_without_pp)}\n")
    
    
    df_reference = df_combined[df_combined[case_id_col].isin(cases_without_pp)]
    
    print("Extracting reference model via Heuristic Miner on traces WITHOUT ping-pong...")
    net, im, fm = pm4py.discover_petri_net_heuristics(df_reference, activity_key=activity_col)
    print("Reference model generated successfully.\n")
    
    print("Saving reference model image...")
    graphviz_paths = [
        r"C:\Program Files\Graphviz\bin",
        r"C:\Program Files (x86)\Graphviz\bin",
        r"C:\ProgramData\chocolatey\lib\graphviz\tools\Graphviz\bin",
        r"C:\ProgramData\chocolatey\bin",
        os.path.expanduser(r"~\anaconda3\Library\bin\graphviz"),
        os.path.expanduser(r"~\miniconda3\Library\bin\graphviz")
    ]
    for path in graphviz_paths:
        if os.path.exists(path) and path not in os.environ["PATH"]:
            os.environ["PATH"] += os.pathsep + path
            
    pm4py.save_vis_petri_net(net, im, fm, "reference_model_combined_no_pingpong.png")
    print("Image saved to 'reference_model_combined_no_pingpong.png'\n")
    
    print("Filtering traces based on D4 and G97...")
    df_valid_groups = df_combined.dropna(subset=[org_group_col])
    traces_groups = df_valid_groups.groupby(case_id_col)[org_group_col].unique().reset_index()
    traces_groups['groups_set'] = traces_groups[org_group_col].apply(set)
    
    cases_with_D4 = set(traces_groups[traces_groups['groups_set'].apply(lambda x: 'D4' in x)][case_id_col])
    cases_with_G97 = set(traces_groups[traces_groups['groups_set'].apply(lambda x: 'G97' in x)][case_id_col])
    
    cases_D4_not_G97 = cases_with_D4 - cases_with_G97
    cases_G97_not_D4 = cases_with_G97 - cases_with_D4
    cases_neither = all_case_ids - cases_with_D4 - cases_with_G97
    
    df_D4_not_G97 = df_combined[df_combined[case_id_col].isin(cases_D4_not_G97)]
    df_G97_not_D4 = df_combined[df_combined[case_id_col].isin(cases_G97_not_D4)]
    df_neither = df_combined[df_combined[case_id_col].isin(cases_neither)]
    
    def calculate_and_print_fitness(dataframe, label):
        if len(dataframe) == 0:
            print(f"\n--- {label} ---")
            print("No traces present, skipping calculation.")
            return
            
        print(f"\n--- {label} ---")
        print(f"Analyzing {dataframe[case_id_col].nunique()} traces against 'No Ping-Pong' model...")
        
        try:
            fitness = pm4py.fitness_token_based_replay(dataframe, net, im, fm, activity_key=activity_col)
            
            print(f" -> Average Trace Fitness: {fitness.get('average_trace_fitness', 0):.4f}")
            print(f" -> Percentage of Fit Traces: {fitness.get('perc_fit_traces', 0):.2f}%")
            print(f" -> Log Fitness: {fitness.get('log_fitness', 0):.4f}")
        except Exception as e:
            print(f" Error during fitness calculation: {e}")

    
    calculate_and_print_fitness(df_D4_not_G97, "1) Traces with D4 but NOT G97")
    calculate_and_print_fitness(df_G97_not_D4, "2) Traces with G97 but NOT D4")
    calculate_and_print_fitness(df_neither, "3) Traces without D4 and without G97")
    
    calculate_and_print_fitness(df_combined, "4) Full Combined Dataset (All traces, including ping-pongs)")
    
    print("\nProcessing completed!")

if __name__ == '__main__':
    main()
