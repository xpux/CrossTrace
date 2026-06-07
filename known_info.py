import os
import re


USERNAME_PATTERN = re.compile(r'\b[\w][\w.\-]{2,29}\b')
PLATFORM_KEYWORDS = {"tiktok", "instagram", "twitter", "snapchat", "youtube", "facebook", "threads", "x"}
SKIP_WORDS = {
    "the", "and", "for", "with", "this", "that", "from", "they", "them",
    "have", "been", "were", "when", "what", "which", "will", "your", "their",
    "about", "also", "just", "like", "more", "some", "than", "then", "there",
    "these", "those", "into", "over", "after", "before", "because", "through",
    "following", "followers", "follow", "profile", "account", "username", "display",
    "name", "platform", "social", "media", "user", "known", "info", "notes",
    "target", "person", "real", "actual", "other", "possible", "maybe", "might"
}


def read_file(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def extract_hints(text):
    hints = {
        "usernames": set(),
        "display_names": set(),
        "platforms": set(),
        "raw_lines": []
    }

    lines = [l.strip() for l in text.splitlines() if l.strip()]

    for line in lines:
        lower = line.lower()

        for platform in PLATFORM_KEYWORDS:
            if platform in lower:
                hints["platforms"].add(platform)

        if " " in line and len(line) < 60:
            words = line.split()
            if 2 <= len(words) <= 5 and not any(w.lower() in SKIP_WORDS for w in words):
                hints["display_names"].add(line.strip())

        for match in USERNAME_PATTERN.finditer(line):
            candidate = match.group()
            if candidate.lower() not in SKIP_WORDS and len(candidate) >= 3:
                if any(c in candidate for c in ("_", ".", "0123456789")) or candidate.islower():
                    hints["usernames"].add(candidate.lower())

        hints["raw_lines"].append(line)

    return hints


def load_known_info(config, target=None):
    known_cfg = config.get("known_info", {})

    if not known_cfg.get("enabled", True):
        return None

    mode = known_cfg.get("mode", "global")
    global_path = known_cfg.get("global_path", "data/known")
    target_path_template = known_cfg.get("target_path", "data/known/{target}")

    paths_to_load = []

    if mode in ("global", "both"):
        paths_to_load.append(global_path)

    if mode in ("target", "both") and target:
        resolved = target_path_template.replace("{target}", target)
        paths_to_load.append(resolved)

    all_hints = {
        "usernames": set(),
        "display_names": set(),
        "platforms": set(),
        "raw_lines": []
    }

    loaded_any = False
    for folder in paths_to_load:
        if not os.path.exists(folder):
            continue
        if os.path.isfile(folder):
            files = [folder]
        else:
            files = [
                os.path.join(root, f)
                for root, _, filenames in os.walk(folder)
                for f in filenames
            ]

        for filepath in files:
            text = read_file(filepath)
            if not text:
                continue
            hints = extract_hints(text)
            all_hints["usernames"].update(hints["usernames"])
            all_hints["display_names"].update(hints["display_names"])
            all_hints["platforms"].update(hints["platforms"])
            all_hints["raw_lines"].extend(hints["raw_lines"])
            loaded_any = True
            print(f"  [known_info] loaded {filepath}")

    if not loaded_any:
        return None

    print(f"  [known_info] extracted {len(all_hints['usernames'])} username hint(s), "
          f"{len(all_hints['display_names'])} name hint(s), "
          f"{len(all_hints['platforms'])} platform hint(s)")

    return all_hints


def score_against_hints(entry, hints, boost=12, exact_only=False):
    if not hints:
        return 0, []

    reasons = []
    total_boost = 0

    u = (entry.get("username") or "").lower()
    d = (entry.get("display_name") or "").lower()

    for hint_u in hints["usernames"]:
        if hint_u == u:
            total_boost += boost
            reasons.append(f"username matches known hint '{hint_u}'")
            break
        elif not exact_only and len(hint_u) >= 4 and (hint_u in u or u in hint_u):
            total_boost += boost // 2
            reasons.append(f"username partially matches known hint '{hint_u}'")
            break

    for hint_d in hints["display_names"]:
        hint_lower = hint_d.lower()
        if hint_lower == d:
            total_boost += boost
            reasons.append(f"display name matches known hint '{hint_d}'")
            break
        elif not exact_only and len(hint_lower) >= 4 and (hint_lower in d or d in hint_lower):
            total_boost += boost // 2
            reasons.append(f"display name partially matches known hint '{hint_d}'")
            break

    return min(total_boost, boost * 2), reasons