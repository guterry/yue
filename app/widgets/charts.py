# -*- coding: utf-8 -*-
"""饼图 / 折线图，纯 canvas 手绘，不引第三方库。

约定：本文件里的控件都是 RelativeLayout，绘制一律用局部坐标（0 到 width/height）。
"""

import math

from kivy.graphics import Color, Ellipse, Line, Mesh
from kivy.metrics import dp
from kivy.properties import ColorProperty, ListProperty, NumericProperty
from kivy.uix.label import Label
from kivy.uix.relativelayout import RelativeLayout

from .. import theme
from .art import art


class PieChart(RelativeLayout):
    """甜甜圈饼图。data = [(标签, 数值, (r,g,b)), ...]"""

    data = ListProperty([])
    hole_color = ColorProperty((1, 1, 1, 1))
    hole_ratio = NumericProperty(0.56)
    empty_color = ColorProperty((0.90, 0.895, 0.885, 1))

    def __init__(self, **kw):
        super().__init__(**kw)
        self.size_hint = (None, None)
        self._art = art(self)
        self.bind(size=self._redraw, pos=self._redraw, data=self._redraw)

    def _redraw(self, *a):
        self._art.clear()
        w, h = self.size
        if w < 8 or h < 8:
            return
        r = min(w, h) / 2.0 - dp(2)
        cx, cy = w / 2.0, h / 2.0
        total = sum(max(0.0, v) for _, v, _ in self.data)

        if total <= 0:
            with self._art:
                Color(*self.empty_color)
                Line(circle=(cx, cy, r), width=dp(1.2))
            return

        ang = math.pi / 2.0          # 从 12 点方向开始，顺时针
        for _label, v, rgb in self.data:
            if v <= 0:
                continue
            sweep = -2 * math.pi * (v / total)
            seg = max(2, int(abs(sweep) / (math.pi / 18)) + 1)
            verts, idx = [], []
            for k in range(seg):
                a1 = ang + sweep * k / seg
                a2 = ang + sweep * (k + 1) / seg
                verts += [cx, cy, 0, 0,
                          cx + r * math.cos(a1), cy + r * math.sin(a1), 0, 0,
                          cx + r * math.cos(a2), cy + r * math.sin(a2), 0, 0]
            idx = list(range(len(verts) // 4))
            with self._art:
                Color(rgb[0], rgb[1], rgb[2], 1)
                Mesh(vertices=verts, indices=idx, mode="triangles")
            ang += sweep

        # 挖掉中间，做成甜甜圈，颜色和卡片一致
        hr = r * self.hole_ratio
        with self._art:
            Color(*self.hole_color)
            Ellipse(pos=(cx - hr, cy - hr), size=(hr * 2, hr * 2))


class LegendList(RelativeLayout):
    """饼图右侧图例：一行一个「圆点 + 名称 + 百分比」。"""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.size_hint = (None, None)
        self._rows = []
        self._art = art(self)          # 私有画布：本控件有 Label 子控件，不能用 canvas.clear()
        self.bind(size=self._relayout)

    def set_items(self, items):
        self.clear_widgets()
        self._rows = []
        self._art.clear()
        for name, pct, rgb in items:
            a = Label(text=name, font_name="CN", font_size=theme.F_SMALL,
                      color=theme.INK_MID, halign="left", valign="middle")
            b = Label(text=pct, font_name="CN", font_size=theme.F_SMALL,
                      color=theme.INK_SOFT, halign="right", valign="middle")
            for l in (a, b):
                l.size_hint = (None, None)
                l.bind(size=lambda i, v: setattr(i, "text_size", v))
            self.add_widget(a)
            self.add_widget(b)
            self._rows.append((a, b, rgb))
        self._relayout()

    def _relayout(self, *a):
        w, h = self.size
        if w < 10:
            return
        self._art.clear()
        n = len(self._rows)
        if not n:
            return
        rh = min(dp(28), h / float(n))
        for i, (lab, pct, rgb) in enumerate(self._rows):
            y = h - rh * (i + 1)
            lab.size = (w - dp(52), rh)
            lab.pos = (dp(14), y)
            pct.size = (dp(46), rh)
            pct.pos = (w - dp(46), y)
            with self._art:
                Color(*rgb)
                Ellipse(pos=(dp(2.4), y + rh / 2.0 - dp(3.2)), size=(dp(6.4), dp(6.4)))


class LineChart(RelativeLayout):
    """极简折线：values 按时间先后，点少时也能看。"""

    values = ListProperty([])
    labels = ListProperty([])
    line_color = ColorProperty(theme.ACCENT)
    dots = NumericProperty(1)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.size_hint = (None, None)
        self._art = art(self)
        self.bind(size=self._redraw, pos=self._redraw,
                  values=self._redraw, labels=self._redraw)

    def _redraw(self, *a):
        self._art.clear()
        w, h = self.size
        if w < 10 or h < 10:
            return
        pad_x = dp(8)
        pad_y = dp(10)
        vals = [max(0.0, float(v)) for v in self.values]
        if not vals:
            return
        vmax = max(vals) or 1.0
        n = len(vals)
        with self._art:
            # 底部的两道浅网格
            Color(*theme.LINE)
            Line(points=[pad_x, pad_y, w - pad_x, pad_y], width=1)
            Color(*theme.LINE_SOFT)
            Line(points=[pad_x, h / 2.0, w - pad_x, h / 2.0], width=1)

        pts = []
        if n == 1:
            pts = [(pad_x, pad_y), (w - pad_x, pad_y)]
        else:
            step = (w - pad_x * 2) / float(n - 1)
            for i, v in enumerate(vals):
                pts += [pad_x + step * i, pad_y + (h - pad_y * 2) * (v / vmax)]

        with self._art:
            Color(*self.line_color[:3], 1)
            if len(pts) >= 4:
                Line(points=pts, width=dp(1.6), joint="round")
            if self.dots:
                for i in range(0, len(pts), 2):
                    Color(*self.line_color[:3], 1)
                    Ellipse(pos=(pts[i] - dp(2.2), pts[i + 1] - dp(2.2)),
                            size=(dp(4.4), dp(4.4)))
