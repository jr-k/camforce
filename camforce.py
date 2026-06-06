#!/usr/bin/env python3
"""Dev entry point.

Run camforce without installing the package:

    python3 camforce.py -c config.yaml
    ./camforce.py -c config.yaml          # if executable bit is set

Equivalent to the installed `camforce` console script, but reads the
local src/ tree directly so code changes are picked up immediately.
"""
from src.cli import main


if __name__ == "__main__":
    main()
