import pandas as pd
import numpy as np
import pyreadstat
import os

# ==============================================================================
# GLOBAL CONFIG
# ==============================================================================
ALL_ACTIVITIES = [
    "Work", "Sell goods or provide services", "Housework", "Eating", "Sleeping",
    "Personal care", "Shopping", "Caring", "Education", "Sport",
    "TV/Online videos", "Passive leisure", "Active leisure",
    "Outdoor activities", "Relaxing", "Travelling", "Others"
]

# ==============================================================================
# DATA LOADING
# ==============================================================================
def load_and_transform_data():
    """
    Loads and standardizes both Canadian and Vietnamese Time Use Data.
    Assumes files are in their respective paths as provided by the user.
    """
    # --------------------------------------------------------------------------
    # 1. LOAD VIETNAM DATA
    # --------------------------------------------------------------------------
    vn_file = r'Data sources\VNM_2022_TUS_v01_M\Data\4_diary_main.csv'
    try:
        df_vn = pd.read_csv(vn_file, usecols=["ID", "age", "gender", "BEGIN", "Q401"], encoding='latin-1')
    except Exception as e:
        print(f"Warning: Could not load VN data. Using mock data. Error: {e}")
        df_vn = pd.DataFrame()

    # --------------------------------------------------------------------------
    # 2. LOAD CANADA DATA
    # --------------------------------------------------------------------------
    ca_episode_file = r'Data sources\CAN_TU_ET_2022\Data_Données\TU_ET_2022_Episode_PUMF.sas7bdat'
    ca_main_file = r'Data sources\CAN_TU_ET_2022\Data_Données\TU_ET_2022_Main_Principal_PUMF.sas7bdat'
    
    try:
        df_ca_episode, _ = pyreadstat.read_sas7bdat(ca_episode_file, usecols=["PUMFID", "STARTMIN", "TUI_01"])
        df_ca_main, _ = pyreadstat.read_sas7bdat(ca_main_file, usecols=["PUMFID", "GENDER2", "AGEGR10"])
        df_ca = pd.merge(df_ca_episode, df_ca_main, on="PUMFID", how="left")
    except Exception as e:
        print(f"Warning: Could not load CA SAS data. Using mock data. Error: {e}")
        df_ca = pd.DataFrame()

    # --------------------------------------------------------------------------
    # 3. MAPPING FUNCTIONS
    # --------------------------------------------------------------------------
    def get_vn_activity(code):
        try:
            code = int(float(code))
        except:
            return "Others"
        if code in [101, 102, 199, 201, 202, 299, 301, 302, 399, 401, 402, 499, 502]: return "Work"
        elif code in [198, 298, 298, 498, 598, 698, 798, 898, 998, 1098, 1198, 1298, 1398, 1498, 1598]: return "Travelling"
        elif code in [501, 504, 505, 506, 507, 508]: return "Sell goods or provide services"
        elif code in [601]: return "Housework"
        elif code in [602]: return "Shopping"
        elif code in [701, 702]: return "Caring"
        elif code in [901, 902, 903]: return "Education"
        elif code in [1201, 1202, 1203, 1299]: return "Active leisure"
        elif code in [1301]: return "Sport"
        elif code in [1302, 1399]: return "Outdoor activities"
        elif code == 1402: return "TV/Online videos"
        elif code == 1404: return "Passive leisure"
        elif code == 1501: return "Sleeping"
        elif code == 1502: return "Eating"
        elif code == 1503: return "Personal care"
        elif code == 1506: return "Relaxing"
        else: return "Others"

    ca_to_vn = {
        "Work": [501, 502, 503, 504, 506, 507, 599],
        "Sell goods or provide services": [505],
        "Housework": list(range(201, 210)) + list(range(231, 242)),
        "Eating": [150, 151, 152, 153, 154, 404],
        "Sleeping": list(range(100, 110)),
        "Personal care": [126, 127, 128, 129, 130, 199, 401],
        "Shopping": [260, 261, 262, 263, 264],
        "Caring": list(range(300, 308)) + list(range(350, 354)) + [801, 802],
        "Education": [600, 601, 602, 603, 604],
        "Sport": [1001, 1002, 1003, 1004, 1005, 413],
        "TV/Online videos": [1202],
        "Passive leisure": [1201, 1203, 1204],
        "Active leisure": [1105],
        "Outdoor activities": [1106],
        "Relaxing": [1301, 1302, 1303],
        "Travelling": list(range(400, 417)),
        "Others": [9999, 1304]
    }

    def map_ca_activity(code):
        try:
            if pd.isna(code): return "Others"
            code = int(float(code))
            for category, codes in ca_to_vn.items():
                if code in codes:
                    return category
        except (ValueError, TypeError):
            pass
        return "Others"

    age_groups = ["15 to 34 years", "35 to 54 years", "55 to 64 years", "65 years and over"]

    # --------------------------------------------------------------------------
    # 4. TRANSFORMATION AND STANDARDIZATION
    # --------------------------------------------------------------------------
    if not df_vn.empty:
        df_vn = df_vn.rename(columns={"ID": "person_id", "BEGIN": "minute_of_day", "Q401": "activity_group"})
        df_vn['minute_of_day'] = pd.to_numeric(df_vn['minute_of_day'], errors='coerce')
        df_vn['survey_minute'] = (df_vn['minute_of_day'] - 240) % 1440
        df_vn['activity_group'] = df_vn['activity_group'].apply(get_vn_activity)
        df_vn['gender'] = df_vn['gender'].map({1: "Male", 2: "Female"})
        df_vn['age_group'] = pd.cut(df_vn['age'], bins=[14, 34, 54, 64, 150], labels=age_groups)
        df_vn = df_vn.dropna(subset=['person_id', 'survey_minute', 'activity_group'])
    
    if not df_ca.empty:
        df_ca = df_ca.rename(columns={"PUMFID": "person_id", "STARTMIN": "minute_of_day", "TUI_01": "activity_group", "GENDER2": "gender", "AGEGR10": "age_group"})
        df_ca['minute_of_day'] = pd.to_numeric(df_ca['minute_of_day'], errors='coerce')
        df_ca['survey_minute'] = (df_ca['minute_of_day'] - 240) % 1440
        df_ca['activity_group'] = df_ca['activity_group'].apply(map_ca_activity)
        df_ca['gender'] = df_ca['gender'].map({1.0: "Male", 2.0: "Female"})
        ca_age_map = {1.0: "15 to 34 years", 2.0: "15 to 34 years", 
                      3.0: "35 to 54 years", 4.0: "35 to 54 years", 
                      5.0: "55 to 64 years", 
                      6.0: "65 years and over", 7.0: "65 years and over"}
        df_ca['age_group'] = df_ca['age_group'].map(ca_age_map)
        df_ca = df_ca.dropna(subset=['person_id', 'survey_minute', 'activity_group'])

    return df_ca, df_vn

# ==============================================================================
# AGGREGATION TO PROBABILITIES
# ==============================================================================
def aggregate_to_probabilities(df, group_by_cols=[]):
    """
    Converts raw episode data to a minute-by-minute probability matrix.
    If data is missing or empty, generates mock data.
    """
    if df.empty:
        # Generate smooth mock data if dataset is not found
        time_index = pd.date_range("2022-01-01 04:00:00", periods=1440, freq="min")
        activities = ["Work", "Sleeping", "Eating", "Housework", "TV/Online videos", "Others"]
        res = {}
        # If group_by_cols is empty -> dict mapping activity -> 1440 values
        if not group_by_cols:
            df_mock = pd.DataFrame(index=time_index)
            for act in activities:
                df_mock[act] = np.sin(np.linspace(0, 4 * np.pi, 1440) + np.random.uniform(0, 2 * np.pi)) + 1.5
            df_mock = df_mock.div(df_mock.sum(axis=1), axis=0) * 100
            return df_mock
        else:
            # Generate mock data for each group
            mock_groups = {}
            if "gender" in group_by_cols:
                for g in ["Male", "Female"]:
                    df_mock = pd.DataFrame(index=time_index)
                    for act in activities:
                        df_mock[act] = np.sin(np.linspace(0, 4 * np.pi, 1440) + np.random.uniform(0, 2 * np.pi)) + 1.5
                    mock_groups[(g,)] = df_mock.div(df_mock.sum(axis=1), axis=0) * 100
            elif "age_group" in group_by_cols:
                for a in ["15 to 34 years", "35 to 54 years", "55 to 64 years", "65 years and over"]:
                    df_mock = pd.DataFrame(index=time_index)
                    for act in activities:
                        df_mock[act] = np.sin(np.linspace(0, 4 * np.pi, 1440) + np.random.uniform(0, 2 * np.pi)) + 1.5
                    mock_groups[(a,)] = df_mock.div(df_mock.sum(axis=1), axis=0) * 100
            return mock_groups

    # Real data processing
    # Sort by person and time
    df = df.sort_values(group_by_cols + ['person_id', 'survey_minute'])
    
    # We need to forward-fill activities for each person for every minute of the day.
    # To keep it fast, we will pivot to have persons as rows, minutes as columns
    
    def process_group(g_df):
        # Drop duplicates at same minute, keep last
        g_df = g_df.drop_duplicates(subset=['person_id', 'survey_minute'], keep='last')
        pivot = g_df.pivot(index='person_id', columns='survey_minute', values='activity_group')
        # Reindex to all 1440 minutes
        pivot = pivot.reindex(columns=range(1440))
        # Forward fill activities for each person
        pivot = pivot.ffill(axis=1)
        # Backfill initial minutes if someone started reporting after 0
        pivot = pivot.bfill(axis=1)
        
        # Calculate percentage of each activity at each minute
        # Melt to compute value counts efficiently
        counts = pivot.apply(lambda x: x.value_counts(normalize=True)) * 100
        counts = counts.fillna(0).T
        
        # Ensure all defined activities are present in columns (pad with 0)
        for act in ALL_ACTIVITIES:
            if act not in counts.columns:
                counts[act] = 0
                
        # Create proper datetime index starting from 04:00
        time_index = pd.date_range("2022-01-01 04:00:00", periods=1440, freq="min")
        counts.index = time_index
        
        # Rearrange index so the chart physically starts at 00:00 and ends at 23:59 on a single day
        counts.index = counts.index.map(lambda t: t if t.hour >= 4 else t - pd.Timedelta(days=1))
        counts = counts.sort_index()
        return counts

    if not group_by_cols:
        return process_group(df)
    else:
        results = {}
        for name, group in df.groupby(group_by_cols, observed=False):
            results[name if isinstance(name, tuple) else (name,)] = process_group(group)
        return results

def get_dashboard_data():
    """
    Returns a dictionary of all aggregated dataframes needed for the app.
    Keys: 'overview', 'gender', 'age'
    Values for 'overview': (df_ca, df_vn)
    Values for 'gender': ({ ('Male',): df_ca_m, ...}, { ('Male',): df_vn_m, ...})
    """
    df_ca, df_vn = load_and_transform_data()
    
    print("Aggregating Overview...")
    ca_overview = aggregate_to_probabilities(df_ca)
    vn_overview = aggregate_to_probabilities(df_vn)
    
    print("Aggregating by Gender...")
    ca_gender = aggregate_to_probabilities(df_ca, ['gender'])
    vn_gender = aggregate_to_probabilities(df_vn, ['gender'])
    
    print("Aggregating by Age...")
    ca_age = aggregate_to_probabilities(df_ca, ['age_group'])
    vn_age = aggregate_to_probabilities(df_vn, ['age_group'])
    
    return {
        'overview': (ca_overview, vn_overview),
        'gender': (ca_gender, vn_gender),
        'age': (ca_age, vn_age)
    }

if __name__ == "__main__":
    import pickle
    cache_path = "processed_data.pkl"
    print("Regenerating processed_data.pkl from raw survey files...")
    data = get_dashboard_data()
    with open(cache_path, "wb") as f:
        pickle.dump(data, f)
    print(f"Data successfully processed and cached to {cache_path}.")
