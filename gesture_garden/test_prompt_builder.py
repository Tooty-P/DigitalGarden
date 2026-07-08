"""Prompt 构建测试文件。

运行：
py -3.12 test_prompt_builder.py
"""

from ai.ai_client import AIClient
from ai.prompt_builder import build_prompt


mock_analysis = {
    "objects": ["cat girl", "magic wand", "floating stars"],
    "style": "anime",
    "prompt": "",
}


if __name__ == "__main__":
    direct_result = build_prompt(mock_analysis)
    print("直接生成 Prompt：")
    print(direct_result)

    client = AIClient()
    client_result = client.build_prompt_from_analysis(mock_analysis)
    print("\n通过 AIClient 生成 Prompt：")
    print(client_result)
