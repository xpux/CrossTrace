import os
import json
from datetime import datetime


HISTORY_FILE = "history.json"


def load_history(path=HISTORY_FILE):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_history(history, path=HISTORY_FILE):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def record_session(session_name, mode, target, results, output_dir, path=HISTORY_FILE):
    history = load_history(path)

    scores = {}
    for r in results:
        if r.get("tier") in ("REJECTED", "FAMOUS", "WEAK"):
            continue
        for side in ("entry_a", "entry_b"):
            e = r.get(side, {})
            key = e.get("username") or (e.get("display_name") or "").lower()
            if key:
                scores[key] = max(scores.get(key, 0), r.get("score", 0))

    discovery_entries = []
    if mode == "discovery":
        for r in results:
            if r.get("tier") in ("REJECTED", "FAMOUS", "WEAK"):
                continue
            entry = r.get("entry", {})
            key = entry.get("username") or (entry.get("display_name") or "").lower()
            if key:
                scores[key] = r.get("score", 0)
                discovery_entries.append({
                    "key": key,
                    "seen_by": r.get("seen_by", []),
                    "platforms": r.get("platforms", [])
                })

    record = {
        "session": session_name,
        "timestamp": datetime.now().isoformat(),
        "mode": mode,
        "target": target,
        "output_dir": output_dir,
        "confirmed_count": len([r for r in results if r.get("tier") == "AUTO-CONFIRMED"]),
        "scores": scores
    }

    history.append(record)
    save_history(history, path)
    return record


def get_score_history(username, path=HISTORY_FILE):
    history = load_history(path)
    timeline = []
    for record in history:
        scores = record.get("scores", {})
        if username in scores:
            timeline.append({
                "session": record["session"],
                "timestamp": record["timestamp"],
                "score": scores[username]
            })
    return timeline


def compare_sessions(session_a, session_b, path=HISTORY_FILE):
    history = load_history(path)
    record_a = next((r for r in history if r["session"] == session_a), None)
    record_b = next((r for r in history if r["session"] == session_b), None)

    if not record_a or not record_b:
        missing = session_a if not record_a else session_b
        return None, f"session '{missing}' not found in history"

    scores_a = record_a.get("scores", {})
    scores_b = record_b.get("scores", {})

    all_keys = set(scores_a.keys()) | set(scores_b.keys())

    new_in_b = []
    gone_from_b = []
    score_changes = []

    for key in all_keys:
        in_a = key in scores_a
        in_b = key in scores_b
        if in_b and not in_a:
            new_in_b.append({"key": key, "score": scores_b[key]})
        elif in_a and not in_b:
            gone_from_b.append({"key": key, "score": scores_a[key]})
        else:
            delta = scores_b[key] - scores_a[key]
            if abs(delta) >= 5:
                score_changes.append({"key": key, "before": scores_a[key], "after": scores_b[key], "delta": delta})

    score_changes.sort(key=lambda x: abs(x["delta"]), reverse=True)

    return {
        "session_a": session_a,
        "session_b": session_b,
        "new": sorted(new_in_b, key=lambda x: x["score"], reverse=True),
        "gone": gone_from_b,
        "changed": score_changes
    }, None