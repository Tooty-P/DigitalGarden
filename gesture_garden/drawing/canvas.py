"""魔法绘画画布。"""

import math

from drawing.stroke import Stroke
from drawing.sketch_exporter import export_sketch


class Canvas:
    """负责保存、绘制、清空用户的绘画轨迹。"""

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.strokes = []
        self.current_stroke = None

        # 几个适合二次元魔法画布的柔和颜色
        self.palette = [
            (118, 229, 255),  # 青蓝
            (255, 154, 208),  # 粉色
            (190, 164, 255),  # 浅紫
            (255, 234, 137),  # 奶油黄
            (152, 255, 202),  # 薄荷绿
        ]
        self.color_names = ["青蓝", "粉色", "浅紫", "奶油黄", "薄荷绿"]
        self.color_index = 0
        self.brush_color = self.palette[self.color_index]
        self.brush_width = 6

        # 平滑相关参数：数值越小越稳，越大越跟手
        self.smoothing = 0.35
        self.min_point_distance = 3
        self.smoothed_point = None

        # 切换颜色或粗细时，下一次输入会从当前位置重新开一笔
        self.should_restart_stroke = False

    def start_stroke(self, point):
        """开始一笔新的绘画。"""
        safe_point = self._clamp_point(point)
        self.smoothed_point = safe_point
        self.should_restart_stroke = False
        self.current_stroke = Stroke(self.brush_color, self.brush_width)
        self.current_stroke.add_point(safe_point)
        self.strokes.append(self.current_stroke)

    def add_point(self, point):
        """把食指或鼠标当前位置加入当前线条。"""
        if self.current_stroke is None or self.should_restart_stroke:
            self.start_stroke(point)
            return

        new_point = self._smooth_point(self._clamp_point(point))
        last_point = self.current_stroke.points[-1]

        # 点之间距离太近时不记录，减少手势抖动带来的锯齿
        if self._distance(last_point, new_point) >= self.min_point_distance:
            self.current_stroke.add_point(new_point)

    def end_stroke(self):
        """结束当前这一笔。"""
        self.current_stroke = None
        self.smoothed_point = None
        self.should_restart_stroke = False

    def clear(self):
        """清空画布上的所有线条。"""
        self.strokes.clear()
        self.current_stroke = None
        self.smoothed_point = None
        self.should_restart_stroke = False

    def set_brush_width(self, width):
        """设置画笔粗细，并限制在适合绘画的范围。"""
        new_width = max(2, min(18, int(width)))
        if new_width != self.brush_width:
            self.brush_width = new_width
            self._request_restart_stroke()

    def change_brush_width(self, amount):
        """增加或减少画笔粗细。"""
        self.set_brush_width(self.brush_width + amount)

    def set_color_by_index(self, index):
        """根据调色板编号切换颜色。"""
        new_index = index % len(self.palette)
        if new_index != self.color_index:
            self.color_index = new_index
            self.brush_color = self.palette[self.color_index]
            self._request_restart_stroke()

    def next_color(self):
        """切换到下一个颜色。"""
        self.set_color_by_index(self.color_index + 1)

    def draw(self, screen):
        """绘制已经保存的所有线条。"""
        for stroke in self.strokes:
            stroke.draw(screen)

    def save_sketch(self, screen=None):
        """导出当前草图，供后续 AI 读取。"""
        return export_sketch(self)

    def _request_restart_stroke(self):
        """请求下一次绘画输入使用新笔刷重新开笔。"""
        if self.current_stroke is not None:
            self.should_restart_stroke = True
            self.smoothed_point = None

    def _smooth_point(self, point):
        """对输入点做简单缓动平滑，减少摄像头手势抖动。"""
        if self.smoothed_point is None:
            self.smoothed_point = point
            return point

        old_x, old_y = self.smoothed_point
        new_x, new_y = point
        smooth_x = old_x + (new_x - old_x) * self.smoothing
        smooth_y = old_y + (new_y - old_y) * self.smoothing
        self.smoothed_point = (smooth_x, smooth_y)
        return self.smoothed_point

    def _clamp_point(self, point):
        """把点限制在窗口范围内，避免线条画到窗口外。"""
        x = max(0, min(self.width - 1, point[0]))
        y = max(0, min(self.height - 1, point[1]))
        return (x, y)

    def _distance(self, point_a, point_b):
        """计算两个点之间的距离。"""
        return math.hypot(point_a[0] - point_b[0], point_a[1] - point_b[1])
