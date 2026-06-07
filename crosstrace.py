import os
import sys
import json
import csv
import argparse
from datetime import datetime

from parser import load_ignorelist, load_aliases, load_all_users, load_target
from matcher import match_across_platforms, find_target, discovery_mode, load_feedback, find_unmatched, suggest_aliases, get_persistent_connections
from known_info import load_known_info
from reviewer import run_review, run_discovery_review, run_unmatched_review, load_famous
from history import record_session, compare_sessions, get_score_history


COLORS = {
    "green":  "\033[92m",
    "yellow": "\033[93m",
    "orange": "\033[33m",
    "grey":   "\033[90m",
    "white":  "\033[97m",
    "cyan":   "\033[96m",
    "red":    "\033[91m",
    "reset":  "\033[0m"
}


def c(text, color):
    return f"{COLORS.get(color, '')}{text}{COLORS['reset']}"


def tier_color(tier):
    if tier == "AUTO-CONFIRMED":
        return "green"
    elif tier == "QUICK REVIEW":
        return "yellow"
    elif tier == "MANUAL REVIEW":
        return "orange"
    elif tier == "WEAK":
        return "grey"
    elif tier in ("FAMOUS", "REJECTED"):
        return "grey"
    return "white"


def load_config(path="config.json"):
    defaults = {
        "min_match_threshold": 30,
        "output_format": ["csv", "json"],
        "review_mode": True,
        "top_results": 5,
        "quick_mode": False,
        "quick_threshold": 70
    }
    if not os.path.exists(path):
        return defaults
    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return {**defaults, **data}
        except json.JSONDecodeError:
            return defaults


def get_session_name():
    default = datetime.now().strftime("session_%Y%m%d_%H%M%S")
    print(f"\n  name this session (leave blank for '{default}'):")
    name = input("  > ").strip()
    return name if name else default


def get_target_interactive():
    print("\n  enter target username (leave blank for discovery mode):")
    val = input("  > ").strip().lower()
    return val if val else None


def save_results_json(results, path):
    serialisable = []
    for r in results:
        row = {k: v for k, v in r.items()}
        if "seen_by" in row and isinstance(row["seen_by"], set):
            row["seen_by"] = list(row["seen_by"])
        if "platforms" in row and isinstance(row["platforms"], set):
            row["platforms"] = list(row["platforms"])
        serialisable.append(row)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(serialisable, f, indent=2)


def save_results_csv(results, path, mode="target"):
    if not results:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)

    if mode == "discovery":
        fields = ["username", "display_name", "platforms", "seen_by", "overlap_count", "score", "tier"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for r in results:
                entry = r.get("entry", {})
                writer.writerow({
                    "username": entry.get("username", ""),
                    "display_name": entry.get("display_name", ""),
                    "platforms": ", ".join(r.get("platforms", [])),
                    "seen_by": ", ".join(r.get("seen_by", [])),
                    "overlap_count": r.get("overlap_count", ""),
                    "score": r.get("score", ""),
                    "tier": r.get("tier", "")
                })
    else:
        fields = ["user", "username_a", "display_name_a", "platform_a",
                  "username_b", "display_name_b", "platform_b", "score", "tier", "reasons"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for r in results:
                ea = r.get("entry_a", {})
                eb = r.get("entry_b", {})
                writer.writerow({
                    "user": r.get("user", ""),
                    "username_a": ea.get("username", ""),
                    "display_name_a": ea.get("display_name", ""),
                    "platform_a": ea.get("platform", ""),
                    "username_b": eb.get("username", ""),
                    "display_name_b": eb.get("display_name", ""),
                    "platform_b": eb.get("platform", ""),
                    "score": r.get("score", ""),
                    "tier": r.get("tier", ""),
                    "reasons": ", ".join(r.get("reasons", []))
                })


def print_summary(results, mode="target", top_n=5):
    print("\n" + "=" * 60)
    print(c("  CROSSTRACE — RESULTS SUMMARY", "white"))
    print("=" * 60)

    if mode == "discovery":
        tiers = {"AUTO-CONFIRMED": [], "QUICK REVIEW": [], "MANUAL REVIEW": [], "WEAK": [], "FAMOUS": [], "REJECTED": []}
        for r in results:
            tiers.setdefault(r.get("tier", "WEAK"), []).append(r)

        print(f"\n  Mode: Discovery\n")
        for tier, items in tiers.items():
            if items and tier not in ("REJECTED", "FAMOUS"):
                print(f"  {c(tier, tier_color(tier))}: {len(items)}")
        print()

        visible = [r for r in results if r.get("tier") not in ("REJECTED", "WEAK", "FAMOUS")]
        top = sorted(visible, key=lambda x: (len(x.get("seen_by", [])), x.get("score", 0)), reverse=True)[:top_n]
        if top:
            print(c(f"  TOP {top_n} MOST PREVALENT", "cyan"))
            print()
            for r in top:
                entry = r.get("entry", {})
                u = entry.get("username", "???")
                d = entry.get("display_name", "")
                seen_by = r.get("seen_by", [])
                line = f"  {c(u, 'white')}"
                if d:
                    line += f" / {d}"
                line += f"  |  seen in {len(seen_by)} list(s): {', '.join(seen_by)}"
                print(line)
            print()

        for r in results:
            if r.get("tier") in ("REJECTED", "WEAK", "FAMOUS"):
                continue
            entry = r.get("entry", {})
            u = entry.get("username", "???")
            d = entry.get("display_name", "")
            platforms = ", ".join(r.get("platforms", []))
            seen_by = ", ".join(r.get("seen_by", []))
            score = r.get("score", 0)
            tier = r.get("tier", "")
            line = f"  {c(u, tier_color(tier))}"
            if d:
                line += f" / {d}"
            line += f"  |  {platforms}  |  followed by: {seen_by}  |  {score}%  |  {c(tier, tier_color(tier))}"
            print(line)

    else:
        tiers = {"AUTO-CONFIRMED": [], "QUICK REVIEW": [], "MANUAL REVIEW": [], "WEAK": [], "FAMOUS": [], "REJECTED": []}
        for r in results:
            tiers.setdefault(r.get("tier", "WEAK"), []).append(r)

        total = sum(len(v) for v in tiers.values())
        print(f"\n  Total pairs analysed: {total}")
        for tier, items in tiers.items():
            if tier not in ("REJECTED", "FAMOUS"):
                print(f"  {c(tier, tier_color(tier))}: {len(items)}")
        print()

        person_lists = {}
        entry_labels = {}
        for r in results:
            if r.get("tier") in ("REJECTED", "FAMOUS", "WEAK"):
                continue
            for side in ("entry_a", "entry_b"):
                e = r.get(side, {})
                key = e.get("username") or e.get("display_name", "").lower()
                plat = e.get("platform", "?")
                if key:
                    if key not in person_lists:
                        person_lists[key] = set()
                    person_lists[key].add(plat)
                    if key not in entry_labels:
                        u = e.get("username", "???")
                        d = e.get("display_name", "")
                        entry_labels[key] = f"{u}" + (f" / {d}" if d else "")

        top = sorted(person_lists.items(), key=lambda x: len(x[1]), reverse=True)[:top_n]
        if top:
            print(c(f"  TOP {top_n} MOST PREVALENT", "cyan"))
            print()
            for key, platforms in top:
                label = entry_labels.get(key, key)
                print(f"  {c(label, 'white')}  |  seen in {len(platforms)} platform(s): {', '.join(sorted(platforms))}")
            print()

        for tier in ("AUTO-CONFIRMED", "QUICK REVIEW", "MANUAL REVIEW"):
            if not tiers[tier]:
                continue
            print(c(f"  {tier}", tier_color(tier)))
            print()
            for r in tiers[tier]:
                ea = r.get("entry_a", {})
                eb = r.get("entry_b", {})
                ua = ea.get("username", "???")
                ub = eb.get("username", "???")
                da = ea.get("display_name", "")
                db = eb.get("display_name", "")
                pa = ea.get("platform", "?")
                pb = eb.get("platform", "?")
                score = r.get("score", 0)
                reasons = r.get("reasons", [])
                a_str = f"{c(ua, 'white')}" + (f" / {da}" if da else "") + f" ({pa})"
                b_str = f"{c(ub, 'white')}" + (f" / {db}" if db else "") + f" ({pb})"
                print(f"  {a_str}  →  {b_str}  |  {c(str(score) + '%', tier_color(tier))}")
                if reasons:
                    print(f"    {c('why:', 'grey')} {', '.join(reasons)}")
            print()

    print("=" * 60 + "\n")


def print_stats(results, all_users, mode, unmatched=None):
    print("=" * 60)
    print(c("  CROSSTRACE — SESSION STATS", "white"))
    print("=" * 60)

    total_folders = len(all_users)
    total_lists = sum(len(v) for v in all_users.values())
    confirmed = [r for r in results if r.get("tier") == "AUTO-CONFIRMED"]
    famous_count = len([r for r in results if r.get("tier") == "FAMOUS"])

    print(f"\n  folders loaded:       {total_folders}")
    print(f"  total lists loaded:   {total_lists}")
    print(f"  confirmed matches:    {c(str(len(confirmed)), 'green')}")
    print(f"  famous filtered out:  {famous_count}")

    if unmatched:
        kept = len([r for r in unmatched if r.get("tier") == "UNMATCHED_KEPT"])
        print(f"  single-platform kept: {kept}")

    if mode == "target" and confirmed:
        platform_counts = {}
        for r in confirmed:
            for side in ("entry_a", "entry_b"):
                p = r.get(side, {}).get("platform", "unknown")
                platform_counts[p] = platform_counts.get(p, 0) + 1
        most_active = max(platform_counts, key=platform_counts.get)
        print(f"  most active platform: {c(most_active, 'cyan')} ({platform_counts[most_active]} confirmed entries)")

    if mode == "discovery":
        person_counts = {}
        for r in results:
            if r.get("tier") in ("REJECTED", "FAMOUS", "WEAK"):
                continue
            for person in r.get("seen_by", []):
                person_counts[person] = person_counts.get(person, 0) + 1
        if person_counts:
            most_connected = max(person_counts, key=person_counts.get)
            print(f"  most connected user:  {c(most_connected, 'cyan')} ({person_counts[most_connected]} shared matches)")

    persistent = get_persistent_connections(min_appearances=2)
    if persistent:
        print(c("  PERSISTENT CONNECTIONS (appear across multiple sessions)", "cyan"))
        print()
        for p in persistent[:5]:
            print(f"  {c(p['key'], 'white')}  |  seen in {p['appearances']} session(s)  |  avg score {p['avg_score']}%")
        print()

    print("\n" + "=" * 60 + "\n")


def export_summary_report(results, unmatched, session_name, mode, output_dir, top_n=5):
    path = os.path.join(output_dir, "summary.md")
    lines = []
    lines.append(f"# CrossTrace — {session_name}")
    lines.append(f"Mode: {mode}\n")

    confirmed = [r for r in results if r.get("tier") == "AUTO-CONFIRMED"]
    review = [r for r in results if r.get("tier") in ("QUICK REVIEW", "MANUAL REVIEW")]
    weak = [r for r in results if r.get("tier") == "WEAK"]
    famous = [r for r in results if r.get("tier") == "FAMOUS"]

    lines.append(f"Auto-confirmed: {len(confirmed)}")
    lines.append(f"Review queue: {len(review)}")
    lines.append(f"Weak: {len(weak)}")
    lines.append(f"Famous filtered: {len(famous)}\n")

    if mode == "discovery":
        visible = [r for r in results if r.get("tier") not in ("REJECTED", "WEAK", "FAMOUS")]
        top = sorted(visible, key=lambda x: (len(x.get("seen_by", [])), x.get("score", 0)), reverse=True)[:top_n]
        if top:
            lines.append(f"## Top {top_n} Most Prevalent\n")
            for r in top:
                entry = r.get("entry", {})
                u = entry.get("username", "???")
                d = entry.get("display_name", "")
                seen_by = r.get("seen_by", [])
                line = f"  {u}"
                if d:
                    line += f" / {d}"
                line += f" — seen in {len(seen_by)} list(s): {', '.join(seen_by)}"
                lines.append(line)
            lines.append("")

        lines.append("## All Results\n")
        for r in results:
            if r.get("tier") in ("REJECTED", "WEAK", "FAMOUS"):
                continue
            entry = r.get("entry", {})
            u = entry.get("username", "???")
            d = entry.get("display_name", "")
            seen_by = ", ".join(r.get("seen_by", []))
            score = r.get("score", 0)
            tier = r.get("tier", "")
            line = f"  {u}"
            if d:
                line += f" / {d}"
            line += f" | followed by: {seen_by} | {score}% | {tier}"
            lines.append(line)
    else:
        if confirmed:
            lines.append("## Auto-Confirmed\n")
            for r in confirmed:
                ea = r.get("entry_a", {})
                eb = r.get("entry_b", {})
                ua = ea.get("username", "???")
                ub = eb.get("username", "???")
                pa = ea.get("platform", "?")
                pb = eb.get("platform", "?")
                score = r.get("score", 0)
                reasons = r.get("reasons", [])
                lines.append(f"  {ua} ({pa}) → {ub} ({pb}) | {score}%")
                if reasons:
                    lines.append(f"  why: {', '.join(reasons)}")
            lines.append("")

        if review:
            lines.append("## Review Queue\n")
            for r in review:
                ea = r.get("entry_a", {})
                eb = r.get("entry_b", {})
                ua = ea.get("username", "???")
                ub = eb.get("username", "???")
                pa = ea.get("platform", "?")
                pb = eb.get("platform", "?")
                score = r.get("score", 0)
                tier = r.get("tier", "")
                reasons = r.get("reasons", [])
                lines.append(f"  {ua} ({pa}) → {ub} ({pb}) | {score}% | {tier}")
                if reasons:
                    lines.append(f"  why: {', '.join(reasons)}")
            lines.append("")

    if unmatched:
        kept = [r for r in unmatched if r.get("tier") == "UNMATCHED_KEPT"]
        if kept:
            lines.append("## Single-Platform (Kept)\n")
            for r in kept:
                entry = r.get("entry", {})
                u = entry.get("username", "???")
                d = entry.get("display_name", "")
                platform = r.get("platform", "unknown")
                line = f"  {u}"
                if d:
                    line += f" / {d}"
                line += f" ({platform} only)"
                lines.append(line)

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  summary report saved to {path}")


def handle_alias_suggestions(results, aliases_path="aliases.txt"):
    suggestions = suggest_aliases(results)
    if not suggestions:
        return

    new_suggestions = []
    existing = open(aliases_path, "r", encoding="utf-8").read() if os.path.exists(aliases_path) else ""
    for u1, u2 in suggestions:
        if u1 not in existing and u2 not in existing:
            new_suggestions.append((u1, u2))

    if not new_suggestions:
        return

    print(f"\n  {len(new_suggestions)} alias suggestion(s) based on confirmed matches:\n")
    approved = []
    for u1, u2 in new_suggestions:
        print(f"  {u1} = {u2}")
        ans = input("  add to aliases.txt? (y/n): ").strip().lower()
        if ans == "y":
            approved.append(f"{u1} = {u2}")
        print()

    if approved:
        with open(aliases_path, "a", encoding="utf-8") as f:
            for line in approved:
                f.write(f"\n{line}")
        print(f"  {len(approved)} alias(es) saved to {aliases_path}\n")


def export_confirmed_as_aliases(results, aliases_path="aliases.txt"):
    confirmed = [r for r in results if r.get("tier") == "AUTO-CONFIRMED"]
    pairs = []
    existing = open(aliases_path, "r", encoding="utf-8").read() if os.path.exists(aliases_path) else ""
    for r in confirmed:
        ea = r.get("entry_a", {})
        eb = r.get("entry_b", {})
        u1 = ea.get("username")
        u2 = eb.get("username")
        if u1 and u2 and u1 != u2 and u1 not in existing and u2 not in existing:
            pairs.append(f"{u1} = {u2}")
    if pairs:
        with open(aliases_path, "a", encoding="utf-8") as f:
            for line in pairs:
                f.write(f"\n{line}")
        print(f"  exported {len(pairs)} confirmed match(es) to {aliases_path}")
    else:
        print("  no new confirmed pairs to export as aliases")


def write_outputs(confirmed, review, weak, config, mode, output_dir):
    fmt = config.get("output_format", ["csv"])
    os.makedirs(output_dir, exist_ok=True)

    if "json" in fmt:
        save_results_json(confirmed, os.path.join(output_dir, "results_confirmed.json"))
        save_results_json(review, os.path.join(output_dir, "results_review.json"))
        save_results_json(weak, os.path.join(output_dir, "results_weak.json"))

    if "csv" in fmt:
        save_results_csv(confirmed, os.path.join(output_dir, "results_confirmed.csv"), mode=mode)
        save_results_csv(review, os.path.join(output_dir, "results_review.csv"), mode=mode)
        save_results_csv(weak, os.path.join(output_dir, "results_weak.csv"), mode=mode)

    print(f"  results written to {output_dir}/")


def cmd_search(username):
    ignore = load_ignorelist()
    all_users = load_all_users(ignore_set=ignore)
    username = username.lower()
    found = []
    for user_name, user_data in all_users.items():
        for platform_num, data in user_data.items():
            platform = data["platform"]
            for entry in data["followers"] + data["following"]:
                u = (entry.get("username") or "").lower()
                d = (entry.get("display_name") or "").lower()
                if username in u or username in d:
                    found.append((user_name, platform, entry))
    if not found:
        print(f"\n  '{username}' not found in any list\n")
        return
    print(f"\n  found '{username}' in {len(found)} list(s):\n")
    for user_name, platform, entry in found:
        u = entry.get("username", "???")
        d = entry.get("display_name", "")
        print(f"  {user_name} / {platform}  →  {u}" + (f" / {d}" if d else ""))
    print()


def cmd_compare(session_a, session_b):
    diff, err = compare_sessions(session_a, session_b)
    if err:
        print(f"\n  error: {err}\n")
        return

    print(f"\n  comparing '{session_a}' vs '{session_b}'\n")

    if diff["new"]:
        print(c(f"  new in {session_b}:", "green"))
        for item in diff["new"]:
            print(f"    {item['key']}  {item['score']}%")
        print()

    if diff["gone"]:
        print(c(f"  gone from {session_b}:", "red"))
        for item in diff["gone"]:
            print(f"    {item['key']}  was {item['score']}%")
        print()

    if diff["changed"]:
        print(c("  score changes:", "yellow"))
        for item in diff["changed"]:
            delta_str = f"+{item['delta']}" if item['delta'] > 0 else str(item['delta'])
            print(f"    {item['key']}  {item['before']}% → {item['after']}%  ({c(delta_str, 'green' if item['delta'] > 0 else 'red')})")
        print()

    if not diff["new"] and not diff["gone"] and not diff["changed"]:
        print("  no significant differences found\n")


def cmd_summary(session_name):
    path = os.path.join("output", session_name, "summary.md")
    if not os.path.exists(path):
        print(f"\n  no summary found for session '{session_name}'\n")
        return
    with open(path, "r", encoding="utf-8") as f:
        print(f.read())


def cmd_score_history(username):
    timeline = get_score_history(username)
    if not timeline:
        print(f"\n  no history found for '{username}'\n")
        return
    print(f"\n  score history for '{username}':\n")
    for entry in timeline:
        print(f"  {entry['session']}  {entry['timestamp'][:10]}  {entry['score']}%")
    print()


def main():
    parser = argparse.ArgumentParser(prog="crosstrace", add_help=True)
    parser.add_argument("--no-review", action="store_true", help="skip review queue entirely")
    parser.add_argument("--search", metavar="USERNAME", help="search for a username across all lists")
    parser.add_argument("--compare", nargs=2, metavar=("SESSION_A", "SESSION_B"), help="compare two sessions")
    parser.add_argument("--summary", metavar="SESSION", help="reprint summary for a previous session")
    parser.add_argument("--history", metavar="USERNAME", help="show score history for a username across sessions")
    parser.add_argument("--export-aliases", action="store_true", help="export all confirmed matches to aliases.txt")
    args = parser.parse_args()

    if args.search:
        cmd_search(args.search)
        return

    if args.compare:
        cmd_compare(args.compare[0], args.compare[1])
        return

    if args.summary:
        cmd_summary(args.summary)
        return

    if args.history:
        cmd_score_history(args.history)
        return

    config = load_config()
    ignore = load_ignorelist()
    aliases = load_aliases()
    feedback = load_feedback()

    session_name = get_session_name()
    output_dir = os.path.join("output", session_name)

    target = load_target()
    if target is None:
        target = get_target_interactive()

    known_hints = load_known_info(config, target=target)

    print("\n  loading user data...")
    all_users = load_all_users(ignore_set=ignore)

    if not all_users:
        print("  no user data found in data/users/")
        return

    mode = "target" if target else "discovery"
    print(f"  mode: {c(mode, 'cyan')}")
    if target:
        print(f"  target: {c(target, 'white')}")
    print()

    if mode == "target":
        print("  searching for target across all lists...")
        target_matches = find_target(target, all_users, aliases, feedback)
        if target_matches:
            seen_display = set()
            print(f"  found {len(target_matches)} potential target match(es)\n")
            for m in target_matches[:5]:
                entry = m["entry"]
                u = entry.get("username", "???")
                d = entry.get("display_name", "")
                plat = m["platform"]
                score = m["score"]
                tier = m["tier"]
                display_key = (u, plat)
                if display_key in seen_display:
                    continue
                seen_display.add(display_key)
                print(f"    {c(u, tier_color(tier))}" + (f" / {d}" if d else "") + f"  ({plat})  {score}%  {c(tier, tier_color(tier))}")
            print()
        else:
            print("  target not found in any list\n")

        total = sum(
            len(data["followers"]) + len(data["following"])
            for user_data in all_users.values()
            for data in user_data.values()
        )
        print(f"  matching {total} entries across platforms...")
        quick_threshold = config["quick_threshold"] if config.get("quick_mode") else None
        results = match_across_platforms(all_users, aliases, feedback, config["min_match_threshold"], known_hints=known_hints, quick_threshold=quick_threshold)

    else:
        total = sum(
            len(data["followers"]) + len(data["following"])
            for user_data in all_users.values()
            for data in user_data.values()
        )
        print(f"  running discovery across {total} entries...")
        results = discovery_mode(all_users, aliases, feedback, config["min_match_threshold"])

    if not results:
        print("  no matches found above threshold")
        return

    famous = load_famous()

    do_review = config.get("review_mode") and not args.no_review

    if do_review:
        if mode == "discovery":
            results = run_discovery_review(results, feedback)
        else:
            results = run_review(results, feedback, famous_path="famous.json")

    if mode == "target":
        print("  finding single-platform unmatched entries...")
        unmatched = find_unmatched(all_users, aliases, feedback, config["min_match_threshold"])
        if unmatched and do_review:
            unmatched = run_unmatched_review(unmatched, feedback, famous)
        elif not unmatched:
            print("  no unmatched entries found.\n")
    else:
        unmatched = []

    print_summary(results, mode=mode, top_n=config.get("top_results", 5))

    kept = [r for r in unmatched if r.get("tier") == "UNMATCHED_KEPT"]
    if kept:
        print(c("  UNMATCHED (single platform, kept)", "orange"))
        print()
        for r in kept:
            entry = r.get("entry", {})
            u = entry.get("username", "???")
            d = entry.get("display_name") or ""
            platform = r.get("platform", "unknown")
            print(f"  {c(u, 'white')}" + (f" / {d}" if d else "") + f"  ({platform} only)")
        print()

    print_stats(results, all_users, mode, unmatched=unmatched)

    confirmed = [r for r in results if r.get("tier") == "AUTO-CONFIRMED"]
    review_list = [r for r in results if r.get("tier") in ("QUICK REVIEW", "MANUAL REVIEW")]
    weak = [r for r in results if r.get("tier") == "WEAK"]

    write_outputs(confirmed, review_list, weak, config, mode, output_dir)
    export_summary_report(results, unmatched, session_name, mode, output_dir, top_n=config.get("top_results", 5))
    record_session(session_name, mode, target, results, output_dir)

    if args.export_aliases:
        export_confirmed_as_aliases(results)
    elif do_review:
        handle_alias_suggestions(results)

    print(c("  done.\n", "green"))


if __name__ == "__main__":
    main()