# Changelog

All notable changes to CrossTrace are recorded here. This project aims to follow
semantic versioning.

## 1.1.1

This release adds mutual-follow detection (reciprocal connections) and extends
CrossTrace’s relationship analysis capabilities.

New features

1. Mutual follower detection system. CrossTrace can now identify accounts that
   appear in both a user's followers and following lists (i.e. mutual connections).
   This allows the tool to extract reciprocal relationships per platform bucket.

2. Mutuals analysis module (`mutuals.py`). Introduced a dedicated module that:
   - Loads follower/following buckets
   - Computes intersection of usernames across both lists
   - Outputs structured mutual connection data

3. Mutuals export support. Results can now be exported per bucket in:
   - CSV format for spreadsheet analysis
   - JSON format for programmatic usage

4. Interactive mutuals selection menu. Users can choose:
   - A specific user/platform bucket
   - Or run mutual detection across all available buckets

5. CLI integration. Mutual detection is now accessible through the main CrossTrace
   workflow via `run_mutuals`, allowing it to be executed alongside other analysis
   steps.

Fixed

1. Improved robustness of username matching between followers and following lists,
   ensuring only valid entries with usernames are considered in mutual comparisons.

Changed

1. Internal data flow now includes an additional "mutuals bucket" stage derived from
   existing follower/following datasets without requiring any external data changes.

## 1.1.0

This release focuses on correctness, scriptability, real graph output, and project
hygiene, while keeping the tool strictly local and offline.

New features

1. Social graph export. CrossTrace now exports the connections it finds as an actual
   graph in three forms: `graph.json` (nodes and edges), `graph.graphml` (opens in
   Gephi, Cytoscape, or yEd), and `graph.html`, a single self-contained file with an
   offline force-directed viewer that has no external dependencies and makes no network
   requests. Control formats with `--graph json,graphml,html`, disable with `--no-graph`,
   or set defaults under `graph.formats` in `config.json`.

2. Non-interactive operation. New flags `--target`, `--discovery`, `--session`, and
   `--yes` let you run a full session without any prompts, which makes CrossTrace usable
   in scripts and CI. `--yes` auto-names the session and skips the review queue.

3. First-run setup moved into the main program as `python crosstrace.py --init`,
   replacing the separate `setup.py` script (see "Changed" below).

Fixed

1. Username hints containing digits in mixed case (for example `John99`) were silently
   dropped from the known-info extractor because the digit check compared against the
   literal string `"0123456789"`. They are now detected correctly.

2. Interactive prompts no longer crash with an `EOFError` when input is piped or absent;
   they fall back to the default instead.

Changed

1. Removed the unused `pandas` dependency. The only runtime requirement is now
   `rapidfuzz`, so installs are smaller and faster.

2. The first-run helper is now `python crosstrace.py --init` rather than
   `python setup.py`. The old filename collided with Python packaging conventions and
   prevented the project from being pip-installable.

3. `aliases.txt` is now produced from a tracked template named `aliases.example.txt`
   and is git-ignored, since it can contain confirmed real-person identity links.

Project

1. Added pytest test suite covering parser, matcher, known-info extractor, history,
   and graph modules.

2. Added `pyproject.toml`, so `pip install .` works and exposes a `crosstrace`
   command.

3. Added GitHub Actions CI running lint and tests on Python 3.8, 3.10, and 3.12.

4. Extended `.gitignore` to also exclude `aliases.txt` and common tooling caches.

## 1.0.0

Initial public release. Cross-platform username and display-name matching, target and
discovery modes, manual review queue, feedback learning, famous-person filtering,
session history with comparison, known-info boosting, and CSV/JSON output.