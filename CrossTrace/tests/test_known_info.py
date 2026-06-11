import known_info as ki


def test_extract_hints_mixed_case_handle_with_digits():
    # Regression: "John99" previously slipped through because the digit check
    # compared against the literal string "0123456789".
    hints = ki.extract_hints("possible handle: John99")
    assert "john99" in hints["usernames"]


def test_extract_hints_picks_up_platforms_and_handles():
    text = "old instagram: jdoe_99\nalso on tiktok as john.doe"
    hints = ki.extract_hints(text)
    assert "instagram" in hints["platforms"]
    assert "tiktok" in hints["platforms"]
    assert "jdoe_99" in hints["usernames"]
    assert "john.doe" in hints["usernames"]


def test_score_against_hints_exact_username():
    hints = {"usernames": {"johndoe"}, "display_names": set(), "platforms": set(), "raw_lines": []}
    boost, reasons = ki.score_against_hints({"username": "johndoe", "display_name": ""}, hints, exact_only=True)
    assert boost > 0
    assert any("known hint" in r for r in reasons)


def test_score_against_hints_exact_only_blocks_substring():
    hints = {"usernames": {"johndoe"}, "display_names": set(), "platforms": set(), "raw_lines": []}
    boost, _ = ki.score_against_hints({"username": "johndoe_backup", "display_name": ""}, hints, exact_only=True)
    assert boost == 0
