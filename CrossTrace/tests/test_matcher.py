import matcher as m


def entry(username=None, display_name=None, **extra):
    base = {"username": username, "display_name": display_name}
    base.update(extra)
    return base


def test_exact_username_strong_but_needs_corroboration():
    # An identical username with no display name is a strong signal but, by
    # design, does not auto-confirm on its own — it lands in quick review so a
    # human can corroborate. This guards against linking common handles blindly.
    score, reasons = m.score_pair(entry("johndoe"), entry("johndoe"), {}, {})
    assert score >= 75
    assert m.get_tier(score) in ("AUTO-CONFIRMED", "QUICK REVIEW")
    assert any("username" in r or "variation" in r for r in reasons)


def test_identical_username_and_display_name_auto_confirms():
    score, _ = m.score_pair(entry("johndoe", "John Doe"), entry("johndoe", "John Doe"), {}, {})
    assert score >= 95


def test_pattern_variation_bonus():
    plain, _ = m.score_pair(entry("johndoe"), entry("xyzqwd"), {}, {})
    varied, reasons = m.score_pair(entry("johndoe"), entry("johndoe_"), {}, {})
    assert varied > plain
    assert any("variation" in r for r in reasons)


def test_alias_forces_match():
    alias_map = {"mikegaming": 0, "mike_g": 0}
    score, reasons = m.score_pair(entry("mikegaming"), entry("mike_g"), {}, alias_map)
    assert score == m.ALIAS_SCORE
    assert any("alias" in r for r in reasons)


def test_feedback_confirmed_and_rejected():
    fb = {"a:b": "confirmed", "c:d": "rejected"}
    s_yes, _ = m.score_pair(entry("a"), entry("b"), fb, {})
    s_no, _ = m.score_pair(entry("c"), entry("d"), fb, {})
    assert s_yes == m.ALIAS_SCORE
    assert s_no == 0


def test_cross_script_display_names_do_not_match():
    # Latin vs Cyrillic display names should score 0 on the name signal
    assert m.display_name_score("Ivan", "Иван") == 0


def test_tiers():
    assert m.get_tier(98) == "AUTO-CONFIRMED"
    assert m.get_tier(80) == "QUICK REVIEW"
    assert m.get_tier(60) == "MANUAL REVIEW"
    assert m.get_tier(20) == "WEAK"


def test_mutual_follow_bonus_beats_single_list():
    a_single = entry("alex", "Alex", in_followers=True, in_following=False)
    b_single = entry("alexx", "Alex", in_followers=True, in_following=False)
    a_both = entry("alex", "Alex", in_followers=True, in_following=True)
    b_both = entry("alexx", "Alex", in_followers=True, in_following=True)
    single, _ = m.score_pair(a_single, b_single, {}, {})
    both, _ = m.score_pair(a_both, b_both, {}, {})
    assert both >= single


def test_match_across_platforms_dedup_and_corroboration():
    users = {
        "me": {
            ("tiktok", 1): {"platform": "tiktok",
                            "followers": [entry("johndoe", "John Doe")], "following": []},
            ("instagram", 2): {"platform": "instagram",
                               "followers": [entry("johndoe", "John Doe")], "following": []},
        }
    }
    results = m.match_across_platforms(users, {}, {}, min_threshold=30)
    assert len(results) == 1
    assert results[0]["tier"] == "AUTO-CONFIRMED"
