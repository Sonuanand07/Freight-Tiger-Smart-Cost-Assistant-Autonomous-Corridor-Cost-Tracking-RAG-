# 10-Minute Presentation & Walkthrough Guide (Round 2)
**Role**: Software Engineering Intern (AI)  
**Company**: Freight Tiger  
**Topic**: Smart Shipping Cost Assistant Walkthrough & Demo

---

## ⏱️ Presentation Outline & Time Allocation (Total: 10 Minutes)

| Time | Slide / Topic | Key Points to Cover |
| :--- | :--- | :--- |
| **00:00 - 02:00** | **1. Problem & Core Formulation** | The business challenge of freight cost creep, weekly Monday grouping, and the exact metric: $\frac{\sum \text{cost}}{\sum (\text{weight} \times \text{distance})}$. |
| **02:00 - 04:00** | **2. Baselines & Ground-Truth Math** | Trailing 8-week strictly prior rolling window (no look-ahead) + same-week peer group baseline excluding self. Proof against sample output. |
| **04:00 - 06:00** | **3. AI, RAG & Hallucination Defense** | ChromaDB semantic search over context notes + Guardrail Engine rejecting negative controls/distractors (`N004` to `N010`). |
| **06:00 - 08:00** | **4. Live Interactive Demo** | Demonstrating CLI `run`, `reproduce` (3 runs matching 100%), and Natural Language Q&A (`ask`) + Web App. |
| **08:00 - 10:00** | **5. Engineering Trade-offs & Q&A** | Determinism vs temperature, local vector search vs cloud vendor lock-in, cost accounting ($0.00 spend). |

---

## 🎤 Detailed Script & Talk Track

### 1. Introduction & Problem Statement (00:00 - 02:00)
> *"Hello everyone, thank you for having me today. In freight logistics, transportation costs fluctuate continuously. While some price increases stem from legitimate operational events—such as fuel hikes, monsoon flooding, or festival surcharges—others represent unjustified price creep from transporters.*
>
> *My goal was to build a production-grade Smart Assistant that accomplishes three things:*
> 1. *Accurately tracks shipping costs per tonne-km week-over-week across corridors.*
> 2. *Compares each route against its own trailing history and its similar-length peers.*
> 3. *Uses AI to retrieve real-world context notes and determine whether an observed cost spike is justified or an anomaly requiring human intervention, with strict anti-hallucination guardrails."*

---

### 2. Core Mathematical Pipeline & Ground-Truth Verification (02:00 - 04:00)
> *"First, let's look at the mathematical formulation. For every route and route_type, we normalize dates into Monday-to-Sunday buckets:*
> $$\text{Cost per Tonne-Km} = \frac{\sum \text{freight\_cost\_inr}}{\sum (\text{quantity\_tonnes} \times \text{distance\_km})}$$
>
> *We then compute two strict baselines:*
> 1. **Trailing 8-Week Rolling Average**: *Uses only weeks strictly prior to the current week—eliminating any look-ahead leakage. For the initial weeks where fewer than 8 weeks exist, we use all available prior weeks without artificial padding.*
> 2. **Similar Routes Baseline**: *Calculates the average cost across all other routes within the same length tier (Short, Medium, or Long) in that same week, explicitly excluding the route itself.*
>
> *To convince myself the core logic was 100% correct before writing any AI logic, I validated against the provided sample rows. Our computed values match the sample output to the exact decimal:
> - Delhi-Jaipur (2024-11-11): Cost 4.17 (+35.5% vs own history, +21.0% vs peers).
> - Ahmedabad-Mumbai (2025-01-20): Cost 3.29 (+29.5% vs own history, +22.5% vs peers).
> - Mumbai-Pune (2025-09-15): Cost 3.98 (+9.2% vs own history, +23.6% vs peers)."*

---

### 3. Meaningful AI: RAG & Anti-Hallucination Guardrails (04:00 - 06:00)
> *"Next is the AI system. A naive RAG system will blindly retrieve the most textually similar note and declare a route 'justified'. But looking closely at the 10 context notes in `context_notes.csv`, 7 of them are intentional distractors and negative controls!*
> - *For instance, Note `N006` mentions that logistics demand remained stable with no major disruptions. A hallucinating LLM sees a note for 'All Routes' around the right date and assumes it's justified.*
> - *Similarly, Note `N005` explicitly states 'costs were not significantly affected', and `N004` states 'affected routes are not part of this dataset'.*
>
> *To solve this, I designed a multi-layer Guardrail Engine:*
> 1. **ChromaDB Vector Retrieval**: *Embeds and indexes notes with metadata filtering on corridor and date ranges.*
> 2. **Corridor Applicability Check**: *Guarantees corridor relevance (`applies_to == route` or `All Routes`).*
> 3. **Temporal Proximity Check**: *Ensures the active event window aligns with the anomaly week (e.g. Chennai-Bangalore flood between Feb 24 and Mar 8).*
> 4. **Cost-Impact Semantic Verification**: *Explicitly checks if the note describes an actual cost inflation event. If it is a negative control, the assistant marks the row `Yes` (unjustified, flagged for human review), leaves `matched_note_id` blank, and explains that the closest note did not describe a valid justification.*
>
> *This precisely matches Row 4 of your sample output!"*

---

### 4. Live Demo: Reproducibility, CLI & Q&A Assistant (06:00 - 08:00)
*(Screen Share Terminal or Web Dashboard)*

**Demo Step A: Run Test Suite**
```powershell
python -m pytest -v
```
> *"Notice that all 13 unit tests pass, confirming mathematical precision, guardrail enforcement, and contract schema compliance."*

**Demo Step B: 3-Run Reproducibility Diff**
```powershell
python -m src.cli reproduce
```
> *"Running 3 untouched passes across the dataset confirms identical flags, note citations, and percentages every single time. By setting temperature strictly to 0, we eliminate non-deterministic drift."*

**Demo Step C: Natural Language Assistant (Stretch Goal)**
```powershell
python -m src.cli ask "Why did Chennai-Bangalore get pricier in March 2025?"
```
> *"Notice the assistant's grounded answer: it recognizes that during the week of March 3rd, costs were elevated due to highway flooding (justified by Note N001), but for the weeks of March 10th and 17th, costs remained elevated even after roads returned to normal conditions (citing Note N009's normal report), correctly flagging those later weeks for human review!"*

**Demo Step D: Visual Web App Dashboard**
```powershell
python -m uvicorn src.web_app:app --port 8000
```
> *"For operational teams, we also provide an interactive dashboard with live filtering, metric cards, and a built-in Q&A chat interface."*

---

### 5. Architectural Trade-offs & Cost Accounting (08:00 - 10:00)

> *"To wrap up, I'd like to highlight key engineering trade-offs:*
> 1. **Open-Source Local vs. Proprietary Cloud APIs**:
>    *Trade-off*: Rather than requiring a paid OpenAI/Anthropic API key that could fail during grading or incur recurring costs, I architected the assistant using an open-source vector store (ChromaDB) with deterministic RAG and template-grounded explanations.
>    *Result*: Zero vendor lock-in, 100% reproducible, and a run cost of exactly **$0.0000** over 1,354 tokens.
> 2. **Rigid Rule-Based vs. Pure Generative AI**:
>    *Trade-off*: Pure generative models are prone to hallucinating explanations when under pressure. By placing a deterministic guardrail validation layer before the output generation, we achieve mathematical safety without sacrificing plain-English clarity.
> 3. **Rolling Window Boundary Handling**:
>    *Trade-off*: Rather than padding early weeks with global averages or forward-filling, we strictly use all available prior weeks, ensuring zero data leakage.
>
> *Thank you, and I look forward to your questions!"*

