import asyncio
import re
from dataclasses import replace
from unittest.mock import AsyncMock

import pytest
from maibot_sdk.context import PluginContext, PluginPaths
from maisearch import COMMAND_PATTERN, MaiSearchConfig, create_plugin
from maisearch.quota_manager import QuotaManager
from maisearch.search_service import SearchService, SearchSettings
from pydantic import ValidationError
from test_search_service import FakeClient


def configured(tmp_path, monkeypatch):
    monkeypatch.delenv("MAISEARCH_API_KEY", raising=False)
    instance = create_plugin()
    rpc = AsyncMock(return_value={"success": True})
    instance._set_context(
        PluginContext(
            "toyaspio.maibot-baidu-search", rpc_call=rpc, paths=PluginPaths(tmp_path / "data", tmp_path / "runtime")
        )
    )
    instance.set_plugin_config(instance.build_default_config())
    return instance, rpc


@pytest.mark.parametrize(
    "text,query", [("/baidu 明朝内阁", "明朝内阁"), ("/baidu", None), ("/baidu ", ""), ("/baidu\t新闻", "新闻")]
)
def test_command_matching(text, query):
    match = re.search(COMMAND_PATTERN, text)
    assert match and match.group("query") == query


@pytest.mark.parametrize("text", ["普通聊天", "我要/baidu 新闻", "/baidux 新闻", "/baidu新闻", "/baidu 新闻\n额外内容"])
def test_no_false_match(text):
    assert not re.search(COMMAND_PATTERN, text)


def test_sdk_config_schema_and_components(tmp_path, monkeypatch):
    instance, _ = configured(tmp_path, monkeypatch)
    assert not instance.config.plugin.enabled and not instance.config.search.llm_enabled
    schema = instance.get_webui_config_schema()
    assert schema and instance.config.plugin.config_version == "0.1.0"
    components = {item["name"]: item for item in instance.get_components()}
    assert set(components) == {"baidu", "baidu_web_search"}
    assert components["baidu"]["type"] == "COMMAND"
    assert components["baidu_web_search"]["type"] == "TOOL"
    assert components["baidu"]["metadata"]["handler_name"] == "handle_baidu"
    assert components["baidu_web_search"]["metadata"]["handler_name"] == "handle_search"


@pytest.mark.parametrize(
    "field,value",
    [
        ("daily_limit", 101),
        ("daily_limit", -1),
        ("max_results", 0),
        ("max_results", 11),
        ("tool_daily_limit", 21),
        ("timeout_seconds", 31),
        ("max_query_length", 241),
        ("auth_header", "Custom-Auth"),
    ],
)
def test_config_constraints(field, value):
    with pytest.raises(ValidationError):
        MaiSearchConfig.model_validate({"search": {field: value}})


def test_lifecycle_env_precedence_and_update(tmp_path, monkeypatch):
    instance, _ = configured(tmp_path, monkeypatch)
    config = instance.build_default_config()
    config["search"]["api_key"] = "synthetic-config-key"
    instance.set_plugin_config(config)
    monkeypatch.setenv("MAISEARCH_API_KEY", "synthetic-environment-key")

    async def scenario():
        await instance.on_load()
        assert instance._service.settings.api_key == "synthetic-environment-key"
        assert not instance._service.settings.enabled
        config["plugin"]["enabled"] = True
        config["search"]["llm_enabled"] = True
        instance.set_plugin_config(config)  # Actual Runner injects before callback.
        await instance.on_config_update("self", config, "0.1.0")
        assert instance._service.settings.enabled and instance._service.settings.llm_enabled
        old = instance._service
        await instance.on_config_update("bot", {}, "other")
        assert instance._service is old
        await instance.on_unload()
        assert instance._service is None
        await instance.on_load()
        assert instance._service.quota.path == tmp_path / "data" / "quota.sqlite3"

    asyncio.run(scenario())


def test_command_and_tool_use_same_service(tmp_path, monkeypatch):
    instance, rpc = configured(tmp_path, monkeypatch)
    client = FakeClient()
    instance._service = SearchService(
        SearchSettings(enabled=True, llm_enabled=True, api_key="synthetic-key", daily_limit=2),
        QuotaManager(tmp_path / "q.sqlite3"),
        client,
    )

    async def scenario():
        assert (await instance.handle_baidu(stream_id="synthetic-stream", matched_groups={"query": "博物馆"}))[0]
        assert (
            await instance.handle_search(
                query="新闻",
                purpose="current_public_information",
                message={"text": "synthetic-private-chat"},
                user_id="synthetic-private-id",
                memory="synthetic-private-memory",
            )
        )["search_success"]
        assert (await instance.handle_baidu(stream_id="synthetic-stream", matched_groups={"query": "博物馆"}))[0]

    asyncio.run(scenario())
    assert len(client.calls) == 2
    assert client.calls == [("博物馆", 5), ("新闻", 5)]
    assert rpc.call_count == 2
    assert "今日搜索额度已用完" in str(rpc.call_args)
    assert "synthetic-key" not in str(rpc.call_args_list)


def test_missing_stream_does_not_search(tmp_path, monkeypatch):
    instance, _ = configured(tmp_path, monkeypatch)
    instance._service = AsyncMock()
    assert not asyncio.run(instance.handle_baidu(matched_groups={"query": "新闻"}))[0]
    instance._service.search.assert_not_called()


def test_send_failure_is_bounded(tmp_path, monkeypatch):
    instance, rpc = configured(tmp_path, monkeypatch)
    rpc.side_effect = RuntimeError("SENSITIVE")
    instance._service = SearchService(replace(SearchSettings(), enabled=True), QuotaManager(tmp_path / "q.sqlite3"))
    success, message, block = asyncio.run(
        instance.handle_baidu(stream_id="synthetic-stream", matched_groups={"query": "新闻"})
    )
    assert not success and "SENSITIVE" not in message and block == 2
    assert rpc.call_count == 1
