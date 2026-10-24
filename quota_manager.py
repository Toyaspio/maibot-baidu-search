"""SQLite reservations are committed before HTTP, across reloads and processes."""

import hashlib
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .errors import SearchError

BEIJING = timezone(timedelta(hours=8))
MAX_DAILY_LIMIT = 100
MAX_TOOL_DAILY_LIMIT = 20
TOOL_COOLDOWN_SECONDS = 60
TOOL_DUPLICATE_SECONDS = 600


class QuotaManager:
    def __init__(self, path: Path, clock=None):
        self.path = Path(path)
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def reserve(self, daily_limit: int, *, tool: bool = False, tool_daily_limit: int = 5, query: str = "") -> None:
        """No refund: cancellations, timeouts and failed HTTP all retain reservations."""
        if (
            type(daily_limit) is not int
            or not 0 <= daily_limit <= MAX_DAILY_LIMIT
            or type(tool_daily_limit) is not int
            or not 0 <= tool_daily_limit <= MAX_TOOL_DAILY_LIMIT
        ):
            raise SearchError("quota_storage")
        connection = None
        try:
            digest = hashlib.sha256(query.casefold().encode("utf-8")).hexdigest()
            self.path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("BEGIN IMMEDIATE")
            # Sample time after acquiring the writer lock: queued reservations may
            # arrive out of order, and lock waits may cross Beijing midnight.
            now = self.clock()
            if now.tzinfo is None:
                raise SearchError("clock")
            day = now.astimezone(BEIJING).date().isoformat()
            stamp = now.timestamp()
            connection.execute(
                "CREATE TABLE IF NOT EXISTS usage(day TEXT PRIMARY KEY, calls INTEGER NOT NULL, "
                "tool_calls INTEGER NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS state(id INTEGER PRIMARY KEY CHECK(id=1), "
                "high_day TEXT NOT NULL, last_tool REAL NOT NULL)"
            )
            connection.execute("CREATE TABLE IF NOT EXISTS queries(digest TEXT PRIMARY KEY, stamp REAL NOT NULL)")
            connection.execute("INSERT OR IGNORE INTO state VALUES(1, ?, 0)", (day,))
            high_day, last_tool = connection.execute("SELECT high_day, last_tool FROM state WHERE id=1").fetchone()
            if day < high_day or (tool and stamp < last_tool):
                raise SearchError("clock")
            connection.execute("INSERT OR IGNORE INTO usage VALUES(?, 0, 0)", (day,))
            calls, tool_calls = connection.execute("SELECT calls, tool_calls FROM usage WHERE day=?", (day,)).fetchone()
            if calls < 0 or tool_calls < 0 or tool_calls > calls:
                raise SearchError("quota_storage")
            if calls >= daily_limit:
                raise SearchError("quota")
            if tool:
                if tool_calls >= tool_daily_limit:
                    raise SearchError("tool_quota")
                previous = connection.execute("SELECT stamp FROM queries WHERE digest=?", (digest,)).fetchone()
                if (last_tool and stamp - last_tool < TOOL_COOLDOWN_SECONDS) or (
                    previous and stamp - previous[0] < TOOL_DUPLICATE_SECONDS
                ):
                    raise SearchError("cooldown")
                connection.execute("UPDATE state SET last_tool=? WHERE id=1", (stamp,))
                connection.execute("DELETE FROM queries WHERE stamp < ?", (stamp - TOOL_DUPLICATE_SECONDS,))
                connection.execute("INSERT OR REPLACE INTO queries VALUES(?, ?)", (digest, stamp))
            connection.execute("UPDATE usage SET calls=calls+1, tool_calls=tool_calls+? WHERE day=?", (int(tool), day))
            connection.execute("UPDATE state SET high_day=? WHERE id=1", (day,))
            connection.commit()
        except SearchError:
            raise
        except (OSError, sqlite3.Error, ValueError, TypeError, OverflowError):
            raise SearchError("quota_storage") from None
        finally:
            if connection is not None:
                connection.close()  # Uncommitted reservations roll back; no HTTP has started.
