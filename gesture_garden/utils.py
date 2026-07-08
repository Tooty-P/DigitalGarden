"""工具函数模块。"""

from datetime import datetime
from pathlib import Path

import pygame


def clamp(value, minimum, maximum):
    """把数值限制在 minimum 到 maximum 之间。"""
    return max(minimum, min(value, maximum))


def save_surface_image(screen, prefix="sketch", folder_name="screenshots"):
    """保存当前 Pygame 画面，并返回保存路径。"""
    # screenshots 文件夹放在当前项目目录下
    project_dir = Path(__file__).resolve().parent
    output_dir = project_dir / folder_name
    output_dir.mkdir(exist_ok=True)

    # 使用时间戳生成文件名，避免覆盖旧文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = output_dir / f"{prefix}_{timestamp}.png"

    pygame.image.save(screen, str(save_path))
    return save_path


def save_screenshot(screen):
    """兼容旧功能：保存当前 Pygame 画面截图。"""
    return save_surface_image(screen, prefix="garden", folder_name="screenshots")
