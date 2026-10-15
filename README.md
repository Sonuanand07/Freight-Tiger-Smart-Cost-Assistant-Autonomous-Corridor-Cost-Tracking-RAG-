# Freight Tiger Smart Shipping Cost Assistant

Autonomous AI assistant that monitors freight route costs, detects out-of-the-ordinary cost inflation against historical and peer baselines, and grounds verdicts in operational context notes using Retrieval-Augmented Generation (RAG) and anti-hallucination guardrails.

---

## 📌 Executive Summary & Core Results

- **Data Ingested**: 2,940 shipment records across 7 nationwide freight corridors (Short, Medium, Long) spanning 2 full calendar years (2024–2025).
- **Weekly Tracking**: Grouped strictly Monday to Sunday (`week_of` = Monday date `YYYY-MM-DD`).
- **Core Formula**: `cost_per_tonne_km = sum(freight_cost_inr) / sum(quantity_tonnes * distance_km)`

- **Verification Against Sample Ground Truth**:
  | Corridor | Week Of | Assistant Cost | Sample Cost | vs. Own History (8-Wk) | vs. Similar Routes | Flagged Verdict | Matched Note |
  | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
  | **Delhi-Jaipur** | 2024-11-11 | **4.17** | **4.17** | **+35.5%** | **+21.0%** | `Yes` | *(blank)* |
  | **Ahmedabad-Mumbai** | 2025-01-20 | **3.29** | **3.29** | **+29.5%** | **+22.5%** | `No (justified)` | `N002` |
  | **Mumbai-Pune** | 2025-09-15 | **3.98** | **3.98** | **+9.2%** | **+23.6%** | `Yes` | *(blank)* |
- **Reproducibility**: 3 untouched consecutive runs produced **100% identical outputs** (0 diff across all numbers, verdicts, and citations).
- **Cost of Full Run**: 21 LLM/RAG calls, 1,354 total tokens, **$0.0000** total run spend (Open-Source Deterministic Model).
- **Test Suite**: 14/14 unit and evaluation tests passing (`pytest`).

---

## 🏗️ Architecture & How It Works

```
┌─────────────────────────────────┐       ┌───────────────────────────────────┐
│   shipment_records.csv (2,940)  │       │      context_notes.csv (10)       │
└────────────────┬────────────────┘       └─────────────────┬─────────────────┘
                 │                                          │
                 ▼                                          ▼
┌─────────────────────────────────┐       ┌───────────────────────────────────┐
│        CostPipeline             │       │      ContextNoteStore (ChromaDB)  │
│  - Monday week_of grouping      │       │  - Vector embeddings & indexing   │
│  - Total cost / Total tonne-km  │       │  - Corridor & temporal metadata   │
│  - Trailing 8-week rolling avg  │       └─────────────────┬─────────────────┘
│  - Similar-length peer baseline │                         │
│  - Candidate anomaly detection  │                         │ Top candidate notes
└────────────────┬────────────────┘                         │
                 │                                          ▼
                 │ Candidate anomalies    ┌───────────────────────────────────┐
                 └───────────────────────►│        GuardrailEngine            │
                                          │  - Corridor match validation      │
                                          │  - Temporal window check          │
                                          │  - Negative control defense       │
                                          │  - Anti-hallucination enforcement │
                                          └─────────────────┬─────────────────┘
                                                            │
                                                            ▼
                                          ┌───────────────────────────────────┐
                                          │      ShippingCostAssistant        │
                                          │  - output/output.csv (Ledger)     │
                                          │  - Natural Language Q&A Engine    │
                                          │  - TokenTracker ($0.00 audit)     │
                                          │  - FastAPI Web Dashboard Demo     │
                                          └───────────────────────────────────┘
```

---

## 📐 Comparison Baselines (Grade Definitions Handled Precisely)

### 1. vs. Own History
- **Definition**: The route's trailing 8-week rolling average cost per tonne-km, using **only weeks strictly before the current week (no look-ahead)**.
- **Handling of fewer than 8 prior weeks**:
  - In Week 0 (e.g. `2024-01-01`), exactly 0 prior weeks exist; `hist_mean` is strictly `NaN` and formatted as `N/A (insufficient prior history)`.
  - In Weeks 1 to 7, the assistant uses **all available strictly prior weeks** without padding, extrapolating, or look-ahead bias (verified in `tests/test_pipeline.py::test_no_lookahead_bias`).

### 2. vs. Similar Routes (Peers)
- **Definition**: The average cost per tonne-km in that **same week** across all other routes sharing the same `route_type` (`Short`, `Medium`, `Long`).
- **Exclusion**: The evaluated route is strictly **excluded** from its own peer average.

---

## 🛡️ Guardrails & Anti-Hallucination Defense

A major requirement in the brief is:
> *"Every 'justified' verdict must cite the exact note, and that note must apply to that route and that time. Wrong route, wrong window, or a note that says costs weren't affected does not count."*

Out of the 10 context notes in `context_notes.csv`:
- Only **3 notes** describe legitimate operational cost spikes:
  - `N001` (Chennai-Bangalore highway flooding from Feb 24 to Mar 8, 2025).
  - `N002` (Ahmedabad-Mumbai regional festival surcharge on Jan 20, 2025).
  - `N003` (Nationwide diesel price hike on May 5, 2025).
- The remaining **7 notes** (`N004`, `N005`, `N006`, `N007`, `N008`, `N009`, `N010`) are intentional **negative controls / distractors**:
  - `N004`: "affected routes are not part of this dataset".
  - `N005`: "costs were not significantly affected".
  - `N006`: "stable demand with no major disruptions reported".
  - `N007`: "improved road conditions after resurfacing".
  - `N008`: "no significant disruptions... movement remained normal".
  - `N009`: "returned to normal conditions after flood repairs".
  - `N010`: "compliance costs were absorbed by transporters without a rate change".

### How Our Guardrail Engine Defends Against Traps:
1. **Corridor Applicability Check**: If a note applies to `Mumbai-Delhi`, it cannot be cited to justify `Chennai-Bangalore`.
2. **Temporal Window Check**: Validates the event date range (e.g. `N001` flooding active Feb 24 to Mar 8).
3. **Negative Control Filtering**: Automatically catches notes that state costs were absorbed or unaffected. For example, for `Mumbai-Pune` on `2025-09-15`, nearest note `N006` is checked, recognized as stating "stable demand with no disruption", so the assistant:
   - Sets verdict: `Yes` (Unjustified, flagged for human review).
   - Leaves `matched_note_id` blank `""`.
   - Explains: *"The closest note (N006, 2025-09-22) mentions stable conditions with no major cost disruption -- it does not describe a reason for a cost rise on this route. No genuine justification found; flagged for review."*

---

## 🧪 How We Convinced Ourselves It Was Right Before Submitting

1. **Exact Reproduction of Sample Ground Truth**:
   The sample file `sample_output_format_v2.csv` was treated as an uncompromisable ground-truth contract. Our arithmetic matched all sample values (`4.17`, `+35.5%`, `+21.0%`, `3.29`, `+29.5%`, `+22.5%`, `3.98`, `+9.2%`, `+23.6%`) to the exact decimal place.
2. **Comprehensive Automated Test Suite (`pytest`)**:
   13 unit and integration tests covering:
   - Monday alignment for all weeks.
   - Exact mathematical formula for `cost_per_tonne_km`.
   - Trailing 8-week rolling window strictness (zero lookahead).
   - Peer group route exclusion.
   - Justified verdict behavior for `N001` and `N002`.
   - Rejection of negative control distractors (`N006`, `N009`).
   - Rejection of corridor mismatches.
   - CSV output schema conformity (column count, ordering, quote handling).
   - 3-run reproducibility equality test.
3. **Reproducibility Verification**:
   Executed 3 consecutive untouched runs from raw data through `src.cli reproduce`. `df1.equals(df2)` and `df2.equals(df3)` returned `True`.

---

## 🚀 Quickstart & Usage

### 1. Installation
```powershell
pip install -r requirements.txt
```

### 2. Run the Full Anomaly Detection Pipeline
```powershell
python -m src.cli run
```
Generates `output/output.csv` matching `sample_output_format_v2.csv` exactly.

To export all 728 route-weeks (including unflagged operational weeks):
```powershell
python -m src.cli run --all-weeks --output output/output_all_weeks.csv
```

### 3. Verify Reproducibility Across 3 Untouched Runs
```powershell
python -m src.cli reproduce
```

### 4. Natural Language Assistant (Stretch Goal)
Ask questions in plain English directly from your terminal:
```powershell
python -m src.cli ask "Why did Chennai-Bangalore get pricier in March 2025?"
python -m src.cli ask "What happened on Ahmedabad-Mumbai in January 2025?"
python -m src.cli ask "Why did Delhi-Jaipur spike in November 2024?"
```

### 5. Run the Automated Test Suite
```powershell
python -m pytest -v
```

### 6. Launch the Interactive Web Dashboard Demo
```powershell
python -m uvicorn src.web_app:app --reload --port 8000
```
Open your browser at `http://localhost:8000` to interact with the visual dashboard and live Q&A assistant!

---

## 📊 Token & Cost Audit Log

From `output/token_cost_report.json`:
```json
{
  "model_name": "open-source-deterministic",
  "number_of_calls": 21,
  "total_input_tokens": 686,
  "total_output_tokens": 668,
  "total_tokens": 1354,
  "cost_per_1k_input_usd": 0.0,
  "cost_per_1k_output_usd": 0.0,
  "estimated_cost_usd": "$0.0000"
}
```
*Note*: The pipeline is designed with zero mandatory external API dependencies, allowing Freight Tiger evaluators to run, score, and reproduce results instantly without setting up paid API keys.

---

## 📁 Repository Structure

```
freight_tiger_assistant/
├── .gitignore                       # Ignores local caches, environments & generated ChromaDB files
├── data/
│   ├── shipment_records.csv          # 2,940 raw shipments (2024-2025)
│   ├── context_notes.csv             # 10 real-world notes & negative controls
│   └── sample_output_format_v2.csv   # Target contract schema
├── src/
│   ├── __init__.py
│   ├── config.py                     # Baseline window, thresholds, paths
│   ├── pipeline.py                   # Grouping, weekly cost, rolling & peer baselines
│   ├── vector_store.py               # ChromaDB embedding, persistence & search
│   ├── guardrails.py                 # Corridor, temporal, and distractor rejection engine
│   ├── assistant.py                  # Pipeline coordinator, CSV exporter, Q&A agent
│   ├── tracker.py                    # Token, call count, and cost accounting
│   ├── cli.py                        # CLI commands (run, reproduce, ask)
│   └── web_app.py                    # Interactive FastAPI demo dashboard
├── tests/
│   ├── __init__.py
│   ├── test_pipeline.py              # Math & baseline tests
│   ├── test_guardrails.py            # Anti-hallucination tests
│   ├── test_reproducibility.py       # Contract & 3-run reproducibility
│   └── test_web_app.py               # Web application favicon route test
├── output/
│   ├── output.csv                    # Final evaluated submission output
│   ├── output_all_weeks.csv          # Complete 728 route-week ledger
│   ├── reproducibility_run1.csv      # Run 1 of 3
│   ├── reproducibility_run2.csv      # Run 2 of 3
│   ├── reproducibility_run3.csv      # Run 3 of 3
│   └── token_cost_report.json        # Official token & cost report
├── README.md                         # Project documentation
├── WALKTHROUGH.md                    # 10-minute presentation guide for Round 2
└── requirements.txt                  # Python dependencies
```

The root-level exploratory analysis scripts used during development are not part of the runnable application or required test suite. They rely on a machine-specific data path, so they are intentionally excluded from the submission; the portable pipeline and verification checks are in `src/` and `tests/`.
