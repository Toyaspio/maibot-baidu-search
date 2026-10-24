import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from maisearch.errors import SearchError
from maisearch.quota_manager import QuotaManager


def attempt(manager, limit=20, **kwargs):
    try:
        manager.reserve(limit, **kwargs)
        return "ok"
    except SearchError as error:
        return error.code


def test_concurrent_instances_and_reload(tmp_path):
    path = tmp_path / "quota.sqlite3"
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(lambda _: attempt(QuotaManager(path)), range(80)))
    assert results.count("ok") == 20
    assert results.count("quota") == 60
    assert attempt(QuotaManager(path)) == "quota"
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT calls FROM usage").fetchone()[0] == 20


def test_beijing_midnight_and_clock_rollback(tmp_path):
    current = [datetime(2026, 10, 24, 15, 59, 59, tzinfo=timezone.utc)]
    manager = QuotaManager(tmp_path / "q.sqlite3", clock=lambda: current[0])
    assert attempt(manager, 1) == "ok"
    assert attempt(manager, 1) == "quota"
    current[0] += timedelta(seconds=1)
    assert attempt(manager, 1) == "ok"
    with sqlite3.connect(manager.path) as db:
        assert db.execute("SELECT day FROM usage ORDER BY day").fetchall() == [("2026-10-24",), ("2026-10-25",)]
    current[0] -= timedelta(seconds=1)
    assert attempt(manager, 1) == "clock"


@pytest.mark.parametrize("limit", [0, 101, -1, True, 2.0])
def test_limits(tmp_path, limit):
    assert attempt(QuotaManager(tmp_path / "q.sqlite3"), limit) == ("quota" if limit == 0 else "quota_storage")


def test_tool_guards_persist(tmp_path):
    current = [datetime(2026, 10, 24, 1, tzinfo=timezone.utc)]
    path = tmp_path / "q.sqlite3"

    def make():
        return QuotaManager(path, clock=lambda: current[0])

    assert attempt(make(), tool=True, query="新闻", tool_daily_limit=2) == "ok"
    assert attempt(make(), tool=True, query="另一关键词", tool_daily_limit=2) == "cooldown"
    current[0] += timedelta(seconds=61)
    assert attempt(make(), tool=True, query="新闻", tool_daily_limit=2) == "cooldown"
    assert attempt(make(), tool=True, query="另一关键词", tool_daily_limit=2) == "ok"
    current[0] += timedelta(seconds=61)
    assert attempt(make(), tool=True, query="第三词", tool_daily_limit=2) == "tool_quota"
    assert attempt(make()) == "ok"  # Independent tool cap leaves command available.
    assert b"\xe6\x96\xb0\xe9\x97\xbb" not in path.read_bytes()


def test_tool_concurrent(tmp_path):
    path = tmp_path / "q.sqlite3"
    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(lambda n: attempt(QuotaManager(path), tool=True, query=f"词{n}"), range(24)))
    assert results.count("ok") == 1
    assert results.count("cooldown") == 23


def test_corruption_fails_closed(tmp_path):
    path = tmp_path / "q.sqlite3"
    path.write_bytes(b"broken database, do not reset")
    assert attempt(QuotaManager(path)) == "quota_storage"
    assert path.read_bytes() == b"broken database, do not reset"


def test_busy_fails_closed(tmp_path):
    path = tmp_path / "q.sqlite3"
    assert attempt(QuotaManager(path)) == "ok"
    with sqlite3.connect(path) as blocker:
        blocker.execute("BEGIN EXCLUSIVE")
        assert attempt(QuotaManager(path)) == "quota_storage"


def test_lowered_limit_does_not_reset(tmp_path):
    manager = QuotaManager(tmp_path / "q.sqlite3")
    for _ in range(3):
        assert attempt(manager) == "ok"
    assert attempt(manager, 2) == "quota"


def test_naive_clock_fails_closed(tmp_path):
    assert attempt(QuotaManager(tmp_path / "q.sqlite3", clock=lambda: datetime(2026, 10, 24))) == "clock"


def test_cross_process_reservations(tmp_path):
    command = [sys.executable, str(Path(__file__).with_name("quota_worker.py")), str(tmp_path / "q.sqlite3")]
    processes = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(6)]
    accepted = []
    for process in processes:
        output, error = process.communicate(timeout=30)
        assert process.returncode == 0, error.decode("utf-8", errors="replace")
        accepted.append(int(output.strip()))
    assert sum(accepted) == 7
    assert attempt(QuotaManager(tmp_path / "q.sqlite3"), 7) == "quota"


def test_time_sampled_inside_reservation_lock(tmp_path):
    path = tmp_path / "q.sqlite3"
    assert attempt(QuotaManager(path)) == "ok"

    def clock():
        with sqlite3.connect(path, timeout=0) as observer:
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                observer.execute("BEGIN IMMEDIATE")
        return datetime.now(timezone.utc)

    assert attempt(QuotaManager(path, clock=clock)) == "ok"
