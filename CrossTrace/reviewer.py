import json
import os

from matcher import save_feedback

WARNING = """
╔══════════════════════════════════════════════════════════════╗
║  WARNING: Check each manual case carefully before pressing Y ║
║  This tool can make mistakes.                                ║
╚══════════════════════════════════════════════════════════════╝
"""


def load_famous(path="famous.json"):
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        try:
            data = json.load(f)
            return set(data)
        except json.JSONDecodeError:
            return set()


def save_famous(famous, path="famous.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(list(famous), f, indent=2)


def is_famous(entry, famous):
    u = entry.get("username", "")
    d = entry.get("display_name") or ""
    return u in famous or d.lower() in famous


def format_entry(entry, label):
    u = entry.get("username", "???")
    d = entry.get("display_name", "")
    platform = entry.get("platform", "unknown")
    line = f"  {label}: {u}"
    if d:
        line += f" / {d}"
    line += f" ({platform})"
    return line


def prompt_choice(prompt, options):
    while True:
        ans = input(prompt).strip()
        if ans in options:
            return ans
        print(f"  enter {', '.join(options)}")


def run_review(results, feedback, feedback_path="feedback.json", famous_path="famous.json"):
    famous = load_famous(famous_path)

    filtered = []
    for r in results:
        ea = r.get("entry_a", {})
        eb = r.get("entry_b", {})
        if is_famous(ea, famous) or is_famous(eb, famous):
            r["tier"] = "FAMOUS"
            r["reviewed"] = True
        filtered.append(r)

    review_queue = [r for r in filtered if r["tier"] in ("MANUAL REVIEW", "QUICK REVIEW")]

    if not review_queue:
        print("\nnothing to review.")
        return filtered

    print(WARNING)
    print(f"  {len(review_queue)} case(s) to review\n")

    for i, match in enumerate(review_queue):
        entry_a = match["entry_a"]
        entry_b = match["entry_b"]
        score = match["score"]
        tier = match["tier"]
        reasons = match.get("reasons", [])

        print(f"[{i + 1}/{len(review_queue)}] {tier} — {score}%")
        print(format_entry(entry_a, "A"))
        print(format_entry(entry_b, "B"))
        if reasons:
            print(f"  why: {', '.join(reasons)}")
        print()
        print("  (1) Yes — same person")
        print("  (2) No — different people")
        print("  (3) Famous / not important — skip")
        print()

        choice = prompt_choice("  choice: ", ["1", "2", "3"])

        u1 = entry_a.get("username")
        u2 = entry_b.get("username")

        if choice == "1":
            if u1 and u2:
                feedback[f"{u1}:{u2}"] = "confirmed"
            match["tier"] = "AUTO-CONFIRMED"
            match["score"] = 100
            match["reviewed"] = True
            match["confirmed_by_user"] = True

        elif choice == "2":
            if u1 and u2:
                feedback[f"{u1}:{u2}"] = "rejected"
            match["tier"] = "REJECTED"
            match["reviewed"] = True

        elif choice == "3":
            if u1:
                famous.add(u1)
            if u2:
                famous.add(u2)
            d1 = entry_a.get("display_name", "")
            d2 = entry_b.get("display_name", "")
            if d1:
                famous.add(d1.lower())
            if d2:
                famous.add(d2.lower())
            match["tier"] = "FAMOUS"
            match["reviewed"] = True

        print()

    save_feedback(feedback, feedback_path)
    save_famous(famous, famous_path)
    print("  feedback saved.\n")

    return filtered


def run_discovery_review(ranked, feedback, feedback_path="feedback.json", famous_path="famous.json"):
    famous = load_famous(famous_path)

    filtered = []
    for r in ranked:
        entry = r.get("entry", {})
        if is_famous(entry, famous):
            r["tier"] = "FAMOUS"
            r["reviewed"] = True
        filtered.append(r)

    review_queue = [r for r in filtered if r["tier"] in ("MANUAL REVIEW", "QUICK REVIEW")]

    if not review_queue:
        print("\nnothing to review.")
        return filtered

    print(WARNING)
    print(f"  {len(review_queue)} case(s) to review\n")

    for i, match in enumerate(review_queue):
        entry = match["entry"]
        u = entry.get("username", "???")
        d = entry.get("display_name", "")
        platforms = ", ".join(match.get("platforms", []))
        seen_by = ", ".join(match.get("seen_by", []))
        score = match["score"]
        tier = match["tier"]

        print(f"[{i + 1}/{len(review_queue)}] {tier} — {score}%")
        print(f"  user: {u}" + (f" / {d}" if d else ""))
        print(f"  seen on: {platforms}")
        print(f"  followed by: {seen_by}")
        print()
        print("  (1) Yes — significant person")
        print("  (2) No — not relevant")
        print("  (3) Famous / not important — skip")
        print()

        choice = prompt_choice("  choice: ", ["1", "2", "3"])

        if choice == "1":
            match["confirmed"] = True
            match["reviewed"] = True

        elif choice == "2":
            match["confirmed"] = False
            match["reviewed"] = True
            match["tier"] = "REJECTED"

        elif choice == "3":
            if u:
                famous.add(u)
            if d:
                famous.add(d.lower())
            match["tier"] = "FAMOUS"
            match["reviewed"] = True

        print()

    save_feedback(feedback, feedback_path)
    save_famous(famous, famous_path)
    print("  feedback saved.\n")

    return filtered


def run_unmatched_review(unmatched, feedback, famous, feedback_path="feedback.json", famous_path="famous.json"):
    queue = [r for r in unmatched if not is_famous(r.get("entry", {}), famous)]

    if not queue:
        print("\n  no unmatched entries to review.")
        return unmatched

    print(f"\n  {len(queue)} unmatched (single-platform) entr{'y' if len(queue) == 1 else 'ies'} to review\n")

    for i, match in enumerate(queue):
        entry = match["entry"]
        u = entry.get("username", "???")
        d = entry.get("display_name") or ""
        platform = match.get("platform", "unknown")

        print(f"[{i + 1}/{len(queue)}] UNMATCHED — {platform} only")
        print(f"  user: {u}" + (f" / {d}" if d else ""))
        print()
        print("  (1) Keep — this person is relevant")
        print("  (2) Ignore — not relevant")
        print("  (3) Famous / not important — skip forever")
        print()

        choice = prompt_choice("  choice: ", ["1", "2", "3"])

        if choice == "1":
            match["tier"] = "UNMATCHED_KEPT"
            match["reviewed"] = True
        elif choice == "2":
            match["tier"] = "UNMATCHED_IGNORED"
            match["reviewed"] = True
        elif choice == "3":
            if u:
                famous.add(u)
            if d:
                famous.add(d.lower())
            match["tier"] = "FAMOUS"
            match["reviewed"] = True

        print()

    save_feedback(feedback, feedback_path)
    save_famous(famous, famous_path)

    return unmatched
