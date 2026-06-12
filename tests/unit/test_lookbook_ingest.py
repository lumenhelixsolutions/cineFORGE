"""Unit tests for lookBOOK → CineForge ingest bridge."""
import json

import pytest

from backend.ingest.lookbook import (
    build_treatment_from_lookbook,
    convert_lookbook_to_shots,
    parse_lookbook_shot_graph,
)


SAMPLE = {
    "schema": "lookbook.shot_graph.v0.3",
    "total_shots": 2,
    "shots": [
        {
            "shot_index": 0,
            "type": "establishing",
            "camera": "pan right",
            "duration_seconds": 5.0,
            "motion_directive": "Slow pan across the scene.",
            "dialogue": [],
            "narration": ["The scene opens."],
            "characters": [],
            "transition_in": "cut",
        },
        {
            "shot_index": 1,
            "type": "dialogue",
            "camera": "zoom in",
            "duration_seconds": 7.0,
            "motion_directive": "Focus on character.",
            "dialogue": ['"Hello."'],
            "narration": [],
            "characters": ["char_000"],
            "transition_in": "dissolve",
        },
    ],
}


def test_parse_lookbook_shot_graph():
    data = parse_lookbook_shot_graph(SAMPLE)
    assert data["total_shots"] == 2


def test_parse_rejects_empty_shots():
    with pytest.raises(ValueError, match="non-empty"):
        parse_lookbook_shot_graph({"schema": "lookbook.shot_graph.v0.3", "shots": []})


def test_convert_maps_durations_and_prompts():
    shots = convert_lookbook_to_shots(SAMPLE)
    assert len(shots) == 2
    assert shots[0]["duration_sec"] in (4, 6, 8)
    assert shots[0]["tier"] == "hero"
    assert "Slow pan" in shots[0]["prompt_text"]
    assert shots[0]["bridge_strategy"] == "hard_cut"
    assert shots[1]["continuity"]["characters"] == ["char_000"]
    assert shots[1]["bridge_strategy"] == "match_cut"


def test_build_treatment_stub():
    treatment = build_treatment_from_lookbook(SAMPLE)
    assert treatment["source"] == "lookbook"
    assert len(treatment["acts"][0]["beats"]) == 2


def test_parse_from_json_string():
    data = parse_lookbook_shot_graph(json.dumps(SAMPLE))
    assert data["total_shots"] == 2