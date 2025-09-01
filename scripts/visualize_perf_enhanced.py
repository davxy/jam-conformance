#!/usr/bin/env python3

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
import math

# Implementation language mapping based on official JAM clients list
# Source: https://graypaper.com/clients/
IMPLEMENTATION_LANGUAGES = {
    'jamzig': 'Zig',        # JamZig (confirmed)
    'jamzilla': 'Go',       # Jamzilla (confirmed)
    'javajam': 'Java',      # JavaJAM (confirmed)
    'pyjamaz': 'Python',    # PyJAMaz (confirmed)
    'jampy': 'Python',      # Jampy (confirmed)
    'jamts': 'TS',          # Likely TSJam or similar TypeScript client
    'turbojam': 'C++',      # TurboJam C++ implementation
    'polkajam': 'Rust',     # PolkaJam (confirmed)
    'polkajam_int': 'Rust (int)',  # PolkaJam interpreted mode
    'boka': 'Swift',        # Boka (confirmed)
    'spacejam': 'Rust',     # SpaceJam (confirmed)
    'vinwolf': 'Rust',      # Vinwolf (confirmed)
    'jamduna': 'Go',        # JAM DUNA (confirmed)
}

def load_json_reports(base_path: str = "fuzz-reports/0.7.0/reports") -> Dict[str, Dict[str, Any]]:
    """Load all performance JSON reports from the directory structure."""
    reports = {}
    base = Path(base_path)
    
    if not base.exists():
        print(f"Error: Directory {base_path} not found")
        return {}
    
    for impl_dir in base.iterdir():
        if impl_dir.is_dir():
            impl_name = impl_dir.name
            perf_dir = impl_dir / "perf"
            
            if perf_dir.exists():
                reports[impl_name] = {}
                for json_file in perf_dir.glob("*.json"):
                    test_name = json_file.stem
                    try:
                        with open(json_file, 'r') as f:
                            reports[impl_name][test_name] = json.load(f)
                    except Exception as e:
                        print(f"Error reading {json_file}: {e}")
            
            # Special case for polkajam's interpreted performance results
            if impl_name == "polkajam":
                perf_int_dir = impl_dir / "perf_int"
                if perf_int_dir.exists():
                    reports["polkajam_int"] = {}
                    for json_file in perf_int_dir.glob("*.json"):
                        test_name = json_file.stem
                        try:
                            with open(json_file, 'r') as f:
                                reports["polkajam_int"][test_name] = json.load(f)
                        except Exception as e:
                            print(f"Error reading {json_file}: {e}")
    
    return reports

def create_bar(value: float, max_value: float, width: int = 50) -> str:
    """Create a terminal bar chart representation."""
    if max_value == 0:
        return ""
    
    filled = int((value / max_value) * width)
    bar = "█" * filled + "░" * (width - filled)
    return bar

def format_time(ms: float) -> str:
    """Format milliseconds for display."""
    if ms < 1:
        return f"{ms*1000:.2f}μs"
    elif ms < 1000:
        return f"{ms:.2f}ms"
    else:
        return f"{ms/1000:.2f}s"

def get_language_color(lang: str) -> str:
    """Return ANSI color code for language (for terminal display)."""
    colors = {
        'Rust': '\033[38;5;208m',     # Orange
        'Rust (int)': '\033[38;5;214m', # Light Orange
        'Zig': '\033[38;5;46m',       # Green
        'Python': '\033[38;5;33m',    # Blue
        'Java': '\033[38;5;196m',     # Red
        'TS': '\033[38;5;39m',        # Cyan
        'Go': '\033[38;5;51m',        # Light Blue
        'C++': '\033[38;5;201m',       # Magenta
        'Swift': '\033[38;5;213m',     # Pink
        'Unknown': '\033[38;5;240m',  # Gray
    }
    return colors.get(lang, '\033[0m')

def calculate_overall_average(reports: Dict[str, Dict[str, Any]]) -> Dict[str, Tuple[float, str]]:
    """Calculate overall average performance across all tests for each implementation."""
    overall_stats = {}
    
    for impl_name, tests in reports.items():
        total_mean = 0
        test_count = 0
        
        for test_type, data in tests.items():
            if 'stats' in data and 'import_mean' in data['stats']:
                mean = data['stats']['import_mean']
                if mean > 0:
                    total_mean += mean
                    test_count += 1
        
        if test_count > 0:
            avg_mean = total_mean / test_count
            language = IMPLEMENTATION_LANGUAGES.get(impl_name, 'Unknown')
            overall_stats[impl_name] = (avg_mean, language)
    
    return overall_stats

def print_overall_comparison(reports: Dict[str, Dict[str, Any]]):
    """Print overall performance comparison across all tests."""
    
    print(f"\n{'='*90}")
    print(f"  OVERALL PERFORMANCE COMPARISON (Average Across All Tests)")
    print(f"{'='*90}\n")
    
    overall_stats = calculate_overall_average(reports)
    
    if not overall_stats:
        print("No data available for overall comparison")
        return
    
    # Sort by average performance (lower is better)
    sorted_impls = sorted(overall_stats.items(), key=lambda x: x[1][0])
    
    # Find max value for bar scaling
    max_avg = max(stat[0] for stat in overall_stats.values())
    
    # Print header
    print("  Implementation    Language       Avg Time    Relative    Graph")
    print("  " + "-"*86)
    
    # Get best performer for relative comparison
    best_time = sorted_impls[0][1][0] if sorted_impls else 1
    
    # Print each implementation
    for impl_name, (avg_time, language) in sorted_impls:
        relative = avg_time / best_time
        bar = create_bar(avg_time, max_avg, 35)
        lang_color = get_language_color(language)
        reset_color = '\033[0m'
        
        print(f"  {impl_name:15} {lang_color}{language:12}{reset_color} {format_time(avg_time):>12}   {relative:>6.2f}x  {bar}")
    
    print()
    
    # Language summary
    print("  Language Performance Summary:")
    print("  " + "-"*50)
    
    # Group by language
    lang_stats = {}
    for impl_name, (avg_time, language) in overall_stats.items():
        if language not in lang_stats:
            lang_stats[language] = []
        lang_stats[language].append((impl_name, avg_time))
    
    # Calculate average per language
    lang_avgs = {}
    for lang, impls in lang_stats.items():
        avg = sum(time for _, time in impls) / len(impls)
        lang_avgs[lang] = (avg, len(impls))
    
    # Sort languages by average performance
    sorted_langs = sorted(lang_avgs.items(), key=lambda x: x[1][0])
    
    for lang, (avg_time, count) in sorted_langs:
        lang_color = get_language_color(lang)
        reset_color = '\033[0m'
        implementations = [name for name, _ in lang_stats[lang]]
        impl_list = ", ".join(implementations)
        print(f"  {lang_color}{lang:12}{reset_color} {format_time(avg_time):>12} ({count} impl{'s' if count > 1 else ''}): {impl_list}")

def print_comparison_chart(reports: Dict[str, Dict[str, Any]], test_type: str = "safrole"):
    """Print a comparison chart for a specific test type across implementations."""
    
    print(f"\n{'='*90}")
    print(f"  PERFORMANCE COMPARISON: {test_type.upper()}")
    print(f"{'='*90}\n")
    
    # Collect data for the specific test type
    impl_data = {}
    max_mean = 0
    
    for impl_name, tests in reports.items():
        if test_type in tests and 'stats' in tests[test_type]:
            stats = tests[test_type]['stats']
            if 'import_mean' in stats and stats['import_mean'] > 0:
                impl_data[impl_name] = stats
                max_mean = max(max_mean, stats['import_mean'])
    
    if not impl_data:
        print(f"No data available for test type: {test_type}")
        return
    
    # Sort by mean performance (lower is better)
    sorted_impls = sorted(impl_data.items(), key=lambda x: x[1]['import_mean'])
    
    # Print header
    print("  Implementation   Lang     Mean Time       P50         P90         P99        Graph")
    print("  " + "-"*84)
    
    # Print each implementation
    for impl_name, stats in sorted_impls:
        mean = stats.get('import_mean', 0)
        p50 = stats.get('import_p50', 0)
        p90 = stats.get('import_p90', 0)
        p99 = stats.get('import_p99', 0)
        language = IMPLEMENTATION_LANGUAGES.get(impl_name, 'Unknown')
        lang_color = get_language_color(language)
        reset_color = '\033[0m'
        
        bar = create_bar(mean, max_mean, 25)
        
        print(f"  {impl_name:15} {lang_color}{language:6}{reset_color} {format_time(mean):>12} {format_time(p50):>10} {format_time(p90):>10} {format_time(p99):>10}  {bar}")
    
    print()

def print_detailed_stats(reports: Dict[str, Dict[str, Any]], impl_name: str):
    """Print detailed statistics for a specific implementation."""
    
    if impl_name not in reports:
        print(f"Implementation '{impl_name}' not found")
        return
    
    language = IMPLEMENTATION_LANGUAGES.get(impl_name, 'Unknown')
    lang_color = get_language_color(language)
    reset_color = '\033[0m'
    
    print(f"\n{'='*80}")
    print(f"  DETAILED STATS: {impl_name.upper()} ({lang_color}{language}{reset_color})")
    print(f"{'='*80}\n")
    
    for test_type, data in reports[impl_name].items():
        if 'stats' in data:
            stats = data['stats']
            print(f"  Test: {test_type}")
            print(f"  " + "-"*40)
            print(f"  Steps:     {stats.get('steps', 'N/A')}")
            print(f"  Imported:  {stats.get('imported', 'N/A')}")
            print(f"  Min:       {format_time(stats.get('import_min', 0))}")
            print(f"  Max:       {format_time(stats.get('import_max', 0))}")
            print(f"  Mean:      {format_time(stats.get('import_mean', 0))}")
            print(f"  Std Dev:   {format_time(stats.get('import_std_dev', 0))}")
            print(f"  P50:       {format_time(stats.get('import_p50', 0))}")
            print(f"  P75:       {format_time(stats.get('import_p75', 0))}")
            print(f"  P90:       {format_time(stats.get('import_p90', 0))}")
            print(f"  P99:       {format_time(stats.get('import_p99', 0))}")
            print()

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print("Usage: python visualize_perf_enhanced.py [options]")
            print("\nOptions:")
            print("  --overall         Show overall average performance across all tests")
            print("  --test TYPE       Show comparison for specific test (default: safrole)")
            print("  --impl NAME       Show detailed stats for specific implementation")
            print("  --all             Show all available tests")
            print("\nExamples:")
            print("  python visualize_perf_enhanced.py --overall")
            print("  python visualize_perf_enhanced.py --test storage")
            print("  python visualize_perf_enhanced.py --impl boka")
            return
    
    # Load all reports
    reports = load_json_reports()
    
    if not reports:
        print("No performance reports found!")
        return
    
    # Parse command line arguments
    test_type = "safrole"
    show_overall = False
    impl_detail = None
    show_all = False
    
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--test" and i + 1 < len(sys.argv):
            test_type = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--impl" and i + 1 < len(sys.argv):
            impl_detail = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--overall":
            show_overall = True
            i += 1
        elif sys.argv[i] == "--all":
            show_all = True
            i += 1
        else:
            i += 1
    
    # Show requested information
    if show_overall:
        print_overall_comparison(reports)
    elif impl_detail:
        print_detailed_stats(reports, impl_detail)
    elif show_all:
        # Get all test types
        all_tests = set()
        for impl_tests in reports.values():
            all_tests.update(impl_tests.keys())
        
        for test in sorted(all_tests):
            print_comparison_chart(reports, test)
        
        # Also show overall at the end
        print_overall_comparison(reports)
    else:
        print_comparison_chart(reports, test_type)
        
        # Print summary
        print("\n  Summary:")
        print("  " + "-"*40)
        print(f"  Total implementations: {len(reports)}")
        
        # Find best performer
        best_impl = None
        best_mean = float('inf')
        
        for impl_name, tests in reports.items():
            if test_type in tests and 'stats' in tests[test_type]:
                mean = tests[test_type]['stats'].get('import_mean', float('inf'))
                if mean < best_mean:
                    best_mean = mean
                    best_impl = impl_name
        
        if best_impl:
            lang = IMPLEMENTATION_LANGUAGES.get(best_impl, 'Unknown')
            print(f"  Best performer ({test_type}): {best_impl} ({lang}) - {format_time(best_mean)}")
        
        print("\n  Tip: Use --overall to see average performance across all tests")
        print("       Use --help for more options")

if __name__ == "__main__":
    main()