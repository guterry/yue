# -*- coding: utf-8 -*-
"""玻璃罐视图：正视图，罐内宽度等于一张纸币的长度。

纸币平躺堆叠，微微下弯，层与层之间留一道缝——侧面看就是一条条横线。
罐身是玻璃：有厚度、有高光、有落地投影，钱是"透过玻璃"看到的。
"""

import math

from kivy.animation import Animation
from kivy.graphics import Color, Line, Rectangle
from kivy.metrics import dp
from kivy.properties import BooleanProperty, ListProperty, NumericProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.label import Label
from kivy.uix.relativelayout import RelativeLayout

from .. import theme
from ..storage import fmt_money
from . import glass
from .art import art

MAX_DRAW = 160          # 最多画这么多张，再多就压成一块（防卡）


class JarView(ButtonBehavior, RelativeLayout):
    cash = ListProperty([])            # [(kind, denom), ...] 从下往上
    reveal = NumericProperty(1.0)      # 0-1，用于入场动画
    showing = BooleanProperty(False)   # 是否显示余额
    balance = NumericProperty(0)       # 分

    def __init__(self, **kw):
        super().__init__(**kw)
        self.size_hint = (None, None)
        self._art = art(self)          # 私有画布：只清这一块，不会误伤子控件
        self.lbl = Label(
            text="",
            font_name="CN",
            font_size=theme.F_HUGE,
            color=theme.INK,
            opacity=0,
            halign="center",
            valign="middle",
        )
        self.add_widget(self.lbl)
        self.bind(pos=self._redraw, size=self._redraw,
                  cash=self._redraw, reveal=self._redraw)
        self.bind(pos=self._layout_lbl, size=self._layout_lbl)

    # ------------------------------------------------------------ 布局
    def _layout_lbl(self, *args):
        # 余额数字浮在罐口正上方，不压在钱堆上（罐内下半部永远是钱）
        self.lbl.size = (self.width, dp(52))
        self.lbl.pos = (0, self.height + dp(6))   # RelativeLayout：局部坐标
        self.lbl.text_size = self.lbl.size

    # ------------------------------------------------------------ 绘制
    def _redraw(self, *args):
        # canvas.before.clear() 在 Kivy 2.3.1 里会崩；canvas.clear() 又会摘掉
        # 余额数字的 canvas。所以只清自己那块私有画布。
        self._art.clear()
        w, h = self.size
        if w <= 2 or h <= 2:
            return

        W = w
        ew = min(dp(26), h * 0.11, w * 0.15)     # 罐底/罐口那道椭圆的高度

        with self._art:
            glass.shadow(W, ew)                  # 1. 落地投影
            glass.table(W, ew)                   # 2. 桌面
            glass.bottom(W, ew)                  # 3. 罐底
            yb, yt = self._draw_cash(W, h, ew)   # 4. 钱（在玻璃后面）
            glass.vignette(W, h, ew, yb, yt)     # 5. 罐壁投在钱上的暗部
            glass.body(W, h, ew)                 # 6. 罐身玻璃 + 高光
            glass.mouth(W, h, ew)                # 7. 罐口

    # ------------------------------------------------------------ 钱
    def _slab(self, x, w, y, th):
        """画一层纸：分几段画，中间微微下垂，才不像一块板。"""
        if th <= 0 or w <= 0:
            return
        seg = 5
        sw = w / float(seg)
        sag = dp(2.2)
        for s in range(seg):
            k = (s + 0.5) / float(seg)
            Rectangle(pos=(x + sw * s, y + sag * math.sin(math.pi * k)),
                      size=(sw + 0.7, th))

    def _draw_cash(self, W, h, ew):
        """返回 (钱堆底 y, 钱堆顶 y)。"""
        n = len(self.cash)
        base_y = ew * 0.38
        if n == 0:
            # 空罐：底部画一排很淡的短虚线，表示"等着第一笔"
            Color(*theme.INK_SOFT[:3], 0.42)
            y = base_y + dp(20)
            x = W * 0.18
            while x < W * 0.82:
                Line(points=[x, y, x + dp(7), y], width=1.0)
                x += dp(15)
            return base_y, base_y + dp(26)

        total_t = sum(theme.BILL_T if k == "bill" else theme.COIN_T
                      for k, _ in self.cash)
        max_stack = max(dp(1), h * theme.FILL_MAX)
        scale = min(1.0, max_stack / total_t) if total_t > 0 else 1.0

        visible = int(math.ceil(n * max(0.0, min(1.0, self.reveal))))
        visible = min(visible, n, MAX_DRAW)
        y = base_y
        cx = W / 2.0
        lim = h - ew * 0.78

        for i in range(visible):
            kind, denom = self.cash[i]
            t = (theme.BILL_T if kind == "bill" else theme.COIN_T) * scale
            if y + t > lim:
                break
            rgb = theme.BILL_COLOR.get(denom, (0.5, 0.5, 0.5)) \
                if kind == "bill" else theme.COIN_COLOR.get(denom, (0.7, 0.7, 0.7))
            # 层与层之间的明度差：堆起来才有纸的层次
            shade = 1.0 + (0.14 if i % 3 == 0 else (-0.10 if i % 3 == 1 else 0.02))
            r = min(1.0, rgb[0] * shade)
            g = min(1.0, rgb[1] * shade)
            b = min(1.0, rgb[2] * shade)

            if kind == "bill":
                mm = theme.BILL_LEN.get(denom, 155)
                bw = W * (mm / 155.0) * 0.90
                # 每张纸左右各错开一点点，堆起来才不是一根齐整的柱子
                jx = (-0.9 if i % 2 else 0.9) * dp(1) * (0.6 + 0.4 * (i % 3))
                x = cx - bw / 2.0 + jx
                th = max(dp(1), t * theme.BILL_GAP)
                Color(r, g, b, 1)
                self._slab(x, bw, y, th)
                # 纸的裁切边会反一道亮光——这条亮线就是"一张纸"的辨识点
                Color(min(1, r * 1.30 + 0.16), min(1, g * 1.30 + 0.16),
                      min(1, b * 1.30 + 0.16), 0.90)
                self._slab(x, bw, y + th - dp(1), dp(1))
            else:
                cw = min(dp(18), W * 0.062)
                th = max(dp(1), t * 0.62)
                Color(r, g, b, 1)
                self._slab(cx - cw / 2.0, cw, y, th)
                Color(min(1, r * 1.28 + 0.16), min(1, g * 1.28 + 0.16),
                      min(1, b * 1.28 + 0.16), 0.9)
                self._slab(cx - cw / 2.0, cw, y + th - dp(1), dp(1))
            y += t

        return base_y, y

    # ------------------------------------------------------------ 交互
    def toggle_balance(self):
        self.showing = not self.showing
        if self.showing:
            self.lbl.text = fmt_money(self.balance)
            Animation(opacity=1, d=0.16).start(self.lbl)
        else:
            Animation(opacity=0, d=0.12).start(self.lbl)

    def flash(self):
        """新钱落下时，罐身轻微一亮。"""
        self.opacity = 0.72
        Animation(opacity=1, d=0.22, t="out_quad").start(self)
