"""AI 配置模块。

这里集中保存 AI 服务配置，方便以后切换 DeepSeek、豆包、GPT、SiliconFlow 或其他兼容服务。
当前默认不启用真实 API，所以项目在没有 Key 的情况下也能正常运行。
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


PROJECT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_DIR / ".env"

# 优先读取项目目录下的 .env，避免依赖系统环境变量。
if load_dotenv is not None:
    load_dotenv(ENV_PATH)


# 可选值："none"、"deepseek"、"doubao"、"gpt"
AI_PROVIDER = os.getenv("AI_PROVIDER", "none")

# 通用 API Key。后续如果只接一个服务，可以直接填写这里。
API_KEY = os.getenv("API_KEY", "")

# 不在代码里写死模型名称，需要真实调用时在这里填写。
API_MODEL = os.getenv("API_MODEL", "")

# OpenAI-compatible Chat Completions 地址。
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/chat/completions")
DOUBAO_BASE_URL = os.getenv("DOUBAO_BASE_URL", "")
GPT_BASE_URL = os.getenv("GPT_BASE_URL", "https://api.openai.com/v1/chat/completions")

# 如果某个服务想单独使用不同 Key，可以填这里；留空时会使用 API_KEY。
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DOUBAO_API_KEY = os.getenv("DOUBAO_API_KEY", "")
GPT_API_KEY = os.getenv("GPT_API_KEY", "")

# SiliconFlow 图片生成测试配置。
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "")
SILICONFLOW_BASE_URL = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
SILICONFLOW_IMAGE_MODEL = os.getenv("SILICONFLOW_IMAGE_MODEL", "Tongyi-MAI/Z-Image-Turbo")

# 请求超时时间，避免网络问题卡住程序。
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
