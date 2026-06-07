import os
import re


HARDCODED_IGNORE = {"following", "followers", "follow back", "follow"}


def load_ignorelist(path="ignorelist.txt"):
    ignore = set(HARDCODED_IGNORE)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip().lower()
                if line:
                    ignore.add(line)
    return ignore


def load_aliases(path="aliases.txt"):
    alias_map = {}
    if not os.path.exists(path):
        return alias_map
    with open(path, "r", encoding="utf-8") as f:
        for group_id, line in enumerate(f):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip().lower() for p in line.split("=")]
            for part in parts:
                if part:
                    alias_map[part] = group_id
    return alias_map


def is_username(line, min_length=2):
    line = line.strip()
    if not line or line.isdigit() or " " in line:
        return False
    if not re.search(r'[a-zA-Z0-9]', line):
        return False
    if len(line) < min_length:
        return False
    return bool(re.match(r'^[\w.\-]+$', line))


def is_display_name(line):
    line = line.strip()
    if not line or line.isdigit():
        return False
    if " " in line:
        return True
    return not bool(re.match(r'^[\w.\-]+$', line))


def parse_file(filepath, ignore_set):
    with open(filepath, "r", encoding="utf-8") as f:
        raw_lines = [line.strip() for line in f.readlines()]

    filtered = [l for l in raw_lines if l and l.lower() not in ignore_set]

    entries = []
    i = 0
    while i < len(filtered):
        line = filtered[i]
        next_line = filtered[i + 1] if i + 1 < len(filtered) else None
        username = None
        display_name = None

        if is_username(line):
            username = line.lower()
            if next_line and is_display_name(next_line) and next_line.lower() not in ignore_set:
                display_name = next_line
                i += 2
            else:
                i += 1
        elif is_display_name(line):
            display_name = line
            if next_line and is_username(next_line) and next_line.lower() not in ignore_set:
                username = next_line.lower()
                i += 2
            else:
                i += 1
        else:
            i += 1
            continue

        if username or display_name:
            entries.append({"username": username, "display_name": display_name})

    return entries


def get_platform_from_filename(filename):
    name = os.path.splitext(os.path.basename(filename))[0].lower()
    match = re.match(r'^([a-z]+)_(followers|following)(\d+)$', name)
    if match:
        return match.group(1), match.group(2), int(match.group(3))
    return "unknown", "unknown", 0


def load_all_users(users_dir="data/users", ignore_set=None):
    if ignore_set is None:
        ignore_set = load_ignorelist()

    all_users = {}

    if not os.path.exists(users_dir):
        print(f"users directory not found: {users_dir}")
        return all_users

    for user_folder in os.listdir(users_dir):
        user_path = os.path.join(users_dir, user_folder)
        if not os.path.isdir(user_path):
            continue

        all_users[user_folder] = {}

        for filename in os.listdir(user_path):
            if not filename.endswith(".txt"):
                continue

            filepath = os.path.join(user_path, filename)
            platform, list_type, number = get_platform_from_filename(filename)

            bucket_key = (platform, number)
            if bucket_key not in all_users[user_folder]:
                all_users[user_folder][bucket_key] = {
                    "platform": platform,
                    "followers": [],
                    "following": []
                }

            entries = parse_file(filepath, ignore_set)

            if list_type == "followers":
                all_users[user_folder][bucket_key]["followers"] = entries
            elif list_type == "following":
                all_users[user_folder][bucket_key]["following"] = entries

    return all_users


def load_target(path="target.txt"):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                return line.lower()
    return None