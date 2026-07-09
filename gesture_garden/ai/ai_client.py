"""AI 客户端模块。

目标：
1. 为 Magic Canvas AI 提供统一的草图理解接口。
2. 支持不同 AI 服务替换。
3. 没有 API 或 API 调用失败时，自动返回模拟结果，保证主程序不受影响。
"""

import base64
import json
from abc import ABC, abstractmethod
from pathlib import Path
from urllib import error, request

from ai import config
from ai.prompt_builder import build_prompt


class AIProvider(ABC):
    """AI Provider 基础接口。"""

    def __init__(self, api_key="", model="", base_url=""):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    @abstractmethod
    def analyze_sketch(self, image_path):
        """分析草图，返回统一格式结果。"""
        raise NotImplementedError

    def is_ready(self):
        """判断当前 Provider 是否具备真实调用条件。"""
        return bool(self.api_key and self.model and self.base_url)


class MockProvider(AIProvider):
    """模拟 AI Provider，不调用真实 API。"""

    def analyze_sketch(self, image_path):
        return create_mock_result(image_path)


class OpenAICompatibleProvider(AIProvider):
    """OpenAI-compatible Chat Completions Provider。

    很多服务都兼容类似的请求格式，所以这里做成通用实现。
    """

    provider_name = "openai-compatible"

    def analyze_sketch(self, image_path):
        if not self.is_ready():
            return create_mock_result(image_path, error_message="AI 配置不完整，已使用模拟结果。")

        sketch_path = Path(image_path)
        if not sketch_path.exists():
            return create_mock_result(image_path, error_message=f"草图文件不存在：{sketch_path}")

        try:
            image_data_url = self._encode_image_as_data_url(sketch_path)
            payload = self._build_payload(image_data_url)
            response_data = self._post_json(payload)
            return self._parse_response(response_data, image_path)
        except Exception as exc:
            return create_mock_result(image_path, error_message=f"AI 调用失败，已使用模拟结果：{exc}")

    def _encode_image_as_data_url(self, image_path):
        """把草图图片转成 base64 data URL。"""
        image_bytes = image_path.read_bytes()
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        return f"data:image/png;base64,{encoded}"

    def _build_payload(self, image_data_url):
        """构建 Chat Completions 请求体。"""
        instruction = (
            "You are a sketch understanding assistant for an anime art generator. "
            "Analyze the user's sketch image and return ONLY valid JSON with keys: "
            "objects, scene, style, prompt. objects must be a list of short English nouns. "
            "style should describe the visual style. prompt should be an English image generation prompt."
        )

        return {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": instruction},
                        {"type": "image_url", "image_url": {"url": image_data_url}},
                    ],
                }
            ],
        }

    def _post_json(self, payload):
        """发送 JSON 请求并返回解析后的 JSON。"""
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        req = request.Request(self.base_url, data=body, headers=headers, method="POST")

        try:
            with request.urlopen(req, timeout=config.REQUEST_TIMEOUT) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc

    def _parse_response(self, response_data, image_path):
        """解析服务返回，并整理成项目统一格式。"""
        content = response_data["choices"][0]["message"]["content"]
        parsed = extract_json(content)

        objects = parsed.get("objects", [])
        scene = parsed.get("scene", "")
        style = parsed.get("style", "anime")
        prompt = parsed.get("prompt", "")

        result = {
            "objects": objects if isinstance(objects, list) else [],
            "scene": scene,
            "style": style,
            "prompt": prompt,
        }

        # 如果服务没有给 prompt，就用本地 prompt_builder 兜底生成。
        if not result["prompt"]:
            result["style"] = "anime kawaii"
            result["prompt"] = build_prompt(result)

        return result


class DeepSeekClient(OpenAICompatibleProvider):
    """DeepSeek Provider。

    使用 OpenAI-compatible 请求格式；具体模型名从 config.API_MODEL 读取。
    """

    provider_name = "deepseek"


class DoubaoClient(OpenAICompatibleProvider):
    """豆包 Provider 预留实现。

    如果填写兼容接口地址、API Key 和模型名，也可以走同一套真实调用流程。
    """

    provider_name = "doubao"


class GPTClient(OpenAICompatibleProvider):
    """GPT Provider 预留实现。

    使用 OpenAI-compatible 请求格式；具体模型名从 config.API_MODEL 读取。
    """

    provider_name = "gpt"


class AIClient:
    """项目统一 AI 客户端。"""

    def __init__(self, provider=None):
        self.provider_name = provider or config.AI_PROVIDER
        self.provider = create_provider(self.provider_name)

    def analyze_sketch(self, image_path):
        """分析草图，输出 objects、scene、style、prompt。"""
        return self.provider.analyze_sketch(image_path)

    def build_prompt_from_analysis(self, analysis_result):
        """根据已有分析结果生成 Prompt，方便测试和未来 API 接入。"""
        return build_prompt(analysis_result)


def create_provider(provider_name):
    """根据配置创建对应 Provider。"""
    normalized = (provider_name or "none").lower()

    if normalized == "deepseek":
        return DeepSeekClient(
            api_key=config.DEEPSEEK_API_KEY or config.API_KEY,
            model=config.API_MODEL,
            base_url=config.DEEPSEEK_BASE_URL,
        )

    if normalized == "doubao":
        return DoubaoClient(
            api_key=config.DOUBAO_API_KEY or config.API_KEY,
            model=config.API_MODEL,
            base_url=config.DOUBAO_BASE_URL,
        )

    if normalized == "gpt":
        return GPTClient(
            api_key=config.GPT_API_KEY or config.API_KEY,
            model=config.API_MODEL,
            base_url=config.GPT_BASE_URL,
        )

    return MockProvider()


def create_mock_result(image_path, error_message=""):
    """生成统一格式的模拟结果。"""
    analysis_result = {
        "objects": [],
        "scene": "unknown sketch scene",
        "style": "anime",
        "prompt": "",
    }
    analysis_result["style"] = "anime kawaii"
    analysis_result["prompt"] = build_prompt(analysis_result)

    if error_message:
        analysis_result["error"] = error_message

    return analysis_result


def extract_json(text):
    """从模型回复中提取 JSON。"""
    cleaned = text.strip()

    # 兼容 ```json ... ``` 代码块格式
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start : end + 1]

    return json.loads(cleaned)
