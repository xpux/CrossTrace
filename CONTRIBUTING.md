# Contributing to CrossTrace

Thanks for your interest in improving CrossTrace. This is a small, dependency-light
project and aims to stay that way.

## Getting set up

Clone the repo, then install in editable mode with the dev extras:

```bash
git clone https://github.com/xpux/CrossTrace.git
cd CrossTrace
pip install -e ".[dev]"
python crosstrace.py --init
```

## Running the checks

The full suite runs in well under a second:

```bash
pytest -q          # tests
ruff check .       # lint
```

Please add or update tests for any behaviour you change. Scoring logic in particular is
easy to break by accident, so the matcher tests are the first place to look when a change
affects results.

## Design principles

1. Local only. CrossTrace never makes a network request, never scrapes, and never calls a
   platform API. It analyses files the user already has. Please keep it that way. A pull
   request that adds scraping or live data collection will not be merged.
2. Few dependencies. The runtime depends only on `rapidfuzz`. Think hard before adding
   anything else.
3. Conservative matching. The tool errs toward flagging borderline matches for human
   review rather than auto-confirming them, to avoid wrongly linking two different people.
   Keep that bias when touching the scorer.

## Responsible use

CrossTrace is built for working with data you have legitimate access to, such as your own
exported lists or a consenting friend group mapping its own network. Please do not use it,
or contribute features designed, to track, profile, or de-anonymise people without their
involvement. When filing issues, never paste real usernames or other people's data.

## Commit style

Write commit messages in plain prose or numbered lists. Describe what changed and why.
