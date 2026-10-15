"""Token and cost tracking module for monitoring LLM and pipeline usage."""

import json
from pathlib import Path
from typing import Dict, Any, List

class TokenTracker:
    def __init__(self, model_name: str = "open-source-deterministic", cost_per_1k_input: float = 0.0, cost_per_1k_output: float = 0.0):
        self.model_name = model_name
        self.cost_per_1k_input = cost_per_1k_input
        self.cost_per_1k_output = cost_per_1k_output
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.call_count = 0
        self.call_logs: List[Dict[str, Any]] = []

    def log_call(self, prompt: str, response: str, input_tokens: int = None, output_tokens: int = None, meta: Dict[str, Any] = None):
        """Log an LLM / assistant call with estimated or exact token counts."""
        # Standard estimation: ~4 chars per token if not provided
        in_tok = input_tokens if input_tokens is not None else max(1, len(prompt) // 4)
        out_tok = output_tokens if output_tokens is not None else max(1, len(response) // 4)

        self.total_input_tokens += in_tok
        self.total_output_tokens += out_tok
        self.call_count += 1

        record = {
            "call_index": self.call_count,
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "meta": meta or {}
        }
        self.call_logs.append(record)

    @property
    def estimated_cost_usd(self) -> float:
        input_cost = (self.total_input_tokens / 1000.0) * self.cost_per_1k_input
        output_cost = (self.total_output_tokens / 1000.0) * self.cost_per_1k_output
        return round(input_cost + output_cost, 6)

    def summary(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "number_of_calls": self.call_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "cost_per_1k_input_usd": self.cost_per_1k_input,
            "cost_per_1k_output_usd": self.cost_per_1k_output,
            "estimated_cost_usd": f"${self.estimated_cost_usd:.4f}"
        }

    def save_report(self, file_path: Path):
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.summary(), f, indent=2)

