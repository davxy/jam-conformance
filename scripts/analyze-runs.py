import os
import json
import glob
import statistics

# --- CONFIGURATION ---
SESSIONS_DIR = "./sessions"
TARGET_STEPS_PER_RUN = 100000   # Goal per runner
TOTAL_STEPS_GOAL = 1000000      # 1 Million steps total (effort)
# ---------------------

def get_trace_count_from_files(trace_dir):
    """
    Fallback: Scans the trace directory for the highest numbered .bin file.
    This tells us 'Imported', but NOT 'Steps'.
    """
    if not os.path.exists(trace_dir):
        return 0
    
    max_block = 0
    files = os.listdir(trace_dir)
    
    for f in files:
        if f.endswith(".bin") and f != "report.bin":
            try:
                # remove .bin and convert to int
                num = int(f.replace(".bin", ""))
                if num > max_block:
                    max_block = num
            except ValueError:
                continue
                
    return max_block

def analyze_session(session_path):
    trace_id = os.path.basename(session_path)
    report_path = os.path.join(session_path, "report", "report.json")
    trace_dir = os.path.join(session_path, "trace")
    
    data = {
        "id": trace_id,
        "steps": 0,
        "imported": 0,
        "source": "UNKNOWN",
        "error": None
    }

    # 1. Try to read the JSON Report
    if os.path.exists(report_path):
        try:
            with open(report_path, 'r') as f:
                report = json.load(f)
                stats = report.get("stats", {})
                
                data["steps"] = stats.get("steps", 0)
                data["imported"] = stats.get("imported", 0)
                data["error"] = report.get("error")
                data["source"] = "Report"
                return data
        except Exception as e:
            data["error"] = f"JSON Parse Error: {str(e)}"

    # 2. Fallback: Count trace files if report failed or doesn't exist
    if os.path.exists(trace_dir):
        highest_block = get_trace_count_from_files(trace_dir)
        if highest_block > 0:
            data["imported"] = highest_block
            data["steps"] = 0  # We cannot guess steps from file counts
            data["source"] = "Trace (Fallback)"
            if not data["error"]: 
                data["error"] = "No Report (Steps Unknown)"
    
    return data

def main():
    if not os.path.exists(SESSIONS_DIR):
        print(f"Error: Directory '{SESSIONS_DIR}' not found.")
        return

    # Find all session directories
    session_paths = [f.path for f in os.scandir(SESSIONS_DIR) if f.is_dir()]
    session_paths.sort()

    results = []
    
    # Header
    print(f"{'TRACE ID':<25} | {'STEPS':<10} | {'IMPORTED':<10} | {'SOURCE':<18} | {'STATUS'}")
    print("-" * 95)

    for path in session_paths:
        res = analyze_session(path)
        results.append(res)
        
        # Formatting status
        error_msg = str(res['error']) if res['error'] else "✅ Success"
        if len(error_msg) > 25: error_msg = error_msg[:22] + "..."
        
        # Add visual flag if steps are below target (and we have a report)
        step_str = f"{res['steps']:,}"
        if res['source'] == "Report" and res['steps'] < TARGET_STEPS_PER_RUN:
            step_str += " ⚠️"

        print(f"{res['id']:<25} | {step_str:<10} | {res['imported']:<10,} | {res['source']:<18} | {error_msg}")

    print("-" * 95)

    # --- STATISTICS & BENCHMARK ---
    total_steps = sum(r['steps'] for r in results)
    total_imported = sum(r['imported'] for r in results)
    
    # Only calculate import stats based on runs that actually have data
    import_counts = [r['imported'] for r in results if r['imported'] > 0]
    
    if not results:
        print("No sessions found.")
        return

    progress_steps = (total_steps / TOTAL_STEPS_GOAL) * 100
    
    print("\n📊 --- FINAL SUMMARY ---")
    print(f"Total Runs Analyzed:   {len(results)}")
    print(f"Total Steps Completed: {total_steps:,} / {TOTAL_STEPS_GOAL:,} ({progress_steps:.2f}%)")
    print(f"Total Blocks Imported: {total_imported:,}")
    print("-" * 30)

    if import_counts:
        print(f"Avg Imported/Run:      {statistics.mean(import_counts):,.2f}")
        print(f"Min Imported:          {min(import_counts):,}")
        print(f"Max Imported:          {max(import_counts):,}")
    else:
        print("No blocks imported yet.")

    print("-" * 30)
    
    # Final Verdict
    if total_steps >= TOTAL_STEPS_GOAL:
        print("🎉 BENCHMARK PASSED: Generated 1 Million+ Steps.")
    else:
        missing = TOTAL_STEPS_GOAL - total_steps
        print(f"⚠️  BENCHMARK FAILED: Missing {missing:,} steps.")

if __name__ == "__main__":
    main()
