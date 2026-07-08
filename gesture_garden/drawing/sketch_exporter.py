"""草图导出工具。

这个模块负责把 Canvas 中保存的线条导出成 AI 后续可以读取的 PNG 文件。
导出的图片只包含用户草图，不包含摄像头预览和界面 UI。
"""

from datetime import datetime
from pathlib import Path

import pygame


PROJECT_DIR = Path(__file__).resolve().parents[1]
SKETCH_DIR = PROJECT_DIR / "data" / "sketches"


def export_sketch(canvas):
    """将 Canvas 当前内容保存为 PNG，并返回保存路径。"""
    # 自动创建 data/sketches 文件夹
    SKETCH_DIR.mkdir(parents=True, exist_ok=True)

    # 使用时间戳作为文件名，避免覆盖旧草图
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = SKETCH_DIR / f"sketch_{timestamp}.png"

    # 重新创建一张独立画布，只绘制草图内容，方便后续 AI 读取
    export_surface = pygame.Surface((canvas.width, canvas.height), pygame.SRCALPHA)
    export_surface.fill((0, 0, 0, 0))

    for stroke in canvas.strokes:
        stroke.draw(export_surface)

    pygame.image.save(export_surface, str(save_path))
    return save_path
