import json
import os
import unicodedata
from rapidfuzz import fuzz


PATTERN_BONUS = 15
BOTH_LISTS_BONUS = 8
MUTUAL_FOLLOW_BONUS = 12
ALIAS_SCORE = 100
FEEDBACK_PENALTY = 15



def detect_script(text):
    if not text:
        return "latin"
    scripts = {}
    for char in text:
        if char.isspace() or not char.isalpha():
            continue
        try:
            name = unicodedata.name(char, "")
            if "ARABIC" in name:
                scripts["arabic"] = scripts.get("arabic", 0) + 1
            elif "CJK" in name or "HIRAGANA" in name or "KATAKANA" in name:
                scripts["cjk"] = scripts.get("cjk", 0) + 1
            elif "CYRILLIC" in name:
                scripts["cyrillic"] = scripts.get("cyrillic", 0) + 1
            elif "HEBREW" in name:
                scripts["hebrew"] = scripts.get("hebrew", 0) + 1
            elif "HANGUL" in name:
                scripts["hangul"] = scripts.get("hangul", 0) + 1
            elif "LATIN" in name or "DIGIT" in name:
                scripts["latin"] = scripts.get("latin", 0) + 1
            else:
                scripts["other"] = scripts.get("other", 0) + 1
        except Exception:
            scripts["latin"] = scripts.get("latin", 0) + 1
    if not scripts:
        return "latin"
    return max(scripts, key=scripts.get)




def load_feedback(path="feedback.json"):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save_feedback(feedback, path="feedback.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(feedback, f, indent=2)


def username_score(u1, u2):
    if not u1 or not u2:
        return 0
    if u1 == u2:
        return 100
    return fuzz.ratio(u1, u2)


def display_name_score(d1, d2):
    if not d1 or not d2:
        return 0
    s1 = detect_script(d1)
    s2 = detect_script(d2)
    if s1 != s2:
        return 0
    d1 = d1.lower().strip()
    d2 = d2.lower().strip()
    if d1 == d2:
        return 100
    return fuzz.token_sort_ratio(d1, d2)


def has_pattern_variation(u1, u2):
    if not u1 or not u2:
        return False
    variations = [
        u1 + "_", "_" + u1,
        u1.replace("_", ""), u1.replace("_", "."),
        u1.replace(".", "_"), u1.replace(".", ""),
    ]
    for i in range(10):
        variations.append(u1 + str(i))
        variations.append(u1 + str(i) + "_")
    return u2 in variations


def score_pair(entry_a, entry_b, feedback, alias_map, known_hints=None):
    u1 = entry_a.get("username")
    u2 = entry_b.get("username")
    d1 = entry_a.get("display_name")
    d2 = entry_b.get("display_name")

    reasons = []

    if u1 and u2:
        key = f"{u1}:{u2}"
        rev_key = f"{u2}:{u1}"
        if key in feedback:
            if feedback[key] == "confirmed":
                return ALIAS_SCORE, ["previously confirmed by user"]
            elif feedback[key] == "rejected":
                return 0, ["previously rejected by user"]
        if rev_key in feedback:
            if feedback[rev_key] == "confirmed":
                return ALIAS_SCORE, ["previously confirmed by user"]
            elif feedback[rev_key] == "rejected":
                return 0, ["previously rejected by user"]

        if alias_map.get(u1) is not None and alias_map.get(u1) == alias_map.get(u2):
            return ALIAS_SCORE, ["matched via alias dictionary"]

    u_score = username_score(u1, u2)
    d_score = display_name_score(d1, d2)

    if u1 and u2:
        base = (u_score * 0.65) + (d_score * 0.35)
        if u_score >= 95:
            reasons.append(f"username exact/near match ({u_score}%)")
        elif u_score >= 70:
            reasons.append(f"username similarity {u_score}%")
        if d_score >= 80:
            script = detect_script(d1)
            reasons.append(f"display name match ({d_score}%)" + (f" [{script}]" if script != "latin" else ""))
        elif d_score >= 50:
            reasons.append(f"display name similarity {d_score}%")
    elif d1 and d2:
        base = d_score * 0.7
        script = detect_script(d1)
        reasons.append(f"display name only match ({d_score}%)" + (f" [{script}]" if script != "latin" else ""))
    else:
        base = 0

    if u1 and u2 and has_pattern_variation(u1, u2):
        base = min(100, base + PATTERN_BONUS)
        reasons.append("common username variation pattern")


    # fix issue 4: apply both-lists bonus symmetrically to both entries
    a_both = entry_a.get("in_followers") and entry_a.get("in_following")
    b_both = entry_b.get("in_followers") and entry_b.get("in_following")
    if a_both and b_both:
        base = min(100, base + MUTUAL_FOLLOW_BONUS)
        reasons.append("mutual follow on both platforms")
    elif a_both or b_both:
        base = min(100, base + BOTH_LISTS_BONUS)
        reasons.append("appears in both followers and following")

    # fix issue 3: removed fuzzy feedback generalization, only exact pair matches apply
    if u1 and u2 and feedback:
        rejected_patterns = [k for k, v in feedback.items() if v == "rejected"]
        for pattern in rejected_patterns:
            parts = pattern.split(":")
            if len(parts) == 2:
                pu1, pu2 = parts
                if (u1 == pu1 and u2 == pu2) or (u1 == pu2 and u2 == pu1):
                    base = max(0, base - FEEDBACK_PENALTY)
                    reasons.append("similar to a previously rejected match")
                    break

    # fix issue 2: known info only boosts with exact username match not substring
    if known_hints:
        from known_info import score_against_hints
        boost_a, reasons_a = score_against_hints(entry_a, known_hints, exact_only=True)
        boost_b, reasons_b = score_against_hints(entry_b, known_hints, exact_only=True)
        if boost_a or boost_b:
            base = min(100, base + max(boost_a, boost_b))
            reasons.extend(reasons_a or reasons_b)

    return round(base), reasons


def get_tier(score, quick_threshold=None):
    if score >= 95:
        return "AUTO-CONFIRMED"
    elif score >= 75:
        return "QUICK REVIEW"
    elif score >= (quick_threshold if quick_threshold else 50):
        return "MANUAL REVIEW"
    else:
        return "WEAK"


def flatten_entries(user_data):
    # fix issue 6: preserve all entries per key as a list instead of overwriting
    all_entries = {}
    for platform_num, data in user_data.items():
        platform = data["platform"]
        for entry in data["followers"]:
            key = entry.get("username") or entry.get("display_name", "").lower()
            if not key:
                continue
            canonical = (key, platform)
            if canonical not in all_entries:
                all_entries[canonical] = {
                    **entry,
                    "platform": platform,
                    "platform_num": platform_num,
                    "in_followers": True,
                    "in_following": False
                }
            else:
                all_entries[canonical]["in_followers"] = True

        for entry in data["following"]:
            key = entry.get("username") or entry.get("display_name", "").lower()
            if not key:
                continue
            canonical = (key, platform)
            if canonical not in all_entries:
                all_entries[canonical] = {
                    **entry,
                    "platform": platform,
                    "platform_num": platform_num,
                    "in_followers": False,
                    "in_following": True
                }
            else:
                all_entries[canonical]["in_following"] = True

    return all_entries


def match_across_platforms(all_users, alias_map, feedback, min_threshold=30, known_hints=None, quick_threshold=None):
    results = []
    # fix issue 5: scope deduplication per user so corroborating evidence from different users is preserved
    pair_scores = {}

    for user_name, user_data in all_users.items():
        platform_nums = list(user_data.keys())
        seen_pairs_this_user = set()

        for i in range(len(platform_nums)):
            for j in range(i + 1, len(platform_nums)):
                num_a = platform_nums[i]
                num_b = platform_nums[j]

                entries_a = flatten_entries({num_a: user_data[num_a]})
                entries_b = flatten_entries({num_b: user_data[num_b]})

                for key_a, entry_a in entries_a.items():
                    for key_b, entry_b in entries_b.items():
                        username_a = entry_a.get("username") or key_a[0]
                        username_b = entry_b.get("username") or key_b[0]
                        pair_key = tuple(sorted([username_a, username_b]))

                        if pair_key in seen_pairs_this_user:
                            continue
                        seen_pairs_this_user.add(pair_key)

                        score, reasons = score_pair(entry_a, entry_b, feedback, alias_map, known_hints=known_hints)

                        effective_min = quick_threshold if quick_threshold else min_threshold
                        if score < effective_min:
                            continue

                        if pair_key not in pair_scores:
                            pair_scores[pair_key] = {
                                "entry_a": entry_a,
                                "entry_b": entry_b,
                                "score": score,
                                "reasons": reasons,
                                "corroborated_by": [user_name]
                            }
                        else:
                            existing = pair_scores[pair_key]
                            if user_name not in existing["corroborated_by"]:
                                existing["corroborated_by"].append(user_name)
                            if score > existing["score"]:
                                existing["score"] = score
                                existing["reasons"] = reasons

    for pair_key, data in pair_scores.items():
        score = data["score"]
        reasons = data["reasons"]
        corroborated_by = data["corroborated_by"]

        if len(corroborated_by) > 1:
            score = min(100, score + 5 * (len(corroborated_by) - 1))
            reasons = reasons + [f"corroborated by {len(corroborated_by)} users"]

        results.append({
            "user": corroborated_by[0],
            "entry_a": data["entry_a"],
            "entry_b": data["entry_b"],
            "score": score,
            "tier": get_tier(score, quick_threshold=quick_threshold),
            "reasons": reasons,
            "corroborated_by": corroborated_by
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def find_target(target_username, all_users, alias_map, feedback):
    seen = {}
    for user_name, user_data in all_users.items():
        for platform_num, data in user_data.items():
            platform = data["platform"]
            all_entries = data["followers"] + data["following"]
            for entry in all_entries:
                u = entry.get("username", "")
                d = entry.get("display_name") or ""
                u_sim = fuzz.ratio(target_username, u)
                d_sim = fuzz.partial_ratio(target_username.lower(), d.lower()) if d else 0
                score = max(u_sim, d_sim * 0.8)
                if alias_map.get(u) is not None and alias_map.get(target_username) == alias_map.get(u):
                    score = 100
                if score >= 50:
                    dedup_key = (u, platform)
                    if dedup_key not in seen or score > seen[dedup_key]["score"]:
                        seen[dedup_key] = {
                            "user": user_name,
                            "platform": platform,
                            "platform_num": platform_num,
                            "entry": entry,
                            "score": round(score),
                            "tier": get_tier(round(score))
                        }
    return sorted(seen.values(), key=lambda x: x["score"], reverse=True)


def discovery_mode(all_users, alias_map, feedback, min_threshold=30):
    all_entries = {}
    for user_name, user_data in all_users.items():
        for platform_num, data in user_data.items():
            platform = data["platform"]
            for entry in data["followers"] + data["following"]:
                key = entry.get("username") or (entry.get("display_name", "").lower().replace(" ", "_"))
                if not key:
                    continue
                if key not in all_entries:
                    all_entries[key] = {"entry": entry, "seen_by": set(), "platforms": set()}
                all_entries[key]["seen_by"].add(user_name)
                all_entries[key]["platforms"].add(platform)

    total_users = len(all_users)
    ranked = []
    for key, data in all_entries.items():
        overlap = len(data["seen_by"])
        if overlap < 2:
            continue
        score = round((overlap / total_users) * 100)
        if score < min_threshold:
            continue
        ranked.append({
            "entry": data["entry"],
            "seen_by": list(data["seen_by"]),
            "platforms": list(data["platforms"]),
            "overlap_count": overlap,
            "total_users": total_users,
            "score": score,
            "tier": get_tier(score)
        })

    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked


def find_unmatched(all_users, alias_map, feedback, min_threshold=30):
    matched_keys = set()
    platform_entries = {}

    for user_name, user_data in all_users.items():
        platform_nums = list(user_data.keys())

        for i in range(len(platform_nums)):
            for j in range(i + 1, len(platform_nums)):
                num_a = platform_nums[i]
                num_b = platform_nums[j]
                entries_a = flatten_entries({num_a: user_data[num_a]})
                entries_b = flatten_entries({num_b: user_data[num_b]})

                for key_a, entry_a in entries_a.items():
                    for key_b, entry_b in entries_b.items():
                        score, _ = score_pair(entry_a, entry_b, feedback, alias_map)
                        if score >= min_threshold:
                            matched_keys.add(key_a)
                            matched_keys.add(key_b)

        for platform_num, data in user_data.items():
            platform = data["platform"]
            entries = flatten_entries({platform_num: data})
            for key, entry in entries.items():
                if key not in platform_entries:
                    platform_entries[key] = {"entry": entry, "platform": platform, "seen_in": set()}
                platform_entries[key]["seen_in"].add(platform)

    unmatched = []
    seen_unmatched = set()
    for key, data in platform_entries.items():
        if key in matched_keys:
            continue
        if key in seen_unmatched:
            continue
        seen_unmatched.add(key)
        platforms = list(data["seen_in"])
        unmatched.append({
            "entry": data["entry"],
            "platform": platforms[0] if len(platforms) == 1 else ", ".join(platforms),
            "platform_count": len(platforms),
            "tier": "UNMATCHED"
        })

    return unmatched


def suggest_aliases(results):
    suggestions = []
    seen = set()
    for r in results:
        if r.get("tier") != "AUTO-CONFIRMED":
            continue
        ea = r.get("entry_a", {})
        eb = r.get("entry_b", {})
        u1 = ea.get("username")
        u2 = eb.get("username")
        if u1 and u2 and u1 != u2:
            key = tuple(sorted([u1, u2]))
            if key not in seen:
                seen.add(key)
                suggestions.append((u1, u2))
    return suggestions


def get_persistent_connections(path="history.json", min_appearances=2):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        try:
            history = json.load(f)
        except json.JSONDecodeError:
            return []

    freq = {}
    for record in history:
        for key, score in record.get("scores", {}).items():
            if key not in freq:
                freq[key] = {"count": 0, "scores": [], "key": key}
            freq[key]["count"] += 1
            freq[key]["scores"].append(score)

    persistent = []
    for key, data in freq.items():
        if data["count"] >= min_appearances:
            avg_score = round(sum(data["scores"]) / len(data["scores"]))
            persistent.append({
                "key": key,
                "appearances": data["count"],
                "avg_score": avg_score
            })

    return sorted(persistent, key=lambda x: (x["appearances"], x["avg_score"]), reverse=True)