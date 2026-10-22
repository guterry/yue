# -*- coding: utf-8 -*-
"""通用 UI 零件：圆角卡片、中心弹出面板、按钮、输入框、分类标签。"""

from kivy.animation import Animation
from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import BooleanProperty, ColorProperty, ListProperty, NumericProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from .. import theme


def mk_label(text, size=None, color=theme.INK, halign="left", valign="middle",
             bold=False, markup=False):
    """固定尺寸 + 可对齐的 Label（text_size 跟随 size）。"""
    l = Label(text=text, font_name="CN", font_size=size or theme.F_BODY,
              color=color, halign=halign, valign=valign, markup=markup)
    l.size_hint = (None, None)
    l.bind(size=lambda i, v: setattr(i, "text_size", v))
    return l


def flabel(text, size=None, color=theme.INK, halign="left", height=None,
           valign="middle"):
    """放进 BoxLayout 用的一行文字：横向拉伸、高度固定。"""
    fs = size or theme.F_BODY
    l = Label(text=text, font_name="CN", font_size=fs, color=color,
              halign=halign, valign=valign)
    l.size_hint = (1, None)
    l.height = height if height is not None else fs + dp(8)
    l.bind(size=lambda i, v: setattr(i, "text_size", v))
    return l


class Card(RelativeLayout):
    """手动布局用的圆角卡片（背景画在自己身上，坐标是局部值）。"""

    def __init__(self, radius=None, fill=None, **kw):
        super().__init__(**kw)
        self.size_hint = (None, None)
        self.radius = radius or theme.R_CARD
        with self.canvas.before:
            self._cc = Color(*(fill or theme.CARD))
            self._rr = RoundedRectangle(radius=[self.radius])
        self.bind(size=self._sync_card)
        self._sync_card()

    def _sync_card(self, *a):
        self._rr.pos = (0, 0)
        self._rr.size = self.size

    def set_fill(self, rgba):
        self._cc.rgba = rgba


class RoundCard(BoxLayout):
    radius_px = NumericProperty(dp(20))
    fill = ColorProperty(theme.CARD)

    def __init__(self, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            self._c = Color(*self.fill)
            self._r = RoundedRectangle(radius=[self.radius_px])
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *a):
        self._r.pos = self.pos
        self._r.size = self.size


class PillButton(ButtonBehavior, Label):
    fill = ColorProperty(theme.INK)
    line_color = ColorProperty((0, 0, 0, 0))
    radius_px = NumericProperty(dp(14))
    line_width = NumericProperty(dp(1.2))

    def __init__(self, **kw):
        super().__init__(**kw)
        self.font_name = "CN"
        self.color = (1, 1, 1, 1)
        with self.canvas.before:
            self._c = Color(*self.fill)
            self._r = RoundedRectangle(radius=[self.radius_px])
            self._lc = Color(*self.line_color)
            self._l = Line(rounded_rectangle=(0, 0, 0, 0, self.radius_px),
                           width=self.line_width)
        self.bind(pos=self._sync, size=self._sync,
                  fill=self._sync_fill, line_color=self._sync_line)

    def _sync(self, *a):
        self._r.pos = self.pos
        self._r.size = self.size
        self._l.rounded_rectangle = (self.x, self.y, self.width, self.height, self.radius_px)

    def _sync_fill(self, *a):
        self._c.rgba = self.fill

    def _sync_line(self, *a):
        self._lc.rgba = self.line_color

    def on_press(self):
        self.opacity = 0.72

    def on_release(self):
        self.opacity = 1


class LineInput(TextInput):
    """无边框、只有一条下划线的输入框。"""

    def __init__(self, hint="", **kw):
        kw.setdefault("multiline", False)
        kw.setdefault("write_tab", False)
        super().__init__(**kw)
        self.font_name = "CN"
        self.font_size = theme.F_TITLE
        self.background_normal = ""
        self.background_active = ""
        self.background_color = (0, 0, 0, 0)
        self.foreground_color = theme.INK
        self.cursor_color = theme.INK
        self.cursor_width = dp(1.4)
        self.hint_text = hint
        self.hint_text_color = (*theme.INK_SOFT[:3], 1)
        self.padding = [0, dp(8), 0, dp(8)]
        with self.canvas.after:
            Color(*theme.LINE)
            self._line = Line(points=[], width=1.2)
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *a):
        self._line.points = [self.x, self.y, self.right, self.y]


class RoundInput(TextInput):
    """圆角灰底输入框（仿微信底部输入栏）。"""

    def __init__(self, hint="", **kw):
        kw.setdefault("multiline", False)
        kw.setdefault("write_tab", False)
        super().__init__(**kw)
        self.size_hint = (None, None)     # 尺寸由外部给定，别被父容器拉伸
        self.font_name = "CN"
        self.font_size = theme.F_BODY
        self.background_normal = ""
        self.background_active = ""
        self.background_color = (0, 0, 0, 0)
        self.foreground_color = theme.INK
        self.cursor_color = theme.INK
        self.cursor_width = dp(1.4)
        self.hint_text = hint
        self.hint_text_color = (*theme.INK_SOFT[:3], 1)
        self.padding = [dp(12), dp(9), dp(12), dp(9)]
        with self.canvas.before:
            self._c = Color(*theme.FIELD_BG)
            self._r = RoundedRectangle(radius=[dp(15)])
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *a):
        self._r.pos = self.pos
        self._r.size = self.size


class CirclePlus(ButtonBehavior, Widget):
    """圆形加号按钮。"""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *a):
        self.canvas.clear()
        w, h = self.size
        if w < 6 or h < 6:
            return
        cx, cy = self.center          # Widget 的 canvas 用父坐标
        r = min(w, h) / 2.0
        s = r * 0.34
        with self.canvas:
            Color(*theme.ACCENT[:3], 1)
            Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))
            Color(1, 1, 1, 1)
            Line(points=[cx - s, cy, cx + s, cy], width=1.7, cap="round")
            Line(points=[cx, cy - s, cx, cy + s], width=1.7, cap="round")

    def on_press(self):
        self.opacity = 0.75

    def on_release(self):
        self.opacity = 1


class Chip(ButtonBehavior, Label):
    selected = BooleanProperty(False)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.font_name = "CN"
        self.font_size = theme.F_BODY
        self.color = theme.INK_MID
        with self.canvas.before:
            self._c = Color(1, 1, 1, 0)
            self._r = RoundedRectangle(radius=[dp(12)])
            self._lc = Color(*theme.LINE)
            self._l = Line(rounded_rectangle=(0, 0, 0, 0, dp(12)), width=1)
        self.bind(pos=self._sync, size=self._sync, selected=self._sync_sel)

    def _sync(self, *a):
        self._r.pos = self.pos
        self._r.size = self.size
        self._l.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(12))

    def _sync_sel(self, *a):
        if self.selected:
            self._c.rgba = (*theme.ACCENT[:3], 1)
            self._lc.rgba = (*theme.ACCENT[:3], 1)
            self.color = (1, 1, 1, 1)
        else:
            self._c.rgba = (1, 1, 1, 0)
            self._lc.rgba = theme.LINE
            self.color = theme.INK_MID


class CenterPanel(RelativeLayout):
    """从页面中心向外弹出的二级面板。座标一律用局部值（相对本面板）。"""

    def __init__(self, card, **kw):
        super().__init__(**kw)
        self.card = card
        card.size_hint = (None, None)
        self.add_widget(card)
        with self.canvas.before:
            self._c = Color(*theme.MASK, 0.30)
            self._bg = Rectangle()
        self.bind(pos=self._sync_bg, size=self._sync_bg)
        self.opacity = 0
        self.card.opacity = 0

    def _sync_bg(self, *a):
        self._bg.pos = (0, 0)       # 局部坐标：铺满本面板
        self._bg.size = self.size

    # ------------------------------------------------------------
    def show(self, target_size):
        """target_size: (w, h)，卡片最终尺寸。"""
        w, h = target_size
        cx, cy = self.width / 2.0, self.height / 2.0
        self.card.size = (w * 0.86, h * 0.86)
        self.card.center = (cx, cy)
        self.card.opacity = 0
        self.opacity = 0
        Animation(opacity=1, d=0.14).start(self)
        Animation(opacity=1, d=0.16).start(self.card)
        Animation(size=(w, h), pos=(cx - w / 2, cy - h / 2),
                  d=0.26, t="out_back").start(self.card)

    def hide(self, on_done=None):
        Animation(opacity=0, d=0.12).start(self)
        anim = Animation(opacity=0, d=0.10)
        if on_done:
            anim.bind(on_complete=lambda *a: on_done())
        anim.start(self.card)

    def on_touch_down(self, touch):
        # 点遮罩关闭（本面板 pos 恒为 (0,0)，所以父空间 == 本空间）
        if self.collide_point(*touch.pos) and not self.card.collide_point(*touch.pos):
            if self.card.opacity > 0.9:
                self.hide()
            return True
        return super().on_touch_down(touch)


# ---------------------------------------------------------------- 小部件

class Pill(ButtonBehavior, RelativeLayout):
    """小胶囊：左边文字，右边一个手画的下箭头。"""

    def __init__(self, text="", **kw):
        super().__init__(**kw)
        self.size_hint = (None, None)
        self.lbl = mk_label(text, theme.F_SMALL, theme.INK_MID, halign="left")
        self.add_widget(self.lbl)
        with self.canvas.before:
            self._c = Color(*theme.PILL_BG)
            self._bg = RoundedRectangle(radius=[dp(13)])
            self._lc = Color(*theme.LINE)
            self._ln = Line(rounded_rectangle=(0, 0, 0, 0, dp(13)), width=1)
        with self.canvas.after:
            self._ac = Color(*theme.INK_SOFT)
            self._arrow = Line(points=[], width=1.3)
        self.bind(size=self._sync, pos=self._sync)
        self._sync()

    def _sync(self, *a):
        w, h = self.size
        self._bg.pos = (0, 0)
        self._bg.size = (w, h)
        self._ln.rounded_rectangle = (0.5, 0.5, w - 1, h - 1, dp(13))
        ax, cy = w - dp(13), h / 2.0
        self._arrow.points = [ax - dp(3.4), cy + dp(1.8),
                              ax, cy - dp(1.6),
                              ax + dp(3.4), cy + dp(1.8)]
        self.lbl.size = (w - dp(30), h)
        self.lbl.pos = (dp(13), 0)

    def set_text(self, text):
        self.lbl.text = text

    def on_press(self):
        self.opacity = 0.75

    def on_release(self):
        self.opacity = 1


class _OptRow(ButtonBehavior, Label):
    def __init__(self, text, active=False, **kw):
        super().__init__(text=text, font_name="CN", font_size=theme.F_BODY,
                         color=(theme.ACCENT if active else theme.INK),
                         halign="left", valign="middle", **kw)
        self.size_hint = (None, None)
        with self.canvas:
            self._lc = Color(*theme.LINE_SOFT)
            self._ln = Line(points=[], width=1)
        self.bind(size=self._sync)
        self._sync()

    def _sync(self, *a):
        w, _h = self.size
        self.text_size = self.size
        self._ln.points = [0, 0.5, w, 0.5]

    def on_press(self):
        self.opacity = 0.6

    def on_release(self):
        self.opacity = 1


class OptionList(RelativeLayout):
    """面板里的一列可选项。"""

    def __init__(self, options, current=None, on_pick=None, row_h=None, **kw):
        super().__init__(**kw)
        self.size_hint = (None, None)
        self.row_h = row_h or dp(46)
        self.options = list(options)
        self.on_pick = on_pick
        self.rows = []
        for text in self.options:
            r = _OptRow(text, active=(text == current))
            r.bind(on_release=lambda w: self._pick(w.text))
            self.rows.append(r)
            self.add_widget(r)
        self.bind(size=self._relayout)

    def _relayout(self, *a):
        w, h = self.size
        for i, r in enumerate(self.rows):
            r.size = (w, self.row_h)
            r.pos = (0, h - self.row_h * (i + 1))

    def _pick(self, text):
        if self.on_pick:
            self.on_pick(text)


class PanelMixin:
    """给页面加「中心弹出面板」能力。"""

    def open_panel(self, card, size):
        if getattr(self, "_panel", None):
            return None
        p = CenterPanel(card)
        p.size = self.size
        p.pos = (0, 0)
        self.add_widget(p)
        self._panel = p
        p.show(size)
        return p

    def close_panel(self):
        p = getattr(self, "_panel", None)
        if not p:
            return
        self._panel = None
        p.hide(lambda: self.remove_widget(p))

    def swap_panel(self, card, size):
        """把当前面板换成另一个（先收起再弹出）。"""
        from kivy.clock import Clock
        self.close_panel()
        Clock.schedule_once(lambda dt: self.open_panel(card, size), 0.17)

    def pick_one(self, title, options, current, on_pick):
        """弹一个选项列表。"""
        n = max(1, len(options))
        row_h = dp(46)
        w = min(self.width * 0.80, dp(320))
        h = dp(46) + n * row_h + dp(8)
        card = Card()
        card.size = (w, h)
        t = mk_label(title, theme.F_SMALL, theme.INK_SOFT, halign="left")
        t.size = (w - dp(28), dp(18))
        t.pos = (dp(16), h - dp(28))
        card.add_widget(t)
        ol = OptionList(options, current, lambda v: (self.close_panel(), on_pick(v)))
        ol.size = (w - dp(16), n * row_h)
        ol.pos = (dp(8), dp(6))
        ol._relayout()
        card.add_widget(ol)
        self.open_panel(card, (w, h))


def note_panel(host, title, text, on_save, hint="写点什么"):
    """通用的「写一行备注」面板。host 需实现 open_panel/close_panel。"""
    w = min(host.width * 0.86, dp(360))
    h = dp(196)
    card = Card()
    box = BoxLayout(orientation="vertical", size_hint=(1, 1),
                    padding=[dp(24), dp(22)], spacing=dp(10))
    card.add_widget(box)
    box.add_widget(mk_label(title, theme.F_TITLE, theme.INK, valign="bottom"))
    inp = LineInput(hint=hint)
    inp.text = text or ""
    inp.size_hint_y = None
    inp.height = dp(46)
    box.add_widget(inp)
    ok = PillButton(text="保 存", font_size=theme.F_BODY, size_hint_y=None, height=dp(44))
    box.add_widget(ok)

    def save(*a):
        on_save(inp.text.strip())
        host.close_panel()

    ok.bind(on_release=save)
    host.open_panel(card, (w, h))
    return card


class Toast(RelativeLayout):
    """底部浮出来的一句话，1.6 秒后自己走。"""

    def __init__(self, text, **kw):
        super().__init__(**kw)
        self.size_hint = (None, None)
        self.lbl = mk_label(text, theme.F_SMALL, (1, 1, 1, 1), halign="center")
        self.add_widget(self.lbl)
        with self.canvas.before:
            self._c = Color(*theme.TOAST_BG)
            self._r = RoundedRectangle(radius=[dp(18)])
        self.bind(size=self._sync)
        self.opacity = 0

    def _sync(self, *a):
        w, h = self.size
        self._r.pos = (0, 0)
        self._r.size = (w, h)
        self.lbl.size = (w, h)
        self.lbl.pos = (0, 0)


def toast(host, text):
    """在 host（页面）底部弹一句话。"""
    from kivy.clock import Clock
    t = Toast(text)
    tw = min(host.width * 0.7, dp(300))
    t.size = (tw, dp(38))
    t.pos = ((host.width - tw) / 2.0, dp(100))
    host.add_widget(t)
    Animation(opacity=1, d=0.12).start(t)
    Clock.schedule_once(lambda dt: Animation(opacity=0, d=0.25).start(t), 1.5)
    Clock.schedule_once(lambda dt: host.remove_widget(t), 1.9)
