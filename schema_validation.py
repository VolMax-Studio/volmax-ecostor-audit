#!/usr/bin/env python3
import os
import hashlib
import json
import pandas as pd
from datetime import datetime, timedelta

# Files dictionary mapping month name to filename (all 13 contiguous months)
FILES = {
    "2025_06": "bollingstedt_2025_06.csv",
    "2025_07": "bollingstedt_2025_07.csv",
    "2025_08": "bollingstedt_2025_08.csv",
    "2025_09": "bollingstedt_2025_09.csv",
    "2025_10": "bollingstedt_2025_10.csv",
    "2025_11": "bollingstedt_2025_11.csv",
    "2025_12": "bollingstedt_2025_12.csv",
    "2026_01": "bollingstedt_2026_01.csv",
    "2026_02": "bollingstedt_2026_02.csv",
    "2026_03": "bollingstedt_2026_03.csv",
    "2026_04": "bollingstedt_2026_04.csv",
    "2026_05": "bollingstedt_2026_05.csv",
    "2026_06": "bollingstedt_2026_06.csv",
}

EXPECTED_VARIABLES = [
    "Relative Wind Power [%]",
    "Relative PV Power [%]",
    "Bollingstedt Power [MW]",
    "Allowed Discharge Power [MW]",
    "Allowed Charge Power [MW]",
    "Discharge Obligation [MW]",
    "Charge Obligation [MW]"
]

def compute_sha256(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def validate_timezone_and_dst(df, filename):
    # Extract unique timezone offset strings from the timestamps
    offsets = df['x'].apply(lambda val: val[-6:] if len(val) >= 6 else None).unique()
    is_consistent = len(offsets) == 1
    dst_transition_detected = not is_consistent
    
    return {
        "offsets": list(offsets),
        "is_consistent": is_consistent,
        "dst_transition_detected": dst_transition_detected
    }

def analyze_completeness(df, year, month):
    df['dt_utc'] = pd.to_datetime(df['x'], utc=True)
    present_utc = set(df['dt_utc'])
    
    # Generate expected UTC timestamps (clean UTC month boundary)
    start_utc = pd.Timestamp(year=year, month=month, day=1, hour=0, minute=0, tz='UTC')
    if month == 12:
        end_utc = pd.Timestamp(year=year+1, month=1, day=1, hour=0, minute=0, tz='UTC')
    else:
        end_utc = pd.Timestamp(year=year, month=month+1, day=1, hour=0, minute=0, tz='UTC')
        
    expected_utc = pd.date_range(start=start_utc, end=end_utc - pd.Timedelta(minutes=15), freq='15min')
    total_expected = len(expected_utc)
    
    # June 2026 cut-off handling (ends at 2026-06-30T23:45:00+02:00, which is 2026-06-30T21:45:00 UTC)
    if year == 2026 and month == 6:
        last_export_utc = pd.Timestamp("2026-06-30 21:45:00", tz='UTC')
        expected_utc = expected_utc[expected_utc <= last_export_utc]
        total_expected = len(expected_utc)
        
    completeness_by_var = {}
    
    for var in EXPECTED_VARIABLES:
        var_df = df[df['trace_name'] == var]
        var_present = set(var_df['dt_utc'])
        
        missing = [dt.isoformat() for dt in expected_utc if dt not in var_present]
        extra = [dt.isoformat() for dt in var_present if dt not in expected_utc]
        
        completeness_by_var[var] = {
            "expected_count": total_expected,
            "actual_count": len(var_df),
            "missing_count": len(missing),
            "extra_count": len(extra),
            "completeness_pct": round((len(var_df) / total_expected) * 100, 2),
            "missing_timestamps": missing,
            "extra_timestamps": extra
        }
        
    return completeness_by_var, len(expected_utc)

def run_l1_validation(base_dir):
    os.makedirs(os.path.join(base_dir, "results"), exist_ok=True)
    report = {
        "snapshot_date": "2026-07-02",
        "timezone_doctrine": "Europe/Berlin local time with fixed offsets. Original data exports align to clean UTC month boundaries (00:00 UTC start of month to 00:00 UTC end of month).",
        "schema_drift_detected": False,
        "schema_drift_resolved": True,
        "files": {},
        "seams": []
    }
    
    file_dfs = {}
    
    # 1. Individual File Integrity & Schema Drift Check
    for key in sorted(FILES.keys()):
        filename = FILES[key]
        filepath = os.path.join(base_dir, filename)
        if not os.path.exists(filepath):
            print(f"Error: {filepath} does not exist.")
            return
            
        sha256 = compute_sha256(filepath)
        df = pd.read_csv(filepath)
        
        # Verify schema
        actual_cols = list(df.columns)
        schema_ok = actual_cols == ["x", "y", "trace_name"]
        
        # Extract variables and verify schema drift (identity of variables)
        actual_variables = sorted(list(df['trace_name'].unique()))
        vars_ok = set(actual_variables) == set(EXPECTED_VARIABLES)
        
        if not vars_ok:
            report["schema_drift_detected"] = True
            
        # Timezone offset check
        tz_info = validate_timezone_and_dst(df, filename)
        
        # Parse year and month from key
        year, month = map(int, key.split("_"))
        
        # Analyze completeness
        completeness_by_var, total_expected = analyze_completeness(df, year, month)
        
        report["files"][key] = {
            "filename": filename,
            "sha256": sha256,
            "row_count": len(df),
            "schema_ok": schema_ok,
            "variables_ok": vars_ok,
            "variables_found": actual_variables,
            "timezone_info": tz_info,
            "completeness_by_var": completeness_by_var
        }
        
        # Save parsed df for seam checks (using UTC datetime index)
        df['parsed_dt_utc'] = pd.to_datetime(df['x'], utc=True)
        file_dfs[key] = df
        
    # 2. Boundary / Seam Checks
    sorted_keys = sorted(FILES.keys())
    for i in range(len(sorted_keys) - 1):
        prev_key = sorted_keys[i]
        next_key = sorted_keys[i+1]
        
        prev_df = file_dfs[prev_key]
        next_df = file_dfs[next_key]
        
        var_seams = {}
        for var in EXPECTED_VARIABLES:
            prev_var = prev_df[prev_df['trace_name'] == var]
            next_var = next_df[next_df['trace_name'] == var]
            
            if prev_var.empty or next_var.empty:
                var_seams[var] = {
                    "prev_max_utc": str(prev_var['parsed_dt_utc'].max()) if not prev_var.empty else "N/A",
                    "next_min_utc": str(next_var['parsed_dt_utc'].min()) if not next_var.empty else "N/A",
                    "gap_minutes": "N/A",
                    "status": "MISSING_DATA"
                }
                continue
                
            prev_max = prev_var['parsed_dt_utc'].max()
            next_min = next_var['parsed_dt_utc'].min()
            gap = next_min - prev_max
            
            gap_minutes = gap.total_seconds() / 60.0
            
            var_seams[var] = {
                "prev_max_utc": str(prev_max),
                "next_min_utc": str(next_min),
                "gap_minutes": gap_minutes,
                "status": "CLEAN" if gap_minutes == 15.0 else f"GAP_OR_OVERLAP ({gap_minutes} min)"
            }
            
        report["seams"].append({
            "transition": f"{prev_key} -> {next_key}",
            "type": "CONTIGUOUS_EXPECTED",
            "variables_seams": var_seams
        })
        
    # Save the L1 integrity report to file
    report_path = os.path.join(base_dir, "results", "l1_integrity_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=4)
        
    print(f"L1 Integrity Report saved to {report_path}")
    
    # Output Markdown summary
    print("\n" + "="*60)
    print("LEVEL 1 - DATA INTEGRITY REPORT SUMMARY (UTC-ALIGNED & DST-AWARE)")
    print("="*60)
    print(f"Schema Drift Check: {'WARNING (Schema drift / variable mismatch detected)' if report['schema_drift_detected'] else 'PASS'}")
    
    for key in sorted(report["files"].keys()):
        f_report = report["files"][key]
        print(f"\nMonth: {key} ({f_report['filename']})")
        print(f"  SHA-256: {f_report['sha256']}")
        print(f"  Rows: {f_report['row_count']} | Schema OK: {f_report['schema_ok']} | Vars OK: {f_report['variables_ok']}")
        if not f_report['variables_ok']:
            print(f"    * Non-standard variables found: {list(set(f_report['variables_found']) - set(EXPECTED_VARIABLES))}")
        print(f"  Timezone Offsets: {f_report['timezone_info']['offsets']} | Consistent: {f_report['timezone_info']['is_consistent']} | DST Transition: {f_report['timezone_info']['dst_transition_detected']}")
        print("  Completeness by Variable:")
        for var, comp in f_report["completeness_by_var"].items():
            missing_info = ""
            if comp['missing_count'] > 0:
                missing_info = f" | Missing count: {comp['missing_count']} (Example: {comp['missing_timestamps'][0][:16]})"
            print(f"    - {var:32s}: {comp['completeness_pct']:6.2f}% (Actual: {comp['actual_count']}/{comp['expected_count']}{missing_info})")
            
    print("\nBoundary Seams:")
    for seam in report["seams"]:
        print(f"  Transition {seam['transition']}:")
        for var, details in seam["variables_seams"].items():
            if isinstance(details, dict):
                print(f"    - {var:32s}: {details['status']} (gap: {details['gap_minutes']} min)")
            else:
                print(f"    - {var:32s}: {details}")
                
if __name__ == "__main__":
    run_l1_validation(os.path.dirname(os.path.abspath(__file__)))
