"""SiliconFlow Z-Image-Turbo 独立测试脚本。

运行方式：
    python -m generation.test_zimage
"""

from generation.siliconflow_generator import SiliconFlowImageGenerator


def main():
    """使用固定 Prompt 测试图片生成。"""
    prompt = (
        "anime style cute magical girl, clean line art, pastel colors, "
        "soft lighting, high quality illustration, simple background"
    )

    generator = SiliconFlowImageGenerator()
    saved_path = generator.generate(prompt)

    if saved_path is None:
        print("测试未成功生成图片。请检查 .env 中的 API Key、网络连接和模型名称。")
        return

    print(f"测试成功，图片保存路径：{saved_path}")


if __name__ == "__main__":
    main()
