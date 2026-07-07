"""工具函数模块。

这里放一些项目中会复用的小函数。
"""


def clamp(value, minimum, maximum):
    """把数值限制在 minimum 到 maximum 之间。"""
    return max(minimum, min(value, maximum))
