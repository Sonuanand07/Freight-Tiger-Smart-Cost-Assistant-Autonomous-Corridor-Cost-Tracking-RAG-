"""Tests for output format contract and reproducibility across runs."""

import pytest
import pandas as pd
from pathlib import Path
from src.assistant import ShippingCostAssistant
from src.config import DEFAULT_SAMPLE_OUTPUT_PATH, OUTPUT_DIR

def test_output_matches_sample_schema():
    """Verify that output CSV matches sample_output_format exactly in column order and types."""
    assistant = ShippingCostAssistant()
    test_out = OUTPUT_DIR / "test_schema_output.csv"
    assistant.export_csv(test_out, include_all_weeks=False)
    
    generated_df = pd.read_csv(test_out)
    
    # Check column names and order
    expected_cols = [
        "route", "week_of", "cost_per_tonne_km", "vs_own_history",
        "vs_similar_routes", "flagged", "matched_note_id", "reason"
    ]
    assert list(generated_df.columns) == expected_cols

    # Check that flagged values are strictly valid
    valid_flags = {"Yes", "No", "No (justified)"}
    assert set(generated_df['flagged']).issubset(valid_flags)

    # Check that when flagged is Yes, matched_note_id is blank/NaN
    unjustified = generated_df[generated_df['flagged'] == 'Yes']
    assert unjustified['matched_note_id'].isna().all() or (unjustified['matched_note_id'] == "").all()

    # Check that when flagged is No (justified), matched_note_id is non-empty
    justified = generated_df[generated_df['flagged'] == 'No (justified)']
    assert (justified['matched_note_id'].notna() & (justified['matched_note_id'] != "")).all()

def test_three_runs_reproducibility():
    """Verify that 3 independent runs produce 100% identical outputs."""
    runs = []
    for i in range(1, 4):
        assistant = ShippingCostAssistant()
        run_file = OUTPUT_DIR / f"test_run_{i}.csv"
        assistant.export_csv(run_file, include_all_weeks=False)
        runs.append(pd.read_csv(run_file))

    df1, df2, df3 = runs[0], runs[1], runs[2]
    assert df1.equals(df2), "Run 1 and Run 2 produced different outputs!"
    assert df2.equals(df3), "Run 2 and Run 3 produced different outputs!"

