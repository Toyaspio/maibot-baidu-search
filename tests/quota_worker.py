"""Child process used by the cross-process SQLite limit test; all data is synthetic."""

import sys
from pathlib import Path

import conftest  # noqa: F401 - import package with Runner's package semantics
from maisearch.errors import SearchError
from maisearch.quota_manager import QuotaManager

manager = QuotaManager(Path(sys.argv[1]))
success = 0
for _ in range(12):
    try:
        manager.reserve(7)
        success += 1
    except SearchError as exc:
        if exc.code != "quota":
            raise
print(success)
