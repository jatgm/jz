"""
Unit tests for file tracking and manifest recording.
"""

from jz_cli.tracker import get_tracked_items, record_manifest


def test_tracked_items():
    items = get_tracked_items()
    assert len(items) >= 5
    names = [i.name for i in items]
    assert "Configuration Directory" in names
    assert "Config File" in names
    assert "Manifest File" in names


def test_record_manifest():
    record_manifest()
    items = get_tracked_items()
    manifest_item = next((i for i in items if i.name == "Manifest File"), None)
    assert manifest_item is not None
    assert manifest_item.exists
    assert manifest_item.size_bytes > 0
