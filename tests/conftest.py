"""Import as a package exactly like the SDK Runner (relative imports supported)."""

import importlib.util
import sys
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("maisearch", ROOT / "plugin.py", submodule_search_locations=[str(ROOT)])
module = importlib.util.module_from_spec(spec)
sys.modules["maisearch"] = module
spec.loader.exec_module(module)


@pytest.fixture(autouse=True)
def prohibit_real_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Tests must never connect to a real API or Host")

    # Blocking raw socket.connect also breaks Windows asyncio's loopback self-pipe.
    # Stop real HTTP at the transport boundary; MockTransport stays usable.
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)
