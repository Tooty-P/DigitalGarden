"""一次连续绘画轨迹。"""

import pygame


class Stroke:
    """保存一笔连续线条。"""

    def __init__(self, color=(124, 230, 255), width=6):
        # points 按时间顺序保存食指或鼠标经过的位置
        self.points = []
        self.color = color
        self.width = width

    def add_point(self, point):
        """向这一笔中加入一个新点。"""
        self.points.append((int(point[0]), int(point[1])))

    def draw(self, screen):
        """绘制带柔和发光感的线条。"""
        if not self.points:
            return

        glow_layer = pygame.Surface(screen.get_size(), pygame.SRCALPHA)

        # 只有一个点时也要画出来，否则刚开始绘画会没有反馈
        if len(self.points) == 1:
            self._draw_point(screen, glow_layer, self.points[0])
            screen.blit(glow_layer, (0, 0))
            return

        # 多层半透明线条叠加，模拟魔法发光画笔
        pygame.draw.lines(glow_layer, (*self.color, 35), False, self.points, self.width + 18)
        pygame.draw.lines(glow_layer, (*self.color, 70), False, self.points, self.width + 10)
        pygame.draw.lines(glow_layer, (*self.color, 110), False, self.points, self.width + 4)
        screen.blit(glow_layer, (0, 0))

        # 主线条和中心高光，线端用圆补一下，看起来更圆润连续
        pygame.draw.lines(screen, self.color, False, self.points, self.width)
        pygame.draw.lines(screen, (245, 252, 255), False, self.points, max(2, self.width // 2))

        for point in self.points:
            pygame.draw.circle(screen, self.color, point, max(2, self.width // 2))
            pygame.draw.circle(screen, (245, 252, 255), point, max(1, self.width // 4))

    def _draw_point(self, screen, glow_layer, point):
        """绘制单个点，适合一笔刚开始时显示。"""
        pygame.draw.circle(glow_layer, (*self.color, 45), point, self.width + 12)
        pygame.draw.circle(glow_layer, (*self.color, 95), point, self.width + 5)
        pygame.draw.circle(screen, self.color, point, max(2, self.width // 2))
        pygame.draw.circle(screen, (245, 252, 255), point, max(1, self.width // 4))
