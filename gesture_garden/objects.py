"""花园对象模块。

当前阶段先保留基础文件，后续可在这里定义花朵、叶子、粒子等类。
"""


class GardenObject:
    """花园对象的基础占位类。"""

    def __init__(self, x=0, y=0):
        # 保存对象位置
        self.x = x
        self.y = y

    def update(self):
        """更新对象状态。"""
        pass

    def draw(self, screen):
        """绘制对象。"""
        pass
