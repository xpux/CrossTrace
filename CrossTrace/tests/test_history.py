import history as h


def make_results():
    return [{
        "tier": "AUTO-CONFIRMED",
        "entry_a": {"username": "johndoe", "platform": "tiktok"},
        "entry_b": {"username": "johndoe", "platform": "instagram"},
        "score": 100,
    }]


def test_record_and_score_history(tmp_path):
    path = str(tmp_path / "history.json")
    h.record_session("s1", "target", "johndoe", make_results(), "output/s1", path=path)
    timeline = h.get_score_history("johndoe", path=path)
    assert len(timeline) == 1
    assert timeline[0]["score"] == 100


def test_compare_sessions(tmp_path):
    path = str(tmp_path / "history.json")
    h.record_session("s1", "target", "x", make_results(), "out", path=path)
    # second session: johndoe drops, newperson appears
    res2 = [{
        "tier": "AUTO-CONFIRMED",
        "entry_a": {"username": "newperson", "platform": "tiktok"},
        "entry_b": {"username": "newperson", "platform": "instagram"},
        "score": 90,
    }]
    h.record_session("s2", "target", "x", res2, "out", path=path)
    diff, err = h.compare_sessions("s1", "s2", path=path)
    assert err is None
    new_keys = {d["key"] for d in diff["new"]}
    gone_keys = {d["key"] for d in diff["gone"]}
    assert "newperson" in new_keys
    assert "johndoe" in gone_keys


def test_compare_missing_session(tmp_path):
    path = str(tmp_path / "history.json")
    h.record_session("s1", "target", "x", make_results(), "out", path=path)
    diff, err = h.compare_sessions("s1", "nope", path=path)
    assert diff is None
    assert "not found" in err
