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

    def copy(self):
        """复制当前笔画，用于撤销历史。"""
        new_stroke = Stroke(self.color, self.width)
        new_stroke.points = list(self.points)
        return new_stroke

    def draw(self, screen):
        """绘制干净的专业绘图线条，基本不使用泛光。"""
        if not self.points:
            return

        if len(self.points) == 1:
            self._draw_point(screen, self.points[0])
            return

        # 只保留一层非常轻的柔边，避免旧版本那种强泛光。
        edge_layer = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        pygame.draw.lines(edge_layer, (*self.color, 45), False, self.points, self.width + 2)
        screen.blit(edge_layer, (0, 0))

        # 主线条。端点和转折点用圆形补齐，让线条更连续。
        pygame.draw.lines(screen, self.color, False, self.points, self.width)
        for point in self.points:
            pygame.draw.circle(screen, self.color, point, max(2, self.width // 2))

    def _draw_point(self, screen, point):
        """绘制单个点，适合一笔刚开始时显示。"""
        pygame.draw.circle(screen, self.color, point, max(2, self.width // 2))
