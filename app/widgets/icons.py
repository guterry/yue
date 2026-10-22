# -*- coding: utf-8 -*-
"""线稿图标：用 canvas 画，不依赖字体里的符号（避免安卓上变成方框）。"""

import math

from kivy.graphics import Color, Ellipse, Line, Triangle
from kivy.metrics import dp
from kivy.properties import ColorProperty, NumericProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.widget import Widget

from .. import theme


class GearIcon(ButtonBehavior, Widget):
    """齿轮：设置入口。"""

    ink = ColorProperty(theme.INK_MID)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *a):
        self.canvas.clear()
        w, h = self.size
        if w < 4 or h < 4:
            return
        cx, cy = self.center
        r = min(w, h) * 0.30
        with self.canvas:
            Color(*self.ink)
            Line(circle=(cx, cy, r, 0, 360), width=1.6)
            Line(circle=(cx, cy, r * 0.46, 0, 360), width=1.6)
            for i in range(8):
                a = math.radians(i * 45)
                x1, y1 = cx + math.cos(a) * r * 0.86, cy + math.sin(a) * r * 0.86
                x2, y2 = cx + math.cos(a) * r * 1.28, cy + math.sin(a) * r * 1.28
                Line(points=[x1, y1, x2, y2], width=1.9, cap="round")


class UndoIcon(ButtonBehavior, Widget):
    """撤销：向左回转的箭头。"""

    ink = ColorProperty(theme.INK_MID)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *a):
        self.canvas.clear()
        w, h = self.size
        if w < 4 or h < 4:
            return
        cx, cy = self.center
        r = min(w, h) * 0.26
        with self.canvas:
            Color(*self.ink)
            Line(circle=(cx, cy, r, 35, 300), width=1.6)
            # 箭头
            ax = cx + math.cos(math.radians(35)) * r
            ay = cy + math.sin(math.radians(35)) * r
            s = min(w, h) * 0.13
            Line(points=[ax - s * 0.5, ay + s * 0.7, ax + s * 0.9, ay, ax - s * 0.5, ay - s * 0.7],
                 width=1.5, close=True)


class RedoIcon(UndoIcon):
    """重做：镜像的撤销箭头。"""

    def _draw(self, *a):
        self.canvas.clear()
        w, h = self.size
        if w < 4 or h < 4:
            return
        cx, cy = self.center
        r = min(w, h) * 0.26
        with self.canvas:
            Color(*self.ink)
            Line(circle=(cx, cy, r, -120, 145), width=1.6)
            ax = cx + math.cos(math.radians(145)) * r
            ay = cy + math.sin(math.radians(145)) * r
            s = min(w, h) * 0.13
            Line(points=[ax + s * 0.5, ay + s * 0.7, ax - s * 0.9, ay, ax + s * 0.5, ay - s * 0.7],
                 width=1.5, close=True)
