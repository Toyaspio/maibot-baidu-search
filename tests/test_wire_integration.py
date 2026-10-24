"""Real Host RPC/MsgPack/registry and real Runner loop over loopback; external HTTP mocked."""

import asyncio
import importlib
import json

import httpx
import pytest
from test_runner_integration import prepare, runner_modules  # noqa: F401


def test_host_runner_wire_tool_command_and_reload(tmp_path, runner_modules, monkeypatch):  # noqa: F811
    pytest.importorskip("jsonschema", reason="Actual Host registry needs jsonschema; run on matching Host environment")
    if not __import__("os").environ.get("MAISEARCH_HOST_SOURCE"):
        pytest.skip("Real Host source not supplied")
    main = runner_modules[1]
    monkeypatch.setattr(main, "_PROJECT_ROOT", tmp_path)
    monkeypatch.delenv("MAISEARCH_API_KEY", raising=False)
    registry_module = importlib.import_module("src.plugin_runtime.host.component_registry")
    auth_module = importlib.import_module("src.plugin_runtime.host.authorization")
    rpc_module = importlib.import_module("src.plugin_runtime.host.rpc_server")
    tcp_module = importlib.import_module("src.plugin_runtime.transport.tcp")
    runner, original, plugin_dir = prepare(tmp_path, runner_modules)
    config = original.instance.build_default_config()
    config["plugin"]["enabled"] = True
    config["search"].update(llm_enabled=True, api_key="synthetic-wire-key", daily_limit=2)
    runner._apply_plugin_config(original, config)
    runner._install_log_handler = lambda: None  # Avoid installing a global logging bridge in the pytest process.
    registry = registry_module.ComponentRegistry()
    auth = auth_module.AuthorizationManager()
    sent = []
    requests = []

    async def scenario():
        transport = tcp_module.TCPTransportServer()
        server = rpc_module.RPCServer(transport, session_token="synthetic-wire-session", host_version="1.3.5")
        ready = asyncio.Event()

        async def bootstrap(envelope):
            auth.register_plugin(envelope.plugin_id, envelope.payload["capabilities_required"])
            return envelope.make_response(payload={})

        async def register(envelope):
            assert registry.register_plugin_components(envelope.plugin_id, envelope.payload["components"]) == 2
            return envelope.make_response(payload={"accepted": True})

        async def ready_handler(envelope):
            ready.set()
            return envelope.make_response(payload={})

        async def unregister(envelope):
            registry.remove_components_by_plugin(envelope.plugin_id)
            return envelope.make_response(payload={})

        async def capability(envelope):
            capability_name = envelope.payload["capability"]
            assert auth.check_capability(envelope.plugin_id, capability_name)[0]
            assert capability_name == "send.text"
            sent.append(envelope.payload["args"]["text"])
            return envelope.make_response(payload={"result": {"success": True}})

        for name, handler in [
            ("plugin.bootstrap", bootstrap),
            ("plugin.register_components", register),
            ("runner.ready", ready_handler),
            ("plugin.unregister", unregister),
            ("cap.call", capability),
        ]:
            server.register_method(name, handler)
        await server.start()
        runner._rpc_client = importlib.import_module("src.plugin_runtime.runner.rpc_client").RPCClient(
            transport.get_address(), "synthetic-wire-session"
        )
        task = asyncio.create_task(runner.run())
        try:
            await asyncio.wait_for(ready.wait(), 10)
            assert server.is_connected
            entries = registry.get_components_by_type("TOOL")
            assert len(entries) == 1
            entry = entries[0]
            assert entry.enabled and entry.metadata["visibility"] == "visible"
            schema = entry._get_parameters_schema()
            assert schema["properties"]["purpose"]["enum"] == ["current_public_information"]
            assert set(schema["required"]) == {"query", "purpose"}

            def mock_search(request):
                requests.append(json.loads(request.content))
                return httpx.Response(
                    200,
                    json={
                        "references": [
                            {
                                "title": "公开测试来源",
                                "url": "https://example.org/",
                                "content": "仅合成资料",
                                "date": "",
                                "type": "web",
                            }
                        ]
                    },
                )

            plugin = runner._loader.get_plugin(original.plugin_id).instance
            plugin._service.client.transport = httpx.MockTransport(mock_search)
            result = await server.send_request(
                "plugin.invoke_tool",
                plugin_id=original.plugin_id,
                payload={
                    "component_name": "baidu_web_search",
                    "args": {"query": "公开新闻", "purpose": "current_public_information"},
                },
                timeout_ms=10000,
            )
            assert not result.error and result.payload["result"]["search_success"]
            history = json.loads(result.payload["result"]["content"])
            assert history["results"][0]["url"] == "https://example.org/"
            command = await server.send_request(
                "plugin.invoke_command",
                plugin_id=original.plugin_id,
                payload={
                    "component_name": "baidu",
                    "args": {"stream_id": "synthetic-stream", "matched_groups": {"query": "博物馆"}},
                },
            )
            assert not command.error and command.payload["result"][0]
            assert len(sent) == 1 and "https://example.org/" in sent[0]
            assert len(requests) == 2
            assert all(set(r) == {"messages", "search_source", "resource_type_filter"} for r in requests)
            # Real config-update RPC changes the guard immediately, without another HTTP request.
            config["search"]["llm_enabled"] = False
            # Host settings persistence precedes its notification RPC; a bare RPC is not a file save.
            runner._save_plugin_config(str(plugin_dir), config)
            update = await server.send_request(
                "plugin.config_updated",
                plugin_id=original.plugin_id,
                payload={
                    "plugin_id": original.plugin_id,
                    "config_scope": "self",
                    "config_data": config,
                    "config_version": "0.1.0",
                },
            )
            assert not update.error
            rejected = await server.send_request(
                "plugin.invoke_tool",
                plugin_id=original.plugin_id,
                payload={
                    "component_name": "baidu_web_search",
                    "args": {"query": "新闻", "purpose": "current_public_information"},
                },
            )
            assert rejected.payload["result"]["search_result"]["error"] == "llm_disabled"
            assert rejected.payload["result"]["stop_after_execution"]
            assert len(requests) == 2
            # Reload refreshes Host visibility as well, retaining committed quota on disk.
            reloaded = await server.send_request(
                "plugin.reload", plugin_id=original.plugin_id, payload={"plugin_id": original.plugin_id}
            )
            assert not reloaded.error
            entry = registry.get_components_by_type("TOOL", enabled_only=False)[0]
            assert not entry.enabled and entry.metadata["visibility"] == "hidden"
            with __import__("sqlite3").connect(tmp_path / "data/plugins" / original.plugin_id / "quota.sqlite3") as db:
                assert db.execute("SELECT calls FROM usage").fetchone()[0] == 2
        finally:
            runner._shutting_down = True
            await asyncio.wait_for(task, 5)
            await server.stop()

    asyncio.run(scenario())
