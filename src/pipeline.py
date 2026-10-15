"""Core data processing and baseline computation pipeline."""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Tuple
from src.config import AnomalyConfig, DEFAULT_SHIPMENTS_PATH

class CostPipeline:
    def __init__(self, config: Optional[AnomalyConfig] = None):
        self.config = config or AnomalyConfig()

    def load_data(self, csv_path: Path = DEFAULT_SHIPMENTS_PATH) -> pd.DataFrame:
        """Load shipment records from CSV and validate essential columns."""
        df = pd.read_csv(csv_path)
        required_cols = [
            'shipment_id', 'origin', 'destination', 'route_type',
            'quantity_tonnes', 'distance_km', 'freight_cost_inr', 'shipment_date'
        ]
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column in shipments data: {col}")
        
        df['shipment_date'] = pd.to_datetime(df['shipment_date'])
        df['route'] = df['origin'].str.strip() + '-' + df['destination'].str.strip()
        df['route_type'] = df['route_type'].str.strip()
        
        # Calculate week_of (Monday of that week)
        df['week_of'] = df['shipment_date'].apply(lambda d: d - pd.Timedelta(days=d.weekday()))
        return df

    def aggregate_weekly_corridors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Group by route, route_type, and week_of.
        cost_per_tonne_km = total freight cost / (quantity in tonnes * distance in km)
        """
        # Sum total cost and total tonne-km per route-week
        agg = df.groupby(['route', 'route_type', 'week_of']).apply(
            lambda g: pd.Series({
                'total_freight_cost': g['freight_cost_inr'].sum(),
                'total_tonne_km': (g['quantity_tonnes'] * g['distance_km']).sum(),
                'shipment_count': len(g)
            })
        ).reset_index()

        agg['cost_per_tonne_km'] = agg['total_freight_cost'] / agg['total_tonne_km']
        agg = agg.sort_values(['route', 'week_of']).reset_index(drop=True)
        return agg

    def compute_baselines(self, agg: pd.DataFrame) -> pd.DataFrame:
        """
        Compute baseline comparisons:
        1. vs own history: trailing 8-week rolling average cost per tonne-km, strictly prior weeks.
        2. vs similar routes: average cost per tonne-km in same week across other routes of same route_type.
        """
        window = self.config.trailing_weeks_window
        results = []

        # 1. Trailing rolling average per route
        for (route, rtype), r_df in agg.groupby(['route', 'route_type']):
            r_df = r_df.sort_values('week_of').reset_index(drop=True)
            for i, row in r_df.iterrows():
                # Strictly prior weeks up to window size (no look-ahead)
                prior_slice = r_df.iloc[max(0, i - window):i]
                prior_count = len(prior_slice)
                
                if prior_count > 0:
                    hist_mean = prior_slice['cost_per_tonne_km'].mean()
                else:
                    hist_mean = np.nan

                results.append({
                    'route': route,
                    'route_type': rtype,
                    'week_of': row['week_of'],
                    'cost_per_tonne_km': row['cost_per_tonne_km'],
                    'shipment_count': row['shipment_count'],
                    'prior_weeks_available': prior_count,
                    'hist_mean': hist_mean
                })

        df_metrics = pd.DataFrame(results)

        # 2. Peer route average (same week, same route_type, excluding the route itself)
        peer_results = []
        for (rtype, w), w_df in df_metrics.groupby(['route_type', 'week_of']):
            for _, row in w_df.iterrows():
                other_routes = w_df[w_df['route'] != row['route']]
                if len(other_routes) > 0:
                    peer_mean = other_routes['cost_per_tonne_km'].mean()
                else:
                    peer_mean = np.nan
                peer_results.append((row['route'], row['week_of'], peer_mean))

        peer_df = pd.DataFrame(peer_results, columns=['route', 'week_of', 'peer_mean'])
        df_metrics = pd.merge(df_metrics, peer_df, on=['route', 'week_of'])

        # Calculate percentage differences
        df_metrics['pct_vs_own'] = np.where(
            df_metrics['hist_mean'].notna() & (df_metrics['hist_mean'] > 0),
            ((df_metrics['cost_per_tonne_km'] - df_metrics['hist_mean']) / df_metrics['hist_mean']) * 100.0,
            np.nan
        )

        df_metrics['pct_vs_peer'] = np.where(
            df_metrics['peer_mean'].notna() & (df_metrics['peer_mean'] > 0),
            ((df_metrics['cost_per_tonne_km'] - df_metrics['peer_mean']) / df_metrics['peer_mean']) * 100.0,
            np.nan
        )

        # Formatted string columns matching sample output
        df_metrics['vs_own_history'] = df_metrics['pct_vs_own'].apply(
            lambda x: f"{x:+.1f}% vs this route's past average" if pd.notna(x) else "N/A (insufficient prior history)"
        )

        df_metrics['vs_similar_routes'] = df_metrics['pct_vs_peer'].apply(
            lambda x: f"{x:+.1f}% vs similar-length routes this week" if pd.notna(x) else "N/A (no peer routes)"
        )

        # Anomaly candidate criteria
        own_th = self.config.own_history_threshold_pct
        peer_th = self.config.similar_routes_threshold_pct
        
        # Rising and looks out of the ordinary compared to history OR similar routes
        df_metrics['is_candidate'] = (
            (df_metrics['pct_vs_own'] > 0) & 
            ((df_metrics['pct_vs_own'] >= own_th) | (df_metrics['pct_vs_peer'] >= peer_th))
        )

        return df_metrics

    def run(self, csv_path: Path = DEFAULT_SHIPMENTS_PATH) -> pd.DataFrame:
        """Run full data loading, weekly aggregation, and baseline computations."""
        raw_df = self.load_data(csv_path)
        agg_df = self.aggregate_weekly_corridors(raw_df)
        metrics_df = self.compute_baselines(agg_df)
        return metrics_df

