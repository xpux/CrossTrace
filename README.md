# CrossTrace
> Cross-platform social graph analyser. Feed it exported follower/following lists, it finds the connections with 1 username only (assuming the target has the same name on other accounts).

CrossTrace takes raw exported follower/following lists from any social media platform and analyses them to find a target user across platforms, map their social circle, and score cross-platform matches using both usernames and display names. No APIs. No scraping. Just files you already have.

---

## Quick start

```bash
git clone https://github.com/xpux/CrossTrace.git
cd CrossTrace
pip install -r requirements.txt
python crosstrace.py --init
```

`--init` creates all the files and folders the tool needs on first run. After that, drop your exported lists into `data/users/me/` and run:

```bash
python crosstrace.py
```

---

## Features

Cross-platform matching: find the same person across TikTok, Instagram, Twitter, and more

Fuzzy matching: catches variations like `johndoe`, `john_doe`, `johndoe_` and scores them by confidence

Display name matching: uses both username and display name as signals, with script detection so Arabic names only match Arabic names, CJK only matches CJK, and so on

Mutual follow detection: identifies accounts that appear in both followers and following lists (reciprocal relationships), giving stronger insight into two-way connections within each platform bucket

Mutual export system: outputs mutual connections per bucket in CSV and JSON formats for external analysis and tracking

Interactive mutual selection: lets you choose a specific user/platform bucket or run mutual detection across all loaded datasets

Mutual scoring integration: mutual connections are treated as higher-confidence relationships compared to one-way follows, improving relationship weighting in analysis

Multi-user / friend group mode: add multiple people's lists to map a shared social network

Discovery mode: don't know who you're looking for? Add multiple users' lists and the tool surfaces who appears most across all of them

Quick mode: set a minimum threshold in config so only high-confidence matches show up in the review queue

Top N most prevalent: see who shows up across the most lists at a glance, fully customisable

Persistent connections: after multiple runs, surfaces people who keep appearing across sessions

Single-platform detection: flags people who only appear on one platform with no cross-platform match found

Manual review queue: borderline matches get flagged for you to confirm, reject, or mark as famous

Famous person filter: mark celebrities and public figures so they never appear in results again

Feedback learning: your confirmed/rejected decisions improve future scoring

Confidence breakdown: every match explains why it scored the way it did

Session naming: each run saves to its own folder so nothing gets overwritten

Stats summary: see most active platform, most connected user, and confirmed match counts after every run

Bulk alias suggestions: the tool suggests aliases based on confirmed matches and lets you save them

Known info system: drop any files you already have about a target into a folder and the tool uses them to boost matching

Customisable ignore list: strip platform-specific UI text from raw pastes

Alias dictionary: hardcode known aliases to auto-confirm them

Flexible output: CSV, JSON, or both

Graph export: every run also writes the discovered network as a real graph in JSON, GraphML (for Gephi, Cytoscape, or yEd), and a single self-contained HTML viewer that runs fully offline

Scriptable: run a whole session with no prompts using `--target`, `--discovery`, `--session`, and `--yes`, so it slots into scripts and automation

---

## How It Works

### 1. Export your lists

Go to any social media platform, navigate to your followers or following list, and copy-paste the content into a `.txt` file. The raw paste typically looks like:

```
John Doe
johndoe_
Following

Jane Smith
jane_smith
Follow Back
```

CrossTrace automatically strips UI text like `Follow`, `Following`, `Followers`, `Follow Back` and keeps only usernames and display names. You can customise what gets stripped in `ignorelist.txt`.

### 2. Set up your files

Place your files in the `data/users/` folder. Each person whose lists you're adding gets their own subfolder. Name your files using this exact format:

```
{platform}_{followers or following}{number}.txt
```

The number at the end groups files by platform: all files with the same number belong to the same platform. The platform name at the start is just a label for readability.

Example:

```
CrossTrace/
├── config.json
├── ignorelist.txt
├── aliases.txt
├── target.txt
├── crosstrace.py
└── data/
    ├── known/
    └── users/
        ├── me/
        │   ├── tiktok_followers1.txt
        │   └── tiktok_following1.txt
        ├── friend_a/
        │   ├── instagram_followers2.txt
        │   └── instagram_following2.txt
        └── friend_b/
            ├── tiktok_followers1.txt
            └── instagram_followers2.txt
```

Valid filename examples:

```
tiktok_followers1.txt       ✓
instagram_following2.txt    ✓
twitter_followers3.txt      ✓
tiktok_followers.txt        ✗  (missing number)
followers1.txt              ✗  (missing platform name)
tiktok1.txt                 ✗  (missing followers/following)
```

### 3. Set a target (or leave blank)

In `target.txt`, write the username you're looking for:

```
johndoe_
```

Leave it empty and CrossTrace will ask you in the terminal when you run it. Leave the prompt blank too to run in discovery mode.

### 4. Run CrossTrace

```bash
python crosstrace.py
```

CrossTrace will ask you to name the session at startup. Each session saves to its own folder under `output/` so previous runs are never overwritten.

---

## Modes

### Mode 1: Known Target

You know who you're looking for. Put their username in `target.txt` or type it when prompted. CrossTrace searches all lists for that username and close variants, then maps their mutual connections across platforms.

Works with just your own lists, no other users needed.

### Mode 2: Discovery Mode

You don't have a specific target. Leave everything blank and CrossTrace finds everyone who appears across multiple users' lists, ranked by how many people in your group follow them.

Important: Discovery mode requires at least two users' lists to work. It finds overlap between people: so if only your lists are in `data/users/`, there's nothing to cross-reference and it will return no results. To use discovery mode, add a second person's lists under their own subfolder (e.g. `data/users/friend_a/`) alongside yours. The more people you add, the better the results.

---

## The more data, the better

CrossTrace gets significantly more accurate the more you feed it. More platforms per person means more surfaces to find matches across. More people's folders means more cross-referencing. More runs with feedback means the scoring learns your decisions and auto-confirms patterns over time. The person you're looking for will naturally float to the top as you add more data.

---

## Known Info System

If you already have files with information about a target: notes, old usernames, bio screenshots you've typed out, anything: you can drop them into a folder and CrossTrace will read them and use whatever looks useful to boost match scores. The file format and naming doesn't matter.

Configure it in `config.json`:

```json
"known_info": {
  "enabled": true,
  "mode": "global",
  "global_path": "data/known",
  "target_path": "data/known/{target}"
}
```

Three modes are available. Global loads `data/known/` on every run regardless of target. Target loads `data/known/{target}/` only when searching for that specific person. Both loads both folders simultaneously.

Example structure:

```
data/known/
├── general_notes.txt         ← loaded in global mode
├── old_usernames.md          ← loaded in global mode
└── johndoe/                  ← loaded in target mode when target = johndoe
    ├── bio_notes.txt
    └── known_accounts.txt
```

When a hint from these files matches an entry, it shows up in the `why:` line during review and in the summary.

---

## Confidence Tiers

| Tier | Score | Action |
|------|-------|--------|
| Auto-confirmed | 95–100% | Saved directly to results |
| Quick review | 75–94% | Flagged for a fast check |
| Manual review | 50–74% | Needs careful review ⚠️ |
| Weak match | Below 50% | Low priority, listed separately |

Scores are calculated from username similarity (fuzzy), display name similarity (script-aware), mutual follow detection, shared mutual connections between platforms, common username patterns (`_` added, numbers appended, `.` swapped), whether the person appears in both followers and following vs just one, alias dictionary hits, known info hints, and how many seed users follow them in multi-user mode.

---

## Review Mode

After the script runs, borderline matches are queued for manual review. Each case shows the two entries side by side with their confidence score, a `why:` line explaining the score, and three options:

```
WARNING: Check each manual case carefully before pressing Yes.
This tool can make mistakes.

[1/7] MANUAL REVIEW: 67%
  A: mikegaming / Mike Gaming (tiktok)
  B: mike_g / Mike G (instagram)
  why: username similarity 71%, common username variation pattern

  (1) Yes: same person
  (2) No: different people
  (3) Famous / not important: skip
```

Option 1 confirms them as the same person, saves to results, bumps score to 100, and feeds back into future scoring.

Option 2 rejects the match and penalises similar patterns in future runs.

Option 3 marks them as famous or not relevant, saves them to `famous.json`, and permanently filters them from all future runs.

After cross-platform review, single-platform entries (people only found on one platform with no match on the other) are shown separately with the same 1/2/3 options.

At the end of each run, CrossTrace suggests confirmed pairs that could be added as aliases and lets you approve or skip each one.

Your decisions persist in `feedback.json` and improve scoring accuracy over time.

---

## Command-line reference

Running `python crosstrace.py` with no flags walks you through naming a session and entering a target interactively. The flags below let you skip the prompts or run other commands.

| Flag | What it does |
|------|--------------|
| `--init` | Create the folders and files CrossTrace needs, then exit |
| `--target USERNAME` | Run against this target without the prompt |
| `--discovery` | Force discovery mode without the prompt |
| `--session NAME` | Name the session without the prompt |
| `--yes`, `-y` | Non-interactive: auto-name the session, no prompts, skips review |
| `--no-review` | Run the matching but skip the manual review queue |
| `--graph FORMATS` | Choose graph formats, a comma list of `json,graphml,html` |
| `--no-graph` | Skip graph export for this run |
| `--dry-run` | Preview the review queue without saving anything |
| `--search USERNAME` | Find a username across all loaded lists |
| `--compare A B` | Compare two past sessions |
| `--summary SESSION` | Reprint the summary for a past session |
| `--history USERNAME` | Show a username's score across sessions |
| `--export-aliases` | Export confirmed matches straight to `aliases.txt` |
| `--stats-only` | Print the last session's stats without rerunning |
| `--reset` | Wipe `feedback.json`, `famous.json`, and `history.json` |
| `--version` | Print the version |

A fully scripted discovery run, no prompts, HTML graph only:

```bash
python crosstrace.py --yes --discovery --session friday_sweep --graph html
```

---

## Graph Output

CrossTrace is a social graph analyser, so every run also reconstructs the network it found and writes it three ways under the session folder.

`graph.json` is a plain nodes-and-edges structure you can load anywhere. `graph.graphml` opens directly in network tools like Gephi, Cytoscape, and yEd if you want to lay out or analyse large networks. `graph.html` is a single self-contained file you can open in any browser: it embeds the data and renders an interactive force-directed view with drag, zoom, search, and a detail panel. It loads no external scripts and makes no network requests, so it works offline and keeps everything on your machine, in keeping with the rest of the tool.

In target mode the nodes are accounts and the edges are same-person matches weighted by confidence. In discovery mode the nodes are the people who appear across lists plus the seed users who follow them, so you can see who sits at the centre of the group.

Pick formats per run with `--graph json,graphml,html`, turn it off with `--no-graph`, or set the default in `config.json`:

```json
"graph": {
  "formats": ["json", "graphml", "html"]
}
```

---



```json
{
  "min_match_threshold": 30,
  "output_format": ["csv", "json"],
  "review_mode": true,
  "top_results": 5,
  "quick_mode": false,
  "quick_threshold": 70,
  "min_username_length": 2,
  "graph": {
    "formats": ["json", "graphml", "html"]
  },
  "known_info": {
    "enabled": true,
    "mode": "global",
    "global_path": "data/known",
    "target_path": "data/known/{target}"
  }
}
```

| Option | Default | Description |
|--------|---------|-------------|
| `min_match_threshold` | `30` | Don't show matches below this confidence % |
| `output_format` | `["csv", "json"]` | Output format(s) |
| `review_mode` | `true` | Enable interactive manual review after run |
| `top_results` | `5` | How many top prevalent people to show in the summary |
| `quick_mode` | `false` | Only show matches above `quick_threshold` in review queue |
| `quick_threshold` | `70` | Minimum score to appear in review queue when quick mode is on |
| `min_username_length` | `2` | Ignore parsed handles shorter than this |
| `graph.formats` | `["json","graphml","html"]` | Graph formats written each run |
| `known_info.enabled` | `true` | Toggle the known info system on or off |
| `known_info.mode` | `"global"` | One of: `global`, `target`, `both` |
| `known_info.global_path` | `"data/known"` | Path to global known info folder |
| `known_info.target_path` | `"data/known/{target}"` | Path template for per-target folder |

### `ignorelist.txt`

Words or phrases to strip from raw pastes. One entry per line. Pre-filled with common platform UI text:

```
Following
Followers
Follow Back
Follow
Suggested
Verified
Mutual Follow
```

Add any extra text your platform includes when you copy a list.

### `aliases.txt`

Known aliases for the same person. CrossTrace auto-confirms these instead of guessing:

```
mikegaming = mike_gaming = mikeg
john_doe = johndoe = jdoe99
```

This file ships as `aliases.example.txt` and `--init` copies it to `aliases.txt` on first run. Because real aliases are confirmed links between people's accounts, `aliases.txt` is git-ignored and never committed.

---

## Output

Each run saves to its own folder under `output/session_name/`.

| File | Contents |
|------|----------|
| `results_confirmed.csv/json` | Auto-confirmed cross-platform matches |
| `results_review.csv/json` | Manual review queue and your decisions |
| `results_weak.csv/json` | Low confidence matches (below threshold) |
| `summary.md` | Human-readable summary report of the full run |
| `graph.json` | The discovered network as nodes and edges |
| `graph.graphml` | Same graph for Gephi, Cytoscape, or yEd |
| `graph.html` | Self-contained offline viewer; open in any browser |

Example output:

```
============================================================
  CROSSTRACE: RESULTS SUMMARY
============================================================

  Total pairs analysed: 348
  AUTO-CONFIRMED: 12
  QUICK REVIEW: 8
  MANUAL REVIEW: 7
  WEAK: 321

  TOP 5 MOST PREVALENT
  johndoe_ / John Doe  |  seen in 2 platform(s): instagram, tiktok
  jane_smith           |  seen in 2 platform(s): instagram, tiktok

  AUTO-CONFIRMED
  johndoe_ (instagram)  →  johndoe_ (tiktok)  |  100%
    why: username exact/near match (100%)
  jane_smith (instagram)  →  jane_smith (tiktok)  |  100%
    why: username exact/near match (100%)

============================================================
  CROSSTRACE: SESSION STATS
============================================================

  folders loaded:       3
  total lists loaded:   6
  confirmed matches:    12
  famous filtered out:  4
  most active platform: instagram (18 confirmed entries)
```

---

## Resetting memory

To wipe all learned state, run `python crosstrace.py --reset`. This clears `feedback.json` (your confirm/reject decisions), `famous.json` (the filtered public figures), and `history.json` (past sessions) in one step.

---

## Installation

```bash
git clone https://github.com/xpux/CrossTrace.git
cd CrossTrace
pip install -r requirements.txt
```

You can also install it as a package, which adds a `crosstrace` command on your path:

```bash
pip install .
crosstrace --version
```

Requirements: Python 3.8+ and `rapidfuzz`.

Works on Windows, Linux, and Mac.

---

## Privacy

CrossTrace works entirely on files you provide. It makes no network requests, calls no APIs, and does not send any data anywhere. Everything runs locally on your machine.

---

## Disclaimer

This tool is intended for personal use with data you have legitimate access to. You are responsible for ensuring you use it in accordance with the terms of service of any platform whose data you export, and in compliance with applicable privacy laws.
