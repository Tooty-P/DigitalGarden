"""图片生成接口模块。

当前阶段不绑定具体图片模型，只提供统一接口和模拟输出。
以后可以替换为豆包图片 API、OpenAI Image API 或 Stable Diffusion。
"""

from datetime import datetime
from pathlib import Path

import pygame


PROJECT_DIR = Path(__file__).resolve().parents[1]
GENERATED_DIR = PROJECT_DIR / "data" / "generated"


class ImageGenerator:
    """可替换的图片生成器。"""

    def __init__(self, provider="mock"):
        # provider 预留给未来切换不同图片生成服务
        self.provider = provider

    def generate(self, prompt):
        """根据 prompt 生成图片，并返回图片路径。

        当前阶段只生成一张模拟占位图，不调用真实 API。
        """
        return self._generate_mock_image(prompt)

    def _generate_mock_image(self, prompt):
        """生成本地模拟图片，方便主流程测试。"""
        GENERATED_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = GENERATED_DIR / f"generated_{timestamp}.png"

        width = 960
        height = 540
        surface = pygame.Surface((width, height))

        # 简单画一个柔和渐变背景，作为“模拟生成结果”
        top_color = (235, 248, 255)
        bottom_color = (255, 231, 247)
        for y in range(height):
            t = y / height
            color = (
                int(top_color[0] * (1 - t) + bottom_color[0] * t),
                int(top_color[1] * (1 - t) + bottom_color[1] * t),
                int(top_color[2] * (1 - t) + bottom_color[2] * t),
            )
            pygame.draw.line(surface, color, (0, y), (width, y))

        # 用基础图形画一个占位构图，表示这里将来会替换成真实 AI 图
        pygame.draw.circle(surface, (118, 229, 255), (width // 2, 230), 95)
        pygame.draw.circle(surface, (255, 255, 255), (width // 2 - 32, 210), 16)
        pygame.draw.circle(surface, (255, 255, 255), (width // 2 + 32, 210), 16)
        pygame.draw.arc(surface, (68, 98, 142), (width // 2 - 38, 228, 76, 48), 0.2, 2.9, 4)

        font = pygame.font.Font(None, 28)
        title = font.render("Mock Generated Image", True, (54, 80, 120))
        hint = font.render("Future API output will appear here", True, (82, 110, 150))
        surface.blit(title, title.get_rect(center=(width // 2, 365)))
        surface.blit(hint, hint.get_rect(center=(width // 2, 398)))

        pygame.image.save(surface, str(output_path))
        return output_path
