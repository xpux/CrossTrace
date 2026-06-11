import json
import xml.dom.minidom as minidom

import graph as g


def target_results():
    return [{
        "tier": "AUTO-CONFIRMED",
        "entry_a": {"username": "johndoe", "display_name": "John Doe", "platform": "tiktok"},
        "entry_b": {"username": "johndoe", "display_name": "John Doe", "platform": "instagram"},
        "score": 100,
        "reasons": ["username exact/near match (100%)"],
    }]


def discovery_results():
    return [{
        "tier": "AUTO-CONFIRMED",
        "entry": {"username": "johndoe", "display_name": "John Doe"},
        "platforms": ["tiktok", "instagram"],
        "seen_by": ["me", "friend_a"],
        "score": 100,
    }]


def test_build_target_graph():
    graph = g.build_graph(target_results(), mode="target")
    assert graph["meta"]["node_count"] == 2
    assert graph["meta"]["edge_count"] == 1
    assert graph["edges"][0]["weight"] == 100


def test_build_discovery_graph_has_seed_nodes():
    graph = g.build_graph(discovery_results(), mode="discovery")
    kinds = {n["kind"] for n in graph["nodes"]}
    assert "seed" in kinds
    assert "account" in kinds
    assert graph["meta"]["edge_count"] == 2  # account linked to two seed users


def test_weak_tier_excluded_by_default():
    res = target_results()
    res[0]["tier"] = "WEAK"
    graph = g.build_graph(res, mode="target")
    assert graph["meta"]["node_count"] == 0


def test_export_json_roundtrip(tmp_path):
    graph = g.build_graph(target_results(), mode="target")
    path = str(tmp_path / "graph.json")
    g.export_json(graph, path)
    loaded = json.load(open(path, encoding="utf-8"))
    assert loaded["meta"]["node_count"] == 2


def test_export_graphml_is_valid_xml(tmp_path):
    graph = g.build_graph(target_results(), mode="target")
    path = str(tmp_path / "graph.graphml")
    g.export_graphml(graph, path)
    minidom.parse(path)  # raises if malformed


def test_export_html_is_offline(tmp_path):
    graph = g.build_graph(target_results(), mode="target")
    path = str(tmp_path / "graph.html")
    g.export_html(graph, path)
    content = open(path, encoding="utf-8").read()
    assert "johndoe" in content
    for marker in ("http://", "https://", "cdn", "googleapis"):
        assert marker not in content.lower()
