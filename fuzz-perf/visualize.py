#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from typing import Dict, Any, Tuple

# Implementation language mapping based on official JAM clients list
# Source: https://graypaper.com/clients/
IMPLEMENTATION_LANGUAGES = {
    'boka': 'Swift',
    'fastroll': 'Rust',
    'gossamer': 'Go',
    'jamduna': 'Go',
    'jampy': 'Python',
    'tsjam': 'TS',
    'jamixir': 'Elixir',
    'jamzig': 'Zig',
    'jamzilla': 'Go',
    'javajam': 'Java',
    'polkajam': 'Rust',
    'polkajam-int': 'Rust',
    'pyjamaz': 'Python',
    'spacejam': 'Rust',
    'strawberry': 'Go',
    'turbojam': 'C++',
    'vinwolf': 'Rust',
    'tessera': 'Python',
    'typeberry': 'Go',
    'new-jamneration': 'Go',
    'jamforge': 'Scala',
    'graymatter': 'Elixir'
}

def load_json_reports(base_path: str = ".") -> Dict[str, Dict[str, Any]]:
    """Load all performance JSON reports from the directory structure."""
    reports = {}
    base = Path(base_path)
    
    if not base.exists():
        print(f"Error: Directory {base_path} not found")
        return {}
    
    for impl_dir in base.iterdir():
        if not impl_dir.is_dir():
            continue
        impl_name = impl_dir.name
        reports[impl_name] = {}
        for json_file in impl_dir.glob("*.json"):
            test_name = json_file.stem
            try:
                with open(json_file, 'r') as f:
                    reports[impl_name][test_name] = json.load(f)
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
        'Rust': '\033[38;5;208m',       # Orange
        'Rust (i)': '\033[38;5;214m',   # Light Orange
        'Zig': '\033[38;5;46m',         # Green
        'Python': '\033[38;5;33m',      # Blue
        'Java': '\033[38;5;196m',       # Red
        'TS': '\033[38;5;39m',          # Cyan
        'Go': '\033[38;5;51m',          # Light Blue
        'C++': '\033[38;5;201m',        # Magenta
        'Swift': '\033[38;5;213m',      # Pink
        'Elixir': '\033[38;5;129m',     # Purple
        'Unknown': '\033[38;5;240m',    # Gray
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
    print("  OVERALL PERFORMANCE COMPARISON (Average Across All Tests)")
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
    parser = argparse.ArgumentParser(
        description="Visualize JAM implementation performance reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  visualize_perf_enhanced.py --overall
  visualize_perf_enhanced.py --test storage
  visualize_perf_enhanced.py --impl boka
  visualize_perf_enhanced.py --path fuzz-reports/0.6.7/reports"""
    )
    
    parser.add_argument("-o", "--overall", action="store_true",
                       help="Show overall average performance across all tests")
    parser.add_argument("-t", "--test", default="safrole",
                       help="Show comparison for specific test (default: safrole)")
    parser.add_argument("-i", "--impl",
                       help="Show detailed stats for specific implementation")
    parser.add_argument("-a", "--all", action="store_true",
                       help="Show all available tests")
    parser.add_argument("-p", "--path", default="./",
                       help="Specify base path for reports (default: current directory)")
    
    args = parser.parse_args()
    
    # Load all reports
    reports = load_json_reports(args.path)
    
    if not reports:
        print("No performance reports found!")
        return
    
    # Show requested information
    if args.overall:
        print_overall_comparison(reports)
    elif args.impl:
        print_detailed_stats(reports, args.impl)
    elif args.all:
        # Get all test types
        all_tests = set()
        for impl_tests in reports.values():
            all_tests.update(impl_tests.keys())
        
        for test in sorted(all_tests):
            print_comparison_chart(reports, test)
        
        # Also show overall at the end
        print_overall_comparison(reports)
    else:
        print_comparison_chart(reports, args.test)
        
        # Print summary
        print("\n  Summary:")
        print("  " + "-"*40)
        print(f"  Total implementations: {len(reports)}")
        
        # Find best performer
        best_impl = None
        best_mean = float('inf')
        
        for impl_name, tests in reports.items():
            if args.test in tests and 'stats' in tests[args.test]:
                mean = tests[args.test]['stats'].get('import_mean', float('inf'))
                if mean < best_mean:
                    best_mean = mean
                    best_impl = impl_name
        
        if best_impl:
            lang = IMPLEMENTATION_LANGUAGES.get(best_impl, 'Unknown')
            print(f"  Best performer ({args.test}): {best_impl} ({lang}) - {format_time(best_mean)}")
        
        print("\n  Tip: Use --overall to see average performance across all tests")
        print("       Use --help for more options")

if __name__ == "__main__":
    main()
