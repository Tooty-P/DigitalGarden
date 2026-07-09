"""独立测试 SiliconFlow Z-Image-Turbo 图片生成 API。

运行方式：
    python test_siliconflow_auth.py
"""

import os
from pathlib import Path


try:
    import requests
except ModuleNotFoundError:
    requests = None

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = None


DEFAULT_BASE_URL = "https://api.siliconflow.cn/v1"
DEFAULT_MODEL = "Tongyi-MAI/Z-Image-Turbo"
TEST_PROMPT = "a cute anime style cat in a pastel fantasy garden"


def key_prefix(api_key, length=6):
    """只显示 API Key 前几位，避免泄露完整 Key。"""
    if not api_key:
        return ""
    return api_key[:length]


def diagnose_status_code(status_code):
    """根据 HTTP 状态码输出中文诊断。"""
    if status_code == 200:
        return "请求成功。"
    if status_code == 400:
        return "请求参数错误：请检查 model、prompt、image_size 等字段。"
    if status_code == 401:
        return "API Key 无效、格式错误，或认证失败。"
    if status_code == 403:
        return "权限、额度或模型可用性问题：账号可能无权调用该模型。"
    if status_code == 404:
        return "URL 错误：请检查 SILICONFLOW_BASE_URL 或接口路径。"
    if status_code == 429:
        return "请求被限流：调用太频繁或额度受限。"
    if status_code == 503:
        return "服务繁忙或暂不可用，请稍后重试。"
    if status_code >= 500:
        return "服务端错误，请稍后重试或查看 SiliconFlow 服务状态。"
    return "未知状态码，请结合 Response Text 判断。"


def main():
    """读取 .env 并发送一次最小图片生成请求。"""
    project_dir = Path(__file__).resolve().parent
    env_path = project_dir / ".env"

    if requests is None:
        print("依赖缺失：没有安装 requests。")
        print("请在 Windows 终端执行：python -m pip install requests")
        return

    if load_dotenv is None:
        print("依赖缺失：没有安装 python-dotenv。")
        print("请在 Windows 终端执行：python -m pip install python-dotenv")
        return

    loaded = load_dotenv(env_path, override=True)

    api_key = os.getenv("SILICONFLOW_API_KEY", "")
    base_url = os.getenv("SILICONFLOW_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    model = os.getenv("SILICONFLOW_IMAGE_MODEL", DEFAULT_MODEL)
    request_url = f"{base_url}/images/generations"

    print("Request URL:", request_url)
    print("Model:", model)
    print("Key loaded:", bool(api_key))
    print("Key prefix:", key_prefix(api_key))

    if not env_path.exists():
        print("友好提示：没有找到 .env 文件，请确认它位于当前项目根目录。")
        return

    if not loaded:
        print("友好提示：.env 没有被 python-dotenv 成功读取，请检查文件名是否为 .env。")
        return

    if not api_key:
        print("友好提示：API Key 缺失，请检查 .env 中的 SILICONFLOW_API_KEY。")
        return

    if api_key == "你的_api_key":
        print("友好提示：API Key 仍是占位文本，请替换为真实 SiliconFlow Key。")
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "prompt": TEST_PROMPT,
        "image_size": "1024x1024",
    }

    try:
        response = requests.post(request_url, headers=headers, json=payload, timeout=60)
        print("Status Code:", response.status_code)
        print("Response Text:", response.text)
        print("诊断：", diagnose_status_code(response.status_code))

        if response.status_code == 200:
            try:
                data = response.json()
            except ValueError:
                print("返回格式异常：响应不是合法 JSON。")
                return

            images = data.get("data")
            if not isinstance(images, list) or not images:
                print("返回格式异常：没有找到 data 图片列表。")
                return

            first_image = images[0]
            if not isinstance(first_image, dict):
                print("返回格式异常：data[0] 不是对象。")
                return

            if first_image.get("url") or first_image.get("b64_json") or first_image.get("base64"):
                print("返回格式正常：已找到图片 URL 或 base64 图片数据。")
            else:
                print("返回格式异常：没有找到图片 URL 或 base64 图片数据。")

    except requests.exceptions.MissingSchema:
        print("友好提示：base_url 格式错误，缺少 http:// 或 https://。")
    except requests.exceptions.ConnectionError as exc:
        print("友好提示：网络连接失败，可能是网络、域名、代理或防火墙问题。")
        print("错误详情：", exc)
    except requests.exceptions.Timeout:
        print("友好提示：请求超时，可能是网络较慢或服务暂时无响应。")
    except requests.exceptions.RequestException as exc:
        print("友好提示：请求失败。")
        print("错误详情：", exc)
    except Exception as exc:
        print("友好提示：发生未预期错误，但程序已捕获，不会直接崩溃。")
        print("错误详情：", exc)


if __name__ == "__main__":
    main()
