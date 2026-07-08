"""AI Client 测试文件。

运行：
py -3.12 test_ai_client.py

默认没有 API Key 时会返回模拟分析结果。
"""

from ai.ai_client import AIClient


if __name__ == "__main__":
    client = AIClient()
    result = client.analyze_sketch("missing_sketch.png")
    print("AI 草图分析结果：")
    print(result)
