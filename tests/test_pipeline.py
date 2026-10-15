"""Unit tests for the data pipeline and baseline computations."""

import pytest
import pandas as pd
import numpy as np
from src.pipeline import CostPipeline
from src.config import AnomalyConfig, DEFAULT_SHIPMENTS_PATH

@pytest.fixture
def pipeline():
    return CostPipeline(AnomalyConfig())

@pytest.fixture
def processed_df(pipeline):
    return pipeline.run(DEFAULT_SHIPMENTS_PATH)

def test_week_of_is_monday(pipeline):
    """Test that all grouped week_of dates are strictly Mondays."""
    df = pipeline.load_data(DEFAULT_SHIPMENTS_PATH)
    weekdays = df['week_of'].dt.weekday.unique()
    assert len(weekdays) == 1
    assert weekdays[0] == 0, "week_of must always be Monday (weekday 0)"

def test_cost_per_tonne_km_formula(pipeline):
    """Verify cost_per_tonne_km = sum(cost) / sum(quantity * distance)."""
    df = pipeline.load_data(DEFAULT_SHIPMENTS_PATH)
    agg = pipeline.aggregate_weekly_corridors(df)
    
    # Check for Delhi-Jaipur on 2024-11-11 (sample ground truth: 4.17)
    dj_sample = agg[(agg['route'] == 'Delhi-Jaipur') & (agg['week_of'] == '2024-11-11')].iloc[0]
    expected_cost = round(dj_sample['total_freight_cost'] / dj_sample['total_tonne_km'], 2)
    assert round(dj_sample['cost_per_tonne_km'], 2) == 4.17
    assert expected_cost == 4.17

def test_sample_output_ground_truth_delhi_jaipur(processed_df):
    """Check Delhi-Jaipur 2024-11-11 exact baseline matches."""
    row = processed_df[(processed_df['route'] == 'Delhi-Jaipur') & (processed_df['week_of'] == '2024-11-11')].iloc[0]
    assert round(row['cost_per_tonne_km'], 2) == 4.17
    assert round(row['pct_vs_own'], 1) == 35.5
    assert round(row['pct_vs_peer'], 1) == 21.0
    assert row['vs_own_history'] == "+35.5% vs this route's past average"
    assert row['vs_similar_routes'] == "+21.0% vs similar-length routes this week"

def test_sample_output_ground_truth_ahmedabad_mumbai(processed_df):
    """Check Ahmedabad-Mumbai 2025-01-20 exact baseline matches."""
    row = processed_df[(processed_df['route'] == 'Ahmedabad-Mumbai') & (processed_df['week_of'] == '2025-01-20')].iloc[0]
    assert round(row['cost_per_tonne_km'], 2) == 3.29
    assert round(row['pct_vs_own'], 1) == 29.5
    assert round(row['pct_vs_peer'], 1) == 22.5
    assert row['vs_own_history'] == "+29.5% vs this route's past average"
    assert row['vs_similar_routes'] == "+22.5% vs similar-length routes this week"

def test_sample_output_ground_truth_mumbai_pune(processed_df):
    """Check Mumbai-Pune 2025-09-15 exact baseline matches."""
    row = processed_df[(processed_df['route'] == 'Mumbai-Pune') & (processed_df['week_of'] == '2025-09-15')].iloc[0]
    assert round(row['cost_per_tonne_km'], 2) == 3.98
    assert round(row['pct_vs_own'], 1) == 9.2
    assert round(row['pct_vs_peer'], 1) == 23.6
    assert row['vs_own_history'] == "+9.2% vs this route's past average"
    assert row['vs_similar_routes'] == "+23.6% vs similar-length routes this week"

def test_no_lookahead_bias(processed_df):
    """Ensure trailing rolling average uses only strictly prior weeks."""
    for (route, _), r_df in processed_df.groupby(['route', 'route_type']):
        r_df = r_df.sort_values('week_of').reset_index(drop=True)
        # Week 0 must have np.nan for hist_mean since 0 prior weeks exist
        assert pd.isna(r_df.iloc[0]['hist_mean'])
        assert r_df.iloc[0]['prior_weeks_available'] == 0
        
        # Week 1 must have exactly 1 prior week
        assert r_df.iloc[1]['prior_weeks_available'] == 1
        assert abs(r_df.iloc[1]['hist_mean'] - r_df.iloc[0]['cost_per_tonne_km']) < 1e-6

