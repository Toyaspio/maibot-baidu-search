"""Public error messages never include provider response bodies or exceptions."""

MESSAGES = {
    "disabled": "百度搜索尚未启用。",
    "llm_disabled": "大模型自主搜索尚未启用。",
    "missing_key": "未配置百度 API Key，请由管理员在本机安全设置。",
    "invalid_key": "API Key 格式无效，请由管理员检查。",
    "invalid_query": "请输入长度合规的单行公开信息搜索词。",
    "privacy": "搜索词包含疑似私人资料、凭证或路径，请改用不含私人信息的公开关键词。",
    "necessity": "自主搜索仅用于需要核实最新公开信息的问题。",
    "quota": "北京时间今日搜索额度已用完。",
    "tool_quota": "今日自主搜索额度已用完，请停止调用搜索工具。",
    "cooldown": "自主搜索处于冷却期或近期已搜索过该词，请使用已有结果并停止重复调用。",
    "quota_storage": "额度存储异常，已暂停搜索，请管理员检查；不会自动重置额度。",
    "clock": "检测到时间回退，已暂停搜索，请管理员检查系统时间。",
    "auth": "百度鉴权失败，请管理员核对密钥、权限及鉴权 Header。",
    "rate_limit": "百度服务限流，请稍后再试；本次尝试已计入额度。",
    "timeout": "百度搜索超时；本次尝试已计入额度。",
    "network": "网络连接或 DNS 异常；本次尝试已计入额度。",
    "http": "百度 HTTP 服务异常；本次尝试已计入额度。",
    "provider": "百度返回业务错误；本次尝试已计入额度。",
    "invalid_response": "百度返回的数据格式异常；本次尝试已计入额度。",
    "response_too_large": "百度响应过大，已停止读取；本次尝试已计入额度。",
    "unavailable": "搜索暂时不可用，请稍后再试。",
    "send": "搜索完成，但消息发送失败。",
}


class SearchError(Exception):
    def __init__(self, code: str):
        self.code = code if code in MESSAGES else "unavailable"
        super().__init__(MESSAGES[self.code])

    def result(self) -> dict:
        return {"success": False, "error": self.code, "message": str(self), "results": []}
