import os
import sys

# Make the top-level modules (parser.py, matcher.py, ...) importable from tests/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
