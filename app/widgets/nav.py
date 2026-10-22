# -*- coding: utf-8 -*-
"""底部三页签导航：选中时有滑动的指示器。"""

from kivy.animation import Animation
from kivy.graphics import Color, Line
from kivy.metrics import dp
from kivy.properties import BooleanProperty, NumericProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label

from .. import theme


class NavItem(ButtonBehavior, Label):
    active = BooleanProperty(False)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.font_name = "CN"
        self.font_size = theme.F_SMALL
        self.color = theme.INK_SOFT
        self.bind(active=self._on_active)

    def _on_active(self, *a):
        self.color = theme.INK if self.active else theme.INK_SOFT
        self.font_size = theme.F_SMALL


class NavBar(FloatLayout):
    ind_x = NumericProperty(0)

    def __init__(self, tabs, on_select, index=0, **kw):
        super().__init__(**kw)
        self.on_select = on_select
        self.items = []
        for i, text in enumerate(tabs):
            it = NavItem(text=text)
            it.bind(on_release=lambda inst, i=i: self.select(i))
            self.add_widget(it)
            self.items.append(it)

        with self.canvas.before:
            Color(*theme.LINE_SOFT)
            self._top = Line(points=[], width=1)

        with self.canvas.after:
            Color(*theme.INK)
            self._ind = Line(points=[], width=dp(1.8), cap="round")

        self.bind(pos=self._layout, size=self._layout, ind_x=self._draw_ind)
        self.select(index, animate=False)

    def _layout(self, *a):
        n = max(1, len(self.items))
        w = self.width / n
        for i, it in enumerate(self.items):
            it.size_hint = (None, None)
            it.size = (w, self.height)
            it.pos = (self.x + i * w, self.y)
        self._top.points = [self.x, self.top, self.right, self.top]
        self.ind_x = self._x_of(self._current())
        self._draw_ind()

    def _x_of(self, i):
        n = max(1, len(self.items))
        return self.x + (i + 0.5) * self.width / n

    def _current(self):
        for i, it in enumerate(self.items):
            if it.active:
                return i
        return 0

    def _draw_ind(self, *a):
        y = self.y + dp(11)
        half = dp(9)
        self._ind.points = [self.ind_x - half, y, self.ind_x + half, y]

    def select(self, i, animate=True):
        for j, it in enumerate(self.items):
            it.active = (j == i)
        if animate:
            Animation(ind_x=self._x_of(i), d=0.24, t="out_cubic").start(self)
        else:
            self.ind_x = self._x_of(i)
        if self.on_select:
            self.on_select(i)
