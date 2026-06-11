import parser as p


def test_is_username_basic():
    assert p.is_username("johndoe_")
    assert p.is_username("john.doe")
    assert p.is_username("jane-smith")
    assert not p.is_username("John Doe")      # space → display name
    assert not p.is_username("12345")          # pure digits
    assert not p.is_username("a", min_length=2)


def test_is_display_name():
    assert p.is_display_name("John Doe")
    assert p.is_display_name("Renée Müller")   # non-word chars
    assert not p.is_display_name("johndoe_")   # plain handle
    assert not p.is_display_name("999")


def test_parse_pairs_username_then_display(tmp_path):
    f = tmp_path / "tiktok_followers1.txt"
    f.write_text("johndoe_\nJohn Doe\nFollowing\njane_smith\nJane Smith\n", encoding="utf-8")
    entries = p.parse_file(str(f), p.load_ignorelist())
    handles = {e["username"] for e in entries}
    assert "johndoe_" in handles
    assert "jane_smith" in handles
    john = next(e for e in entries if e["username"] == "johndoe_")
    assert john["display_name"] == "John Doe"


def test_ignorelist_strips_ui_text(tmp_path):
    f = tmp_path / "ig_followers1.txt"
    f.write_text("Follow\nFollowers\njohndoe\n", encoding="utf-8")
    entries = p.parse_file(str(f), p.load_ignorelist())
    usernames = {e["username"] for e in entries}
    assert "follow" not in usernames
    assert "followers" not in usernames
    assert "johndoe" in usernames


def test_get_platform_from_filename():
    assert p.get_platform_from_filename("tiktok_followers1.txt") == ("tiktok", "followers", 1)
    assert p.get_platform_from_filename("instagram_following2.txt") == ("instagram", "following", 2)
    assert p.get_platform_from_filename("badname.txt") == ("unknown", "unknown", 0)


def test_min_username_length_is_applied(tmp_path):
    f = tmp_path / "tiktok_followers1.txt"
    f.write_text("ab\nlongerhandle\n", encoding="utf-8")
    # with a high minimum, the 2-char handle should be dropped
    entries = p.parse_file(str(f), p.load_ignorelist(), min_username_length=5)
    handles = {e["username"] for e in entries}
    assert "ab" not in handles
    assert "longerhandle" in handles


def test_load_aliases_groups(tmp_path):
    f = tmp_path / "aliases.txt"
    f.write_text("# comment\nmikegaming = mike_g = mikeg\njohn = jdoe\n", encoding="utf-8")
    amap = p.load_aliases(str(f))
    assert amap["mikegaming"] == amap["mike_g"] == amap["mikeg"]
    assert amap["john"] == amap["jdoe"]
    assert amap["mikegaming"] != amap["john"]
