# -*- coding: utf-8 -*-
"""左滑列表行：左滑从右侧拉出一排按钮，点了才执行。"""

from kivy.animation import Animation
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import NumericProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.label import Label
from kivy.uix.relativelayout import RelativeLayout

from .. import theme


class ActionBtn(ButtonBehavior, Label):
    """展开后露出的操作按钮。"""

    def __init__(self, text, rgb, width, **kw):
        kw.setdefault("font_name", "CN")
        kw.setdefault("font_size", theme.F_SMALL)
        kw.setdefault("color", (1, 1, 1, 1))
        super().__init__(text=text, **kw)
        self.size_hint = (None, None)
        self.width = width
        self._rgb = rgb
        with self.canvas.before:
            self._c = Color(*rgb)
            self._r = RoundedRectangle(radius=[dp(11)])
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *a):
        pad = dp(4)
        self._r.pos = (self.x + pad * 0.5, self.y + pad)
        self._r.size = (self.width - pad, self.height - pad * 2)

    def on_press(self):
        self.opacity = 0.72

    def on_release(self):
        self.opacity = 1


class SwipeRow(RelativeLayout):
    """content 由外部给，必须是 RelativeLayout 并且用局部坐标。"""

    offset = NumericProperty(0)      # 内容左移了多少（正数）

    def __init__(self, actions, on_action, content, **kw):
        fixed = "size_hint" not in kw
        super().__init__(**kw)
        if fixed:
            self.size_hint = (None, None)
        self.actions = actions
        self.on_action = on_action
        self.aw = dp(72)
        self.content = content
        self.content.size_hint = (None, None)
        self.btns = []
        for key, text, rgb in reversed(actions):      # 从右往左排
            b = ActionBtn(text, rgb, self.aw)
            b._key = key
            b.bind(on_release=lambda w: self._fire(w._key))
            self.btns.append(b)
            self.add_widget(b)
        self.add_widget(self.content)                 # 内容盖在按钮上面
        self._dragging = False
        self._open = False
        self.bind(pos=self._relayout, size=self._relayout)
        self.bind(offset=self._sync_offset)

    # ------------------------------------------------------------ 布局
    def _relayout(self, *a):
        w, h = self.size
        if w < 10:
            return
        self.content.size = (w, h)
        self.content.pos = (-self.offset, 0)
        n = len(self.btns)
        for i, b in enumerate(self.btns):
            b.size = (self.aw, h)
            b.pos = (w - self.aw * (i + 1), 0)

    def _sync_offset(self, *a):
        self.content.x = -self.offset

    def _snap(self, open_):
        self._open = open_
        target = self.aw * len(self.btns) if open_ else 0
        Animation(offset=target, d=0.18, t="out_quad").start(self)

    # ------------------------------------------------------------ 触摸
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if self._open and touch.pos[0] < self.x + self.width - self.aw * len(self.btns):
                # 打开状态下点空白处 → 收起
                self._snap(False)
            self._touch = touch
            self._grab = False
            self._start = touch.pos
            self._base = self.offset
            # 交给按钮/内容自己处理（返回 False 让事件继续往下派发）
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if getattr(self, "_touch", None) is not touch:
            return super().on_touch_move(touch)
        dx = touch.pos[0] - self._start[0]
        dy = touch.pos[1] - self._start[1]
        if not self._grab and abs(dx) > dp(10) and abs(dx) > abs(dy) * 1.5:
            self._grab = True
            self._dragging = True
            touch.grab(self)
        if self._grab:
            total = self.aw * len(self.btns)
            self.offset = max(0.0, min(total, self._base - dx))
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if getattr(self, "_touch", None) is not touch:
            return super().on_touch_up(touch)
        if self._grab:
            touch.ungrab(self)
            self._grab = False
            self._dragging = False
            total = self.aw * len(self.btns)
            self._snap(self.offset > total * 0.45)
            return True
        return super().on_touch_up(touch)

    def _fire(self, key):
        self._snap(False)
        if self.on_action:
            self.on_action(key, self)


# ---------------------------------------------------------------- 行内容

class RowContent(RelativeLayout):
    """列表行内容基类：不透明底色（挡住背后的操作按钮）+ 底部一条极淡分隔线。"""

    def __init__(self, bg=None, **kw):
        super().__init__(**kw)
        self.size_hint = (None, None)
        with self.canvas.before:
            Color(*(bg or theme.BG))
            self._fill = Rectangle()
        with self.canvas:
            self._sep_c = Color(*theme.LINE_SOFT)
            from kivy.graphics import Line
            self._sep = Line(points=[], width=1)
        self.bind(size=self._sync_sep, pos=self._sync_sep)

    def _sync_sep(self, *a):
        w, h = self.size
        self._fill.pos = (0, 0)
        self._fill.size = (w, h)
        self._sep.points = [0, 0.5, w, 0.5]

    def hide_sep(self):
        self._sep_c.a = 0


def lite_label(text, size=None, color=theme.INK, halign="left"):
    l = Label(text=text, font_name="CN", font_size=size or theme.F_BODY,
              color=color, halign=halign, valign="middle", markup=False)
    l.size_hint = (None, None)
    l.bind(size=lambda i, v: setattr(i, "text_size", v))
    return l
