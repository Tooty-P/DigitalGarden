"""检查 .env 是否能正确读取 SiliconFlow 配置。

运行方式：
    python test_env.py
"""

import os
from pathlib import Path


try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = None


def key_prefix(value, length=6):
    """只显示 API Key 前几位，避免泄露完整 Key。"""
    if not value:
        return ""
    return value[:length]


def main():
    """读取并打印 SiliconFlow 相关环境变量状态。"""
    project_dir = Path(__file__).resolve().parent
    env_path = project_dir / ".env"

    print("Env file:", env_path)

    if load_dotenv is None:
        print("依赖缺失：没有安装 python-dotenv。")
        print("请在 Windows 终端执行：python -m pip install python-dotenv")
        return

    # 明确读取项目根目录下的 .env，并覆盖可能存在的空环境变量。
    loaded = load_dotenv(env_path, override=True)

    api_key = os.getenv("SILICONFLOW_API_KEY", "")
    base_url = os.getenv("SILICONFLOW_BASE_URL", "")
    model = os.getenv("SILICONFLOW_IMAGE_MODEL", "")

    print("Env loaded:", loaded)
    print("base_url:", base_url)
    print("model:", model)
    print("key exists:", bool(api_key))
    print("key length:", len(api_key))
    print("key prefix:", key_prefix(api_key))

    if not env_path.exists():
        print("诊断：没有找到 .env 文件，请确认它位于当前项目根目录。")
    elif not loaded:
        print("诊断：.env 没有被成功读取，请检查文件名是否为 .env。")
    elif not api_key:
        print("诊断：没有读取到 SILICONFLOW_API_KEY，请检查 .env 中变量名是否正确。")
    elif api_key == "你的_api_key":
        print("诊断：SILICONFLOW_API_KEY 仍是占位文本，请替换为真实 Key。")
    else:
        print("诊断：.env 基础读取正常。")


if __name__ == "__main__":
    main()
