"""Prompt 构建模块。

输入草图分析结果，输出适合二次元图片生成模型使用的 Prompt。
当前阶段只做规则拼接，不调用任何真实 AI API。
"""


FIXED_STYLE_WORDS = [
    "anime illustration",
    "kawaii",
    "Japanese style",
    "pastel color",
    "fantasy",
]


def build_prompt(analysis_result):
    """根据草图分析结果生成二次元图片 Prompt。"""
    objects = analysis_result.get("objects", [])

    # 如果模拟分析里没有对象，就使用比较通用的画布描述
    if objects:
        object_text = ", ".join(objects)
    else:
        object_text = "a magical character or object inspired by the user's sketch"

    style_text = ", ".join(FIXED_STYLE_WORDS)
    prompt = (
        f"Create an {style_text}. "
        f"Main subject: {object_text}. "
        "Use clean line art, soft glowing details, cute proportions, "
        "gentle lighting, and a dreamy magical atmosphere."
    )

    return {
        "style": "anime kawaii",
        "prompt": prompt,
    }
