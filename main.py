#!/usr/bin/env python3
"""Run git-hotspots from a checkout without installing it.

After `pip install .` the same CLI is available as the `git-hotspots` command.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from git_hotspots.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
