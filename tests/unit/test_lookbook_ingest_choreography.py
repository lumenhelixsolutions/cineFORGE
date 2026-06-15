"""Unit tests for lookBOOK choreography + panels ingest bridge."""
import json

import pytest

from backend.ingest.lookbook import (
    build_treatment_from_lookbook,
    convert_lookbook_to_shots,
    parse_lookbook_choreography,
)


SHOT_GRAPH = {
    "schema": "lookbook.shot_graph.v0.3",
    "total_shots": 2,
    "shots": [
        {
            "shot_index": 0,
            "type": "establishing",
            "camera": "pan right",
            "duration_seconds": 5.0,
            "characters": [],
            "transition_in": "cut",
        },
        {
            "shot_index": 1,
            "type": "dialogue",
            "camera": "push in",
            "duration_seconds": 4.0,
            "characters": ["char_000"],
            "choreography_line_index": 0,
            "active_speaker": "Hero",
            "transition_in": "cut",
        },
    ],
}

CHOREOGRAPHY = {
    "schema": "lookbook.choreography.v0.1",
    "total_lines": 2,
    "lines": [
        {
            "line_index": 0,
            "speaker": "Hero",
            "text": '"Hello there."',
            "classification": "dialogue",
            "panel_index": 1,
        },
        {
            "line_index": 1,
            "speaker": "narrator",
            "text": "Meanwhile, elsewhere…",
            "classification": "narration",
            "panel_index": 0,
        },
    ],
    "voice_cast": {"Hero": {"character_id": "char_000"}},
}

PANELS = [
    {"panel_index": 0, "bbox": {"x": 0, "y": 0, "w": 200, "h": 300}},
    {"panel_index": 1, "bbox": {"x": 200, "y": 0, "w": 200, "h": 300}},
]


def test_parse_lookbook_choreography():
    data = parse_lookbook_choreography(CHOREOGRAPHY)
    assert data["total_lines"] == 2


def test_parse_choreography_rejects_missing_lines():
    with pytest.raises(ValueError, match="lines array"):
        parse_lookbook_choreography({"schema": "lookbook.choreography.v0.1"})


def test_convert_maps_dialogue_to_continuity():
    shots = convert_lookbook_to_shots(SHOT_GRAPH, choreography=CHOREOGRAPHY)
    assert shots[1]["continuity"]["dialogue"] == '"Hello there."'
    assert shots[1]["continuity"]["active_speaker"] == "Hero"
    assert shots[1]["continuity"]["choreography_line_index"] == 0


def test_convert_maps_narration_line_to_narration_field():
    graph = {
        **SHOT_GRAPH,
        "shots": [
            {
                "shot_index": 0,
                "type": "dialogue",
                "duration_seconds": 4.0,
                "choreography_line_index": 1,
                "active_speaker": "narrator",
                "characters": [],
                "transition_in": "cut",
            }
        ],
    }
    shots = convert_lookbook_to_shots(graph, choreography=CHOREOGRAPHY)
    assert shots[0]["narration"] == "Meanwhile, elsewhere…"
    assert "dialogue" not in shots[0]["continuity"]


def test_build_treatment_stores_choreography_and_panels():
    treatment = build_treatment_from_lookbook(
        SHOT_GRAPH,
        choreography=CHOREOGRAPHY,
        panels=PANELS,
    )
    assert treatment["choreography"]["total_lines"] == 2
    assert len(treatment["panels"]) == 2
    assert treatment["source"] == "lookbook"


def test_shot_only_ingest_unchanged_without_choreography():
    shots = convert_lookbook_to_shots(SHOT_GRAPH)
    treatment = build_treatment_from_lookbook(SHOT_GRAPH)
    assert "dialogue" not in shots[1]["continuity"]
    assert "choreography" not in treatment
    assert "panels" not in treatment


def test_parse_choreography_from_json_string():
    data = parse_lookbook_choreography(json.loads(json.dumps(CHOREOGRAPHY)))
    assert data["total_lines"] == 2