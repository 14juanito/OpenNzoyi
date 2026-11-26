"""Pytest path setup: make nzoyi-api and nzoyi-core importable."""

import sys
from pathlib import Path

_API = Path(__file__).resolve().parent.parent          # nzoyi-api/
_CORE = _API.parent / "nzoyi-core"                      # nzoyi-core/
for p in (_API, _CORE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
