"""魔法绘画画布。"""

import math

from drawing.stroke import Stroke
from drawing.sketch_exporter import export_sketch


class Canvas:
    """负责保存、绘制、清空、撤销用户的绘画轨迹。"""

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.strokes = []
        self.current_stroke = None
        self.undo_stack = []
        self.max_undo_steps = 30

        # 12 个适合草图和二次元绘图的预设颜色。
        self.palette = [
            (245, 252, 255),  # 白色
            (40, 48, 62),     # 深灰
            (118, 229, 255),  # 青蓝
            (68, 158, 255),   # 蓝色
            (190, 164, 255),  # 浅紫
            (255, 154, 208),  # 粉色
            (255, 116, 135),  # 珊瑚红
            (255, 178, 94),   # 橙色
            (255, 234, 137),  # 奶油黄
            (152, 255, 202),  # 薄荷绿
            (93, 214, 134),   # 草绿
            (191, 204, 220),  # 蓝灰
        ]
        self.color_names = [
            "白色", "深灰", "青蓝", "蓝色", "浅紫", "粉色",
            "珊瑚红", "橙色", "奶油黄", "薄荷绿", "草绿", "蓝灰",
        ]
        self.color_index = 2
        self.brush_color = self.palette[self.color_index]
        self.brush_width = 6

        # 平滑相关参数：数值越小越稳，越大越跟手。
        self.smoothing = 0.35
        self.min_point_distance = 3
        self.smoothed_point = None

        # 切换颜色或粗细时，下一次输入会从当前位置重新开一笔。
        self.should_restart_stroke = False

    def start_stroke(self, point):
        """开始一笔新的绘画。"""
        self.save_undo_state()
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

        # 点之间距离太近时不记录，减少手势抖动带来的锯齿。
        if self._distance(last_point, new_point) >= self.min_point_distance:
            self.current_stroke.add_point(new_point)

    def end_stroke(self):
        """结束当前这一笔。"""
        self.current_stroke = None
        self.smoothed_point = None
        self.should_restart_stroke = False

    def clear(self):
        """清空画布上的所有线条。"""
        if self.strokes:
            self.save_undo_state()
        self.strokes.clear()
        self.current_stroke = None
        self.smoothed_point = None
        self.should_restart_stroke = False

    def erase_at(self, point, radius=18):
        """在指定位置用圆形橡皮擦删除轨迹点。"""
        if point is None or not self.strokes:
            return False

        erase_point = self._clamp_point(point)
        new_strokes = []
        changed = False

        for stroke in self.strokes:
            current_segment = []

            for stroke_point in stroke.points:
                # 在橡皮范围内的点会被删除；范围外的点保留。
                if self._distance(stroke_point, erase_point) <= radius:
                    changed = True
                    self._append_segment(new_strokes, current_segment, stroke)
                    current_segment = []
                else:
                    current_segment.append(stroke_point)

            self._append_segment(new_strokes, current_segment, stroke)

        if changed:
            self.strokes = new_strokes
            self.current_stroke = None
            self.smoothed_point = None
            self.should_restart_stroke = False

        return changed

    def begin_erase_action(self):
        """开始一次连续擦除前记录撤销状态。"""
        if self.strokes:
            self.save_undo_state()

    def save_undo_state(self):
        """保存当前画布状态，供 Ctrl+Z 撤销。"""
        snapshot = [stroke.copy() for stroke in self.strokes]
        self.undo_stack.append(snapshot)
        if len(self.undo_stack) > self.max_undo_steps:
            self.undo_stack.pop(0)

    def undo(self):
        """撤销上一笔、上次擦除或清空。"""
        if not self.undo_stack:
            return False

        self.strokes = self.undo_stack.pop()
        self.current_stroke = None
        self.smoothed_point = None
        self.should_restart_stroke = False
        return True

    def set_brush_width(self, width):
        """设置画笔粗细，并限制在适合绘画的范围。"""
        new_width = max(2, min(32, int(width)))
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

    def _append_segment(self, strokes, points, source_stroke):
        """把擦除后剩余的一段轨迹重新保存成 stroke。"""
        if not points:
            return

        new_stroke = Stroke(source_stroke.color, source_stroke.width)
        for point in points:
            new_stroke.add_point(point)
        strokes.append(new_stroke)

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
        """把点限制在画布范围内，避免线条画到画布外。"""
        x = max(0, min(self.width - 1, point[0]))
        y = max(0, min(self.height - 1, point[1]))
        return (x, y)

    def _distance(self, point_a, point_b):
        """计算两个点之间的距离。"""
        return math.hypot(point_a[0] - point_b[0], point_a[1] - point_b[1])
