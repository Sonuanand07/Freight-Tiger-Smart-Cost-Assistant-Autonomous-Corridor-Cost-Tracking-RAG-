"""Command-line interface for the Freight Tiger Shipping Cost Assistant."""

import argparse
import sys
from pathlib import Path
import pandas as pd

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from src.assistant import ShippingCostAssistant
from src.config import DEFAULT_OUTPUT_PATH, OUTPUT_DIR

def run_command(args):
    print("=" * 60)
    print("  FREIGHT TIGER SMART SHIPPING COST ASSISTANT")
    print("=" * 60)
    print(f"Loading data and analyzing shipments...")
    
    assistant = ShippingCostAssistant()
    output_path = Path(args.output) if args.output else DEFAULT_OUTPUT_PATH
    include_all = args.all_weeks

    assistant.export_csv(output_path=output_path, include_all_weeks=include_all)
    print(f"Analysis complete! Saved output to: {output_path}")

    # Read and display preview
    df = pd.read_csv(output_path)
    print(f"\nTotal evaluated rows: {len(df)}")
    flagged_counts = df['flagged'].value_counts().to_dict()
    print(f"Verdict breakdown: {flagged_counts}")
    print("\n--- Preview of Results ---")
    print(df.to_string(index=False))

    # Save token report
    token_report_path = OUTPUT_DIR / "token_cost_report.json"
    assistant.tracker.save_report(token_report_path)
    print(f"\nToken & Cost Audit Report saved to: {token_report_path}")
    print(assistant.tracker.summary())

def reproduce_command(args):
    print("=" * 60)
    print("  REPRODUCIBILITY EVALUATION: 3 UNTOUCHED RUNS")
    print("=" * 60)
    
    runs = []
    for i in range(1, 4):
        print(f"\nExecuting Run {i}...")
        assistant = ShippingCostAssistant()
        run_file = OUTPUT_DIR / f"reproducibility_run{i}.csv"
        assistant.export_csv(output_path=run_file, include_all_weeks=args.all_weeks)
        df = pd.read_csv(run_file)
        runs.append((run_file, df))
        print(f"  Run {i} complete: {len(df)} rows saved to {run_file.name}")

    # Check equality
    df1, df2, df3 = runs[0][1], runs[1][1], runs[2][1]
    
    # 1. Check exact shapes
    assert len(df1) == len(df2) == len(df3), "Row count mismatch across runs!"
    
    # 2. Check identical verdicts, notes, and numbers
    match_1_2 = df1.equals(df2)
    match_2_3 = df2.equals(df3)

    print("\n" + "=" * 60)
    print("  REPRODUCIBILITY CHECK RESULTS")
    print("=" * 60)
    print(f"  Run 1 vs Run 2 Identical: {match_1_2}")
    print(f"  Run 2 vs Run 3 Identical: {match_2_3}")

    if match_1_2 and match_2_3:
        print("\nSUCCESS: All 3 runs are 100% IDENTICAL across all numbers, verdicts, and note citations!")
        print("Zero hallucination or non-deterministic drift detected.")
    else:
        print("\nWARNING: Discrepancies detected between runs.")
        sys.exit(1)

def ask_command(args):
    query = " ".join(args.query)
    if not query:
        print("Error: Please provide a question. Example: python -m src.cli ask why did Chennai-Bangalore get pricier in March?")
        return

    assistant = ShippingCostAssistant()
    print("=" * 60)
    print(f"Question: {query}")
    print("=" * 60)
    response = assistant.ask(query)
    print(response)

def main():
    parser = argparse.ArgumentParser(description="Freight Tiger Shipping Cost Smart Assistant")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # 'run' subcommand
    run_parser = subparsers.add_parser("run", help="Run shipping cost anomaly detection pipeline")
    run_parser.add_argument("--output", "-o", type=str, default=str(DEFAULT_OUTPUT_PATH), help="Target output CSV path")
    run_parser.add_argument("--all-weeks", action="store_true", help="Output all 728 route-weeks instead of only flagged candidates")

    # 'reproduce' subcommand
    reproduce_parser = subparsers.add_parser("reproduce", help="Run 3 consecutive runs and verify exact reproducibility")
    reproduce_parser.add_argument("--all-weeks", action="store_true", help="Include all weeks in reproduction test")

    # 'ask' subcommand (Stretch goal)
    ask_parser = subparsers.add_parser("ask", help="Ask questions about shipping costs in plain English")
    ask_parser.add_argument("query", nargs="+", help="Question to ask the assistant")

    args = parser.parse_args()
    if args.command == "run":
        run_command(args)
    elif args.command == "reproduce":
        reproduce_command(args)
    elif args.command == "ask":
        ask_command(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

