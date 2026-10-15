"""Unit and evaluation tests for guardrail and hallucination defense."""

import pytest
import pandas as pd
from src.guardrails import GuardrailEngine
from src.vector_store import ContextNoteStore
from src.config import DEFAULT_NOTES_PATH

@pytest.fixture
def guardrail():
    return GuardrailEngine()

@pytest.fixture
def note_store():
    return ContextNoteStore(DEFAULT_NOTES_PATH)

def test_justified_verdict_flooding_chennai_bangalore(guardrail, note_store):
    """Note N001 should justify Chennai-Bangalore spike on 2025-02-24."""
    week = pd.to_datetime('2025-02-24')
    notes = note_store.search_relevant_notes('Chennai-Bangalore', '2025-02-24')
    result = guardrail.verify_justification(
        route='Chennai-Bangalore',
        week_of_dt=week,
        cost_per_tonne_km=3.58,
        pct_vs_own=31.5,
        pct_vs_peer=38.7,
        retrieved_notes=notes
    )
    assert result.is_justified is True
    assert result.matched_note_id == 'N001'
    assert 'flooding' in result.reason.lower()

def test_justified_verdict_festival_ahmedabad_mumbai(guardrail, note_store):
    """Note N002 should justify Ahmedabad-Mumbai spike on 2025-01-20."""
    week = pd.to_datetime('2025-01-20')
    notes = note_store.search_relevant_notes('Ahmedabad-Mumbai', '2025-01-20')
    result = guardrail.verify_justification(
        route='Ahmedabad-Mumbai',
        week_of_dt=week,
        cost_per_tonne_km=3.29,
        pct_vs_own=29.5,
        pct_vs_peer=22.5,
        retrieved_notes=notes
    )
    assert result.is_justified is True
    assert result.matched_note_id == 'N002'
    assert 'festival' in result.reason.lower()

def test_guardrail_rejects_distractor_n006(guardrail, note_store):
    """Note N006 (stable demand) must NOT justify Mumbai-Pune spike on 2025-09-15."""
    week = pd.to_datetime('2025-09-15')
    notes = note_store.search_relevant_notes('Mumbai-Pune', '2025-09-15')
    result = guardrail.verify_justification(
        route='Mumbai-Pune',
        week_of_dt=week,
        cost_per_tonne_km=3.98,
        pct_vs_own=9.2,
        pct_vs_peer=23.6,
        retrieved_notes=notes
    )
    assert result.is_justified is False
    assert result.matched_note_id == ""
    assert "stable" in result.reason.lower() or "unexplained" in result.reason.lower()

def test_unexplained_verdict_delhi_jaipur(guardrail, note_store):
    """Delhi-Jaipur on 2024-11-11 has no note and must be marked unexplained."""
    week = pd.to_datetime('2024-11-11')
    notes = note_store.search_relevant_notes('Delhi-Jaipur', '2024-11-11')
    result = guardrail.verify_justification(
        route='Delhi-Jaipur',
        week_of_dt=week,
        cost_per_tonne_km=4.17,
        pct_vs_own=35.5,
        pct_vs_peer=21.0,
        retrieved_notes=notes
    )
    assert result.is_justified is False
    assert result.matched_note_id == ""
    assert "no matching note" in result.reason.lower()

def test_route_mismatch_rejection(guardrail):
    """Note N001 (Chennai-Bangalore) cannot justify a spike on Mumbai-Delhi."""
    week = pd.to_datetime('2025-02-24')
    fake_notes = [{
        'note_id': 'N001',
        'date': '2025-02-24',
        'applies_to': 'Chennai-Bangalore',
        'note_text': 'Heavy flooding on Chennai-Bangalore'
    }]
    result = guardrail.verify_justification(
        route='Mumbai-Delhi',
        week_of_dt=week,
        cost_per_tonne_km=2.50,
        pct_vs_own=20.0,
        pct_vs_peer=15.0,
        retrieved_notes=fake_notes
    )
    assert result.is_justified is False
    assert result.matched_note_id == ""

