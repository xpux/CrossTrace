"""
mutuals.py — find accounts that appear in BOTH a followers list and a
following list for the same platform (i.e. people who follow each other).

Works on the same data layout as the rest of CrossTrace:
data/users/<person>/<platform>_followers<N>.txt
data/users/<person>/<platform>_following<N>.txt

A "bucket" is one (platform, N) pair for one person — e.g. tiktok1.
"""

import csv
import json
import os


def find_mutual_buckets(all_users):
    """Return a list of buckets that have BOTH a followers and a following
    list loaded, across all people in all_users.

    Each item: {"user": str, "platform": str, "number": int,
                "followers": [...], "following": [...]}
    """
    buckets = []
    for user_folder, platforms in all_users.items():
        for (platform, number), data in platforms.items():
            if data.get("followers") and data.get("following"):
                buckets.append({
                    "user": user_folder,
                    "platform": platform,
                    "number": number,
                    "followers": data["followers"],
                    "following": data["following"],
                })
    return buckets


def compute_mutuals(bucket):
    """Compare a bucket's followers and following lists by username.

    Returns a sorted list of dicts: {"username", "display_name"} for every
    username present in both lists.
    """
    followers_by_user = {e["username"]: e for e in bucket["followers"] if e.get("username")}
    following_by_user = {e["username"]: e for e in bucket["following"] if e.get("username")}

    shared_usernames = set(followers_by_user) & set(following_by_user)

    mutuals = []
    for username in sorted(shared_usernames):
        f_entry = followers_by_user[username]
        g_entry = following_by_user[username]
        mutuals.append({
            "username": username,
            "display_name": f_entry.get("display_name") or g_entry.get("display_name") or "",
        })
    return mutuals


def mutuals_filename(bucket, ext):
    return f"mutuals_{bucket['user']}_{bucket['platform']}{bucket['number']}.{ext}"


def write_mutuals(bucket, mutuals, output_dir, formats=("csv", "json")):
    """Write mutuals for one bucket to output_dir. Returns list of paths written."""
    os.makedirs(output_dir, exist_ok=True)
    written = []

    if "csv" in formats:
        path = os.path.join(output_dir, mutuals_filename(bucket, "csv"))
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["username", "display_name"])
            for m in mutuals:
                writer.writerow([m["username"], m["display_name"]])
        written.append(path)

    if "json" in formats:
        path = os.path.join(output_dir, mutuals_filename(bucket, "json"))
        with open(path, "w", encoding="utf-8") as f:
            json.dump(mutuals, f, indent=2)
        written.append(path)

    return written


def run_mutuals(all_users, output_dir, formats=("csv", "json"), only_user=None, only_platform=None):
    """Run the mutuals comparison across all loaded users (or a filtered
    subset) and write results. Returns a summary list of dicts:
    {"user", "platform", "number", "count", "files": [...]}.

    Prints a short report to the console as it goes.
    """
    buckets = find_mutual_buckets(all_users)

    if only_user:
        buckets = [b for b in buckets if b["user"] == only_user]
    if only_platform:
        buckets = [b for b in buckets if b["platform"] == only_platform]

    if not buckets:
        print("\n  no platform has both a followers and a following list loaded.")
        print("  mutuals needs e.g. tiktok_followers1.txt AND tiktok_following1.txt for the same person.\n")
        return []

    summary = []
    print("\n  mutual followers (people who follow each other)\n")
    for bucket in buckets:
        mutuals = compute_mutuals(bucket)
        label = f"{bucket['user']} / {bucket['platform']}{bucket['number']}"

        if not mutuals:
            print(f"  {label}: 0 mutuals")
            summary.append({"user": bucket["user"], "platform": bucket["platform"],
                             "number": bucket["number"], "count": 0, "files": []})
            continue

        files = write_mutuals(bucket, mutuals, output_dir, formats)
        print(f"  {label}: {len(mutuals)} mutuals -> {', '.join(os.path.basename(p) for p in files)}")
        for m in mutuals:
            shown = f"{m['username']} ({m['display_name']})" if m["display_name"] else m["username"]
            print(f"      - {shown}")

        summary.append({"user": bucket["user"], "platform": bucket["platform"],
                         "number": bucket["number"], "count": len(mutuals), "files": files})

    print()
    return summary


def get_mutuals_menu_choice(buckets):
    """Interactive menu: let the user pick which bucket to run mutuals on.

    Returns (only_user, only_platform) filter, or (None, None) for "all".
    """
    print("\n  mutual followers / following comparison")
    print("  found the following followers+following pairs:\n")
    for i, b in enumerate(buckets, 1):
        print(f"    {i}. {b['user']} / {b['platform']}{b['number']}")
    print(f"    {len(buckets) + 1}. all of the above\n")

    try:
        choice = input("  > ").strip()
    except EOFError:
        choice = ""

    if not choice or not choice.isdigit():
        return None, None

    idx = int(choice)
    if idx == len(buckets) + 1 or idx < 1 or idx > len(buckets):
        return None, None

    chosen = buckets[idx - 1]
    return chosen["user"], chosen["platform"]
