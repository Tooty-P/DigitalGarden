"""SiliconFlow Z-Image-Turbo 图片生成测试模块。

这个模块提供可复用的 SiliconFlow 图片生成能力，也可以被独立测试脚本调用。
"""

import base64
import time
from pathlib import Path

import requests

from ai import config


PROJECT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_DIR / "outputs" / "generated"


class SiliconFlowImageGenerator:
    """SiliconFlow 图片生成器。"""

    def __init__(self, api_key=None, base_url=None, model=None):
        self.api_key = api_key or config.SILICONFLOW_API_KEY
        self.base_url = (base_url or config.SILICONFLOW_BASE_URL).rstrip("/")
        self.model = model or config.SILICONFLOW_IMAGE_MODEL
        self.last_error = ""

    def generate(self, prompt):
        """根据 prompt 请求 SiliconFlow 生成图片，并返回本地图片路径。"""
        self.last_error = ""

        if not self._has_valid_api_key():
            return self._fail("SiliconFlow API Key 缺失或仍是占位文本，请先在 .env 中填写真实 SILICONFLOW_API_KEY。")

        if not prompt.strip():
            return self._fail("Prompt 不能为空。")

        try:
            response_data = self._request_image(prompt)
            image_url, image_base64 = self._extract_image_result(response_data)

            if image_url:
                return self._download_image(image_url)

            if image_base64:
                return self._save_base64_image(image_base64)

            print(f"返回内容：{response_data}")
            return self._fail("SiliconFlow 返回格式异常：没有找到图片 URL 或 base64 图片数据。")
        except requests.HTTPError as exc:
            detail = ""
            if exc.response is not None:
                detail = f"HTTP {exc.response.status_code}: {exc.response.text}"
            return self._fail(f"SiliconFlow API 返回错误：{detail or exc}")
        except requests.RequestException as exc:
            return self._fail(f"请求 SiliconFlow API 失败，可能是网络或接口地址问题：{exc}")
        except Exception as exc:
            return self._fail(f"处理 SiliconFlow 返回结果失败：{exc}")

    def _fail(self, message):
        """记录友好错误信息并返回 None，避免主程序崩溃。"""
        self.last_error = message
        print(message)
        return None

    def _has_valid_api_key(self):
        """判断 API Key 是否可用。"""
        return bool(self.api_key and self.api_key.strip() and self.api_key != "你的_api_key")

    def _request_image(self, prompt):
        """发送图片生成请求。"""
        endpoint = f"{self.base_url}/images/generations"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "prompt": prompt,
            "image_size": "1024x1024",
        }

        print(f"正在请求 SiliconFlow 图片生成 API：{self.model}")
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=config.REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()

    def _extract_image_result(self, response_data):
        """从返回 JSON 中提取图片 URL 或 base64 数据。"""
        # SiliconFlow 可能返回 data，也可能同时返回 images；两种格式都兼容。
        data = response_data.get("data") or response_data.get("images")
        if not isinstance(data, list) or not data:
            return None, None

        first_item = data[0]
        if not isinstance(first_item, dict):
            return None, None

        image_url = first_item.get("url")
        image_base64 = first_item.get("b64_json") or first_item.get("base64")
        return image_url, image_base64

    def _download_image(self, image_url):
        """下载图片 URL 并保存到 outputs/generated。"""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = OUTPUT_DIR / self._build_file_name()

        print("正在下载生成图片...")
        try:
            # 生成图文件较大时下载可能超过接口请求超时，下载阶段给更宽松的时间。
            response = requests.get(image_url, timeout=max(config.REQUEST_TIMEOUT, 90))
            response.raise_for_status()
            output_path.write_bytes(response.content)
        except requests.RequestException as exc:
            return self._fail(f"图片下载失败，可能是临时图片地址访问慢或网络不稳定：{exc}")

        print(f"图片已保存：{output_path}")
        return output_path

    def _save_base64_image(self, image_base64):
        """保存 base64 图片数据。"""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = OUTPUT_DIR / self._build_file_name()

        if image_base64.startswith("data:image"):
            image_base64 = image_base64.split(",", 1)[1]

        image_bytes = base64.b64decode(image_base64)
        output_path.write_bytes(image_bytes)

        print(f"图片已保存：{output_path}")
        return output_path

    def _build_file_name(self):
        """生成图片文件名。"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        return f"zimage_{timestamp}.png"
