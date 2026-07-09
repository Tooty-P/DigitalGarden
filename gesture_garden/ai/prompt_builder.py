"""Magic Canvas AI 的 Prompt 构建模块。

目标：优先生成和用户主题、关键词相关的场景图，避免默认总是生成人物。
"""


STYLE_DESCRIPTION = (
    "anime illustration, Japanese kawaii style, pastel colors, "
    "soft lighting, fantasy atmosphere, clean composition"
)


THEME_DESCRIPTIONS = {
    "garden": "cute anime fantasy garden scene, flowers, trees, magical plants",
    "pet": "cute fantasy pet, small magical creature, soft environment",
    "room": "cute anime style magical room interior",
    "sky_island": "floating island, clouds, tiny house, fantasy sky scene",
    "character": "cute anime character, full body, fantasy costume",
}


def build_prompt(theme=None, extra_keywords=None):
    """根据主题和用户补充关键词生成英文图片 Prompt。"""
    theme_key = _normalize_theme(theme)
    theme_description = THEME_DESCRIPTIONS[theme_key]
    keyword_text = _normalize_keywords(extra_keywords)

    prompt_parts = [
        theme_description,
    ]

    # 用户关键词优先放在主题后面，用来提高和输入内容的相关性。
    if keyword_text:
        prompt_parts.append(f"user provided visual keywords: {keyword_text}")

    prompt_parts.append(f"style: {STYLE_DESCRIPTION}")

    if theme_key != "character":
        # 非 character 主题明确压低人物倾向，解决默认总生成人物的问题。
        prompt_parts.append("focus on scene and objects, no portrait, no main human character")
    else:
        prompt_parts.append("character focused, full body, not just a portrait")

    return ". ".join(prompt_parts) + "."


def _normalize_theme(theme):
    """把主题归一化为受支持的主题名。"""
    if isinstance(theme, dict):
        theme = theme.get("theme") or "garden"

    theme_key = str(theme or "garden").strip().lower().replace(" ", "_")
    return theme_key if theme_key in THEME_DESCRIPTIONS else "garden"


def _normalize_keywords(extra_keywords):
    """支持字符串或列表形式的关键词输入。"""
    if not extra_keywords:
        return ""

    if isinstance(extra_keywords, str):
        return " ".join(extra_keywords.split())

    return ", ".join(str(keyword).strip() for keyword in extra_keywords if str(keyword).strip())


if __name__ == "__main__":
    # 简单测试：默认不应生成明显人物主体。
    print("Garden:")
    print(build_prompt("garden", "flowers tree small house"))

    print("\nPet:")
    print(build_prompt("pet", "cat wings star"))

    print("\nRoom:")
    print(build_prompt("room", "bed window moon plant"))

    print("\nCharacter:")
    print(build_prompt("character", "pink hair magical staff"))
