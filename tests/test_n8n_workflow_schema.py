"""Unit tests for n8n Cloud Workflow JSON Schema and JS Helper Scripts."""

import json
import pytest
from pathlib import Path


def test_n8n_workflow_json_structure():
    """Verify that video_post_master_workflow.json is valid n8n workflow format."""
    workflow_path = Path("n8n_workflows/video_post_master_workflow.json")
    assert workflow_path.exists(), "n8n workflow JSON file must exist"

    with open(workflow_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "name" in data
    assert "nodes" in data
    assert "connections" in data
    assert isinstance(data["nodes"], list)
    assert len(data["nodes"]) >= 8

    # Check for all required node types
    node_types = [n.get("type") for n in data["nodes"]]
    assert "n8n-nodes-base.scheduleTrigger" in node_types
    assert "n8n-nodes-base.googleSheets" in node_types
    assert "n8n-nodes-base.googleDrive" in node_types
    assert "n8n-nodes-base.code" in node_types
    assert "n8n-nodes-base.httpRequest" in node_types

    # Verify all connections point to valid node IDs
    node_ids = {n["id"] for n in data["nodes"]}
    for src_id, conn_data in data["connections"].items():
        assert src_id in node_ids, f"Connection source '{src_id}' must exist in nodes"
        for branch in conn_data.get("main", []):
            for target in branch:
                target_id = target.get("node")
                assert target_id in node_ids, f"Connection target '{target_id}' must exist in nodes"


def test_js_helper_scripts_exist_and_non_empty():
    """Verify JS helper scripts exist and contain required logic."""
    parse_script = Path("n8n_workflows/scripts/parse_candidate_jobs.js")
    format_script = Path("n8n_workflows/scripts/format_publish_result.js")

    assert parse_script.exists()
    assert format_script.exists()

    parse_content = parse_script.read_text(encoding="utf-8")
    assert "extractDriveFileId" in parse_content
    assert "#Shorts" in parse_content
    assert "post_before" in parse_content

    format_content = format_script.read_text(encoding="utf-8")
    assert "status_yt" in format_content
    assert "status_fb" in format_content
    assert "status_ig" in format_content


def test_readme_guide_exists():
    """Verify README guide exists with essential sections."""
    readme_path = Path("n8n_workflows/README.md")
    assert readme_path.exists()
    content = readme_path.read_text(encoding="utf-8")
    assert "YouTube Shorts" in content
    assert "Facebook Reels" in content
    assert "Instagram Reels" in content
    assert "Import" in content
