"""Configuration settings for Freight Tiger Shipping Cost Assistant."""

from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

DEFAULT_SHIPMENTS_PATH = DATA_DIR / "shipment_records.csv"
DEFAULT_NOTES_PATH = DATA_DIR / "context_notes.csv"
DEFAULT_SAMPLE_OUTPUT_PATH = DATA_DIR / "sample_output_format_v2.csv"
DEFAULT_OUTPUT_PATH = OUTPUT_DIR / "output.csv"
CHROMA_PERSIST_DIR = BASE_DIR / "chroma_db"

class AnomalyConfig(BaseModel):
    """Thresholds and parameters for flagging cost anomalies."""
    trailing_weeks_window: int = 8
    own_history_threshold_pct: float = 8.0     # cost must rise >= 8% vs trailing history
    similar_routes_threshold_pct: float = 20.0  # OR cost must rise >= 20% vs peer routes
    require_positive_rise: bool = True          # cost must be strictly higher than trailing history

class ModelConfig(BaseModel):
    """Configuration for LLM and Embeddings."""
    model_name: str = "open-source-deterministic"
    temperature: float = 0.0                    # strictly 0 for reproducibility
    cost_per_1k_input_tokens: float = 0.0       # $0.00 for local / free tier
    cost_per_1k_output_tokens: float = 0.0

