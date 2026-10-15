"""Smart Shipping Cost Assistant coordinator and natural language Q&A interface."""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
import csv
import re

from src.config import (
    DEFAULT_SHIPMENTS_PATH, DEFAULT_NOTES_PATH, DEFAULT_OUTPUT_PATH,
    AnomalyConfig, ModelConfig
)
from src.pipeline import CostPipeline
from src.vector_store import ContextNoteStore
from src.guardrails import GuardrailEngine, VerificationResult
from src.tracker import TokenTracker

class ShippingCostAssistant:
    def __init__(
        self,
        shipments_path: Path = DEFAULT_SHIPMENTS_PATH,
        notes_path: Path = DEFAULT_NOTES_PATH,
        anomaly_config: Optional[AnomalyConfig] = None,
        model_config: Optional[ModelConfig] = None
    ):
        self.anomaly_config = anomaly_config or AnomalyConfig()
        self.model_config = model_config or ModelConfig()
        self.pipeline = CostPipeline(config=self.anomaly_config)
        self.vector_store = ContextNoteStore(notes_path=notes_path)
        self.guardrail = GuardrailEngine()
        self.tracker = TokenTracker(
            model_name=self.model_config.model_name,
            cost_per_1k_input=self.model_config.cost_per_1k_input_tokens,
            cost_per_1k_output=self.model_config.cost_per_1k_output_tokens
        )
        self.shipments_path = shipments_path
        self._analyzed_df: Optional[pd.DataFrame] = None
        self._output_df: Optional[pd.DataFrame] = None

    def analyze(self, include_all_weeks: bool = False) -> pd.DataFrame:
        """
        Run the complete pipeline:
        1. Calculate weekly aggregates and comparisons.
        2. Filter candidate anomalies (or all weeks if include_all_weeks=True).
        3. Retrieve relevant context notes for each candidate.
        4. Guardrail verification against hallucinations and negative controls.
        5. Format output matching sample_output_format.csv.
        """
        metrics_df = self.pipeline.run(self.shipments_path)
        self._analyzed_df = metrics_df.copy()

        if include_all_weeks:
            eval_df = metrics_df.copy()
        else:
            eval_df = metrics_df[metrics_df['is_candidate']].copy()

        output_rows = []
        for _, row in eval_df.iterrows():
            route = row['route']
            week_of = row['week_of']
            week_str = week_of.strftime('%Y-%m-%d')
            cost = round(row['cost_per_tonne_km'], 2)
            vs_own = row['vs_own_history']
            vs_peer = row['vs_similar_routes']
            pct_own = row['pct_vs_own']
            pct_peer = row['pct_vs_peer']
            is_candidate = row['is_candidate']

            # If not candidate (normal week), flag is No
            if not is_candidate:
                flagged = "No"
                matched_id = ""
                reason = "Cost per tonne-km is within normal operating baselines."
            else:
                # Retrieve candidate notes from vector store
                retrieved_notes = self.vector_store.search_relevant_notes(route, week_str, top_k=3)

                # Verify via strict guardrail engine
                result: VerificationResult = self.guardrail.verify_justification(
                    route=route,
                    week_of_dt=week_of,
                    cost_per_tonne_km=cost,
                    pct_vs_own=pct_own,
                    pct_vs_peer=pct_peer,
                    retrieved_notes=retrieved_notes
                )

                if result.is_justified:
                    flagged = "No (justified)"
                    matched_id = result.matched_note_id
                    reason = result.reason
                else:
                    flagged = "Yes"
                    matched_id = ""
                    reason = result.reason

                # Log token usage for explainability / RAG call
                prompt_text = (
                    f"Evaluate cost rise for route {route} on week {week_str}. "
                    f"Cost: {cost}, vs_own: {pct_own:+.1f}%, vs_peer: {pct_peer:+.1f}%. "
                    f"Context notes retrieved: {len(retrieved_notes)}"
                )
                self.tracker.log_call(
                    prompt=prompt_text,
                    response=reason,
                    meta={"route": route, "week": week_str, "flagged": flagged, "note_id": matched_id}
                )

            output_rows.append({
                "route": route,
                "week_of": week_str,
                "cost_per_tonne_km": f"{cost:.2f}",
                "vs_own_history": vs_own,
                "vs_similar_routes": vs_peer,
                "flagged": flagged,
                "matched_note_id": matched_id,
                "reason": reason
            })

        out_df = pd.DataFrame(output_rows)
        # Reorder to match exact contract in sample_output_format_v2.csv
        contract_cols = [
            "route", "week_of", "cost_per_tonne_km", "vs_own_history",
            "vs_similar_routes", "flagged", "matched_note_id", "reason"
        ]
        out_df = out_df[contract_cols]
        self._output_df = out_df
        return out_df

    def export_csv(self, output_path: Path = DEFAULT_OUTPUT_PATH, include_all_weeks: bool = False) -> Path:
        """Export analyzed results to CSV matching exact format with RFC 4180 quotes."""
        out_df = self.analyze(include_all_weeks=include_all_weeks)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Using csv.QUOTE_MINIMAL ensures commas in reason prose are properly quoted
        out_df.to_csv(output_path, index=False, quoting=csv.QUOTE_MINIMAL, encoding="utf-8")
        return output_path

    def ask(self, query: str) -> str:
        """
        Stretch Goal: Natural language assistant to answer questions about shipping costs,
        corridors, spikes, dates, and justifications based on analysis results.
        """
        if self._analyzed_df is None or self._output_df is None:
            self.analyze(include_all_weeks=True)

        query_lower = query.lower()

        # Check for route mentions
        all_routes = self._analyzed_df['route'].unique().tolist()
        matched_route = None
        for r in all_routes:
            parts = r.lower().split('-')
            if r.lower() in query_lower or (parts[0] in query_lower and parts[1] in query_lower):
                matched_route = r
                break

        # Check for month or year mentions
        months = {
            'january': '01', 'jan': '01',
            'february': '02', 'feb': '02',
            'march': '03', 'mar': '03',
            'april': '04', 'apr': '04',
            'may': '05',
            'june': '06', 'jun': '06',
            'july': '07', 'jul': '07',
            'august': '08', 'aug': '08',
            'september': '09', 'sep': '09',
            'october': '10', 'oct': '10',
            'november': '11', 'nov': '11',
            'december': '12', 'dec': '12'
        }
        matched_month = None
        for m_name, m_num in months.items():
            if re.search(r'\b' + m_name + r'\b', query_lower):
                matched_month = m_num
                break

        year_match = re.search(r'\b(2024|2025)\b', query)
        matched_year = year_match.group(1) if year_match else None

        # Filter output df
        df = self._output_df
        subset = df.copy()

        if matched_route:
            subset = subset[subset['route'] == matched_route]

        if matched_year:
            subset = subset[subset['week_of'].str.startswith(matched_year)]

        if matched_month:
            subset = subset[subset['week_of'].str.slice(5, 7) == matched_month]

        # Log Q&A interaction
        prompt_text = f"User Query: {query}"

        if len(subset) == 0:
            if matched_route:
                answer = f"No flagged anomalies or unusual cost spikes were detected for route {matched_route} during the specified period."
            else:
                answer = "I could not locate specific anomalies matching that corridor or time period. Please specify a corridor (e.g., Chennai-Bangalore, Delhi-Jaipur) and date or month."
            self.tracker.log_call(prompt=prompt_text, response=answer, meta={"query": query})
            return answer

        # Format informative response
        flagged_subset = subset[subset['flagged'].isin(['Yes', 'No (justified)'])]
        if len(flagged_subset) == 0:
            avg_cost = pd.to_numeric(subset['cost_per_tonne_km']).mean()
            answer = f"For {matched_route or 'the queried route'}, costs remained normal during this period (averaging INR {avg_cost:.2f} per tonne-km), within expected historical baselines."
        else:
            lines = []
            target_name = matched_route or "Queried corridors"
            lines.append(f"Findings for {target_name}:")
            for _, r in flagged_subset.iterrows():
                lines.append(
                    f"- Week of {r['week_of']}: Cost was INR {r['cost_per_tonne_km']}/tonne-km "
                    f"({r['vs_own_history']}, {r['vs_similar_routes']}). "
                    f"Status: {r['flagged']}. {r['reason']}"
                )
            answer = "\n".join(lines)

        self.tracker.log_call(prompt=prompt_text, response=answer, meta={"query": query})
        return answer

