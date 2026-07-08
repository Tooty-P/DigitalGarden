"""图片生成接口测试文件。

运行：
py -3.12 test_image_generator.py
"""

import pygame

from generation.image_generator import ImageGenerator


if __name__ == "__main__":
    pygame.init()
    generator = ImageGenerator()
    image_path = generator.generate("anime kawaii magical canvas test")
    pygame.quit()
    print(f"模拟生成图片路径：{image_path}")
