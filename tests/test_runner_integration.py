"""Unmodified host Runner modules, real SDK; only support logging/version and IPC are isolated.

MAISEARCH_HOST_SOURCE points to a read-only source snapshot (parent of src/).
No snapshot is distributed with the plugin. These tests skip when it is unavailable.
"""

import asyncio
import importlib
import json
import logging
import os
import shutil
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import tomllib
from conftest import ROOT
from packaging.version import Version

HOST_SOURCE = os.environ.get("MAISEARCH_HOST_SOURCE")
HOST_VERSION = os.environ.get("MAISEARCH_HOST_VERSION", "1.3.5")
SDK_VERSION = os.environ.get("MAISEARCH_SDK_VERSION", "2.10.0")
pytestmark = pytest.mark.skipif(
    not HOST_SOURCE, reason="MAISEARCH_HOST_SOURCE not set: actual Runner source unavailable"
)


@pytest.fixture
def runner_modules(monkeypatch):
    assert importlib.import_module("maibot_sdk").__version__ == SDK_VERSION
    monkeypatch.syspath_prepend(HOST_SOURCE)
    # Infrastructure outside plugin runtime is not part of this source snapshot.
    # Business methods of PluginLoader/PluginRunner/ManifestValidator remain unmodified.
    for name, attrs in {
        "src.common": {"__path__": [str(Path(HOST_SOURCE) / "src/common")]},
        "src.common.logger": {
            "get_logger": logging.getLogger,
            "get_console_handler": lambda: None,
            "initialize_logging": lambda *a, **k: None,
        },
        "src.common.version": {"read_project_version": lambda *a, **k: HOST_VERSION},
        "src.config": {"__path__": []},
        "src.config.config_utils": {
            "compare_versions": lambda a, b: (Version(a) > Version(b)) - (Version(a) < Version(b))
        },
    }.items():
        module = types.ModuleType(name)
        module.__dict__.update(attrs)
        monkeypatch.setitem(sys.modules, name, module)
    loader = importlib.import_module("src.plugin_runtime.runner.plugin_loader")
    main = importlib.import_module("src.plugin_runtime.runner.runner_main")
    manifest = importlib.import_module("src.plugin_runtime.runner.manifest_validator")
    return loader, main, manifest


def prepare(tmp_path, modules):
    loader_module, main, manifest = modules
    plugins = tmp_path / "plugins"
    path = plugins / "maibot-baidu-search"
    path.mkdir(parents=True)
    for file in ROOT.iterdir():
        if file.suffix in (".py", ".json") or file.name in ("README.md", "CHANGELOG.md"):
            shutil.copy2(file, path / file.name)
    runner = main.PluginRunner("tcp://127.0.0.1:1", "synthetic-test-session", [str(plugins)])
    runner._loader = loader_module.PluginLoader(host_version=HOST_VERSION)
    runner._loader._manifest_validator = manifest.ManifestValidator(host_version=HOST_VERSION, sdk_version=SDK_VERSION)
    metas = runner._loader.discover_and_load([str(plugins)])
    assert len(metas) == 1, runner._loader.failed_plugins
    return runner, metas[0], path


def test_actual_manifest_loader_and_default_file(tmp_path, runner_modules):
    runner, meta, path = prepare(tmp_path, runner_modules)
    config = runner._apply_plugin_config(meta)
    assert config["plugin"] == {"config_version": "0.1.0", "enabled": False}
    assert config["search"]["daily_limit"] == 20
    assert tomllib.loads((path / "config.toml").read_text("utf-8")) == config
    assert meta.instance.get_webui_config_schema()
    assert meta.capabilities_required == ["send.text"]


def test_actual_runner_registration_callbacks_reload(tmp_path, runner_modules, monkeypatch):
    from maibot_sdk.context import PluginContext, PluginPaths
    from maisearch.search_service import SearchService, SearchSettings
    from test_search_service import FakeClient

    monkeypatch.delenv("MAISEARCH_API_KEY", raising=False)
    runner, meta, path = prepare(tmp_path, runner_modules)
    instance = meta.instance
    rpc = AsyncMock(return_value=types.SimpleNamespace(error=None, payload={"accepted": True}))
    runner._rpc_client.send_request = rpc
    instance._set_context(PluginContext(meta.plugin_id, paths=PluginPaths(tmp_path / "data", tmp_path / "runtime")))
    runner._apply_plugin_config(meta)

    async def scenario():
        assert await runner._invoke_plugin_on_load(meta)
        assert await runner._register_plugin(meta)
        register = rpc.call_args.kwargs["payload"]
        assert {(c["name"], c["component_type"]) for c in register["components"]} == {
            ("baidu", "COMMAND"),
            ("baidu_web_search", "TOOL"),
        }
        assert register["default_config"]["plugin"]["enabled"] is False
        assert set(meta.component_handlers) == {"baidu", "baidu_web_search"}
        config = instance.build_default_config()
        config["plugin"]["enabled"] = True
        config["search"]["llm_enabled"] = True
        runner._apply_plugin_config(meta, config)
        await runner._invoke_plugin_callable(instance.on_config_update, "self", config, "0.1.0")
        assert instance._service.settings.enabled and instance._service.settings.llm_enabled
        quota_path = instance._service.quota.path
        service = SearchService(
            SearchSettings(enabled=True, llm_enabled=True, api_key="synthetic-key", daily_limit=1),
            instance._service.quota,
            FakeClient(),
        )
        instance._service = service
        handler = runner._resolve_component_handler(meta, "baidu_web_search")
        assert (await handler(query="国家博物馆官网", purpose="current_public_information"))["search_success"]
        await runner._invoke_plugin_on_unload(meta)
        assert instance._service is None
        await runner._invoke_plugin_on_load(meta)
        assert instance._service.quota.path == quota_path
        assert quota_path.exists()
        SearchError = importlib.import_module(meta.module_name + ".errors").SearchError
        with pytest.raises(SearchError) as error:
            instance._service.quota.reserve(1)
        assert error.value.code == "quota"
        # Persist the enabled state as the real admin update flow does.
        runner._save_plugin_config(str(path), config)
        # Full module purge/reload through real loader, not just lifecycle re-entry.
        runner._loader.purge_plugin_modules(meta.plugin_id, str(path))
        metas = runner._loader.discover_and_load([str(path.parent)])
        assert len(metas) == 1
        reloaded = metas[0]
        runner._apply_plugin_config(reloaded)
        reloaded.instance._set_context(instance.ctx)
        assert await runner._invoke_plugin_on_load(reloaded)
        ReloadedSearchError = importlib.import_module(reloaded.module_name + ".errors").SearchError
        with pytest.raises(ReloadedSearchError) as reload_error:
            reloaded.instance._service.quota.reserve(1)
        assert getattr(reload_error.value, "code", "") == "quota"
        await runner._invoke_plugin_on_unload(reloaded)

    asyncio.run(scenario())


def test_actual_manifest_sdk_outside_declared_range(runner_modules):
    manifest = runner_modules[2]
    validator = manifest.ManifestValidator(host_version=HOST_VERSION, sdk_version="2.16.0", log_errors=False)
    declaration = json.loads((ROOT / "_manifest.json").read_text("utf-8"))
    declaration["sdk"] = {"min_version": "2.10.0", "max_version": "2.10.0"}
    accepted = validator.validate(declaration)
    if os.environ.get("MAISEARCH_SDK_RANGE_POLICY", "reject") == "warn":
        assert accepted and not validator.errors
        assert any("SDK" in warning for warning in validator.warnings)
    else:
        assert not accepted and validator.errors
