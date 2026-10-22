# -*- coding: utf-8 -*-
"""储钱罐页（主页）。"""

from kivy.animation import Animation
from kivy.app import App
from kivy.metrics import dp
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.relativelayout import RelativeLayout

from .. import theme
from ..storage import fmt_money, parse_amount, split_cash
from ..widgets.icons import GearIcon, RedoIcon, UndoIcon
from ..widgets.jar import JarView
from ..widgets.panel import (Chip, LineInput, PanelMixin, PillButton,
                             RoundCard)

CATEGORIES = ["饮食", "交通", "服饰", "娱乐", "学习", "医疗", "电子", "其他"]


def _lbl(text, size=None, color=theme.INK, height=None, halign="left"):
    l = Label(text=text, font_name="CN", font_size=size or theme.F_BODY,
              color=color, halign=halign, valign="middle")
    l.bind(size=lambda i, v: setattr(i, "text_size", (v[0], v[1])))
    if height:
        l.size_hint_y = None
        l.height = height
    return l


class JarScreen(RelativeLayout, PanelMixin):
    """RelativeLayout：子控件坐标相对本页，页面整体平移时内容跟着走。"""

    def __init__(self, store, **kw):
        super().__init__(**kw)
        self.store = store
        self._jar_h = theme.MIN_JAR_H
        self._prev_n = None
        self._panel = None
        self._baseline = theme.ACTION_ROW_H + dp(30)
        self._max_jar = dp(300)

        self.jar = JarView()
        self.add_widget(self.jar)

        self.gear = GearIcon(size_hint=(None, None))
        self.undo = UndoIcon(size_hint=(None, None))
        self.redo = RedoIcon(size_hint=(None, None))
        for ic in (self.gear, self.undo, self.redo):
            self.add_widget(ic)

        self.gear.bind(on_release=lambda *a: self.open_settings())
        self.undo.bind(on_release=lambda *a: self.do_undo())
        self.redo.bind(on_release=lambda *a: self.do_redo())
        # 点罐子：显示/隐藏余额
        self.jar.bind(on_release=lambda *a: self.jar.toggle_balance())

        self.btn_in = PillButton(text="存钱", size_hint=(None, None), font_size=theme.F_TITLE)
        self.btn_out = PillButton(text="花钱", size_hint=(None, None), font_size=theme.F_TITLE)
        self.btn_out.fill = (1.0, 1.0, 1.0, 1.0)
        self.btn_out.color = theme.INK
        self.btn_out.line_color = theme.INK_MID
        self.btn_out.line_width = dp(1.15)
        self.btn_in.bind(on_release=lambda *a: self.open_income())
        self.btn_out.bind(on_release=lambda *a: self.open_expense())
        self.add_widget(self.btn_in)
        self.add_widget(self.btn_out)

        self.bind(pos=self._relayout, size=self._relayout)
        self._relayout()
        self._sync_icons()

    # ------------------------------------------------------------ 布局
    def _relayout(self, *a):
        if self.width < 10 or self.height < 10:
            return
        self.jar.width = self.width * theme.BOTTLE_W_RATIO
        self.jar.x = self.center_x - self.jar.width / 2
        base = theme.ACTION_ROW_H + dp(40)
        self.jar.y = base
        self._baseline = base
        usable = max(dp(160), self.height - theme.TOPBAR_H - dp(10) - base)
        self._max_jar = max(theme.MIN_JAR_H, usable * theme.JAR_MAX_RATIO)
        if self.jar.height <= 1:
            self.jar.height = theme.MIN_JAR_H

        s = dp(30)
        self.gear.size = (s, s)
        self.gear.pos = (dp(20), self.height - dp(22) - s)
        self.redo.size = (s, s)
        self.redo.pos = (self.width - dp(20) - s, self.gear.y)
        self.undo.size = (s, s)
        self.undo.pos = (self.redo.x - dp(18) - s, self.gear.y)

        bw = (self.width - dp(20) * 2 - dp(14)) / 2
        bh = dp(50)
        by = dp(24)
        self.btn_in.size = (bw, bh)
        self.btn_in.pos = (dp(20), by)
        self.btn_out.size = (bw, bh)
        self.btn_out.pos = (dp(20) + bw + dp(14), by)

        self._apply_balance(animate=False)

    # ------------------------------------------------------------ 数据
    def _apply_balance(self, animate=True):
        bal = self.store.balance()
        cash = split_cash(bal) if bal > 0 else []
        self.jar.balance = bal
        self.jar.cash = cash

        n = len(cash)
        stack = n * theme.BILL_T
        desired = (stack / theme.FILL_TARGET) if n else theme.MIN_JAR_H
        desired = max(theme.MIN_JAR_H, min(desired, self._max_jar))
        if desired > self._jar_h:
            self._jar_h = desired
        target = min(self._jar_h, self._max_jar)

        if animate and abs(self.jar.height - target) > 0.5:
            Animation(height=target, d=0.40, t="out_cubic").start(self.jar)
        elif not animate:
            self.jar.height = target

        if animate and self._prev_n is not None and n > self._prev_n:
            self.jar.reveal = (self._prev_n / float(n)) if n else 1.0
            Animation(reveal=1.0, d=0.36, t="out_quad").start(self.jar)
        elif self._prev_n is None:
            self.jar.reveal = 1.0
        self._prev_n = n

        if self.jar.showing:
            self.jar.lbl.text = fmt_money(bal)

        self._sync_icons()

    def _sync_icons(self):
        self.undo.ink = theme.INK_MID if self.store.can_undo() else theme.INK_FAINT
        self.redo.ink = theme.INK_MID if self.store.can_redo() else theme.INK_FAINT

    def refresh(self):
        self._apply_balance(animate=True)
        app = App.get_running_app()
        if app and hasattr(app, "refresh_others"):
            app.refresh_others(self)

    def do_undo(self):
        if self.store.undo():
            self.refresh()

    def do_redo(self):
        if self.store.redo():
            self.refresh()

    # ------------------------------------------------------------ 面板
    def _panel_size(self, h):
        return (min(self.width * 0.88, dp(380)), h)

    def open_income(self):
        card = RoundCard(orientation="vertical", padding=[dp(24), dp(22)], spacing=dp(4))
        card.add_widget(_lbl("存 钱", theme.F_TITLE, height=dp(34)))
        amt = LineInput(hint="金额")
        amt.input_type = "number"
        amt.font_size = dp(28)
        amt.size_hint_y = None
        amt.height = dp(56)
        card.add_widget(amt)
        src = LineInput(hint="来源（自己写，比如：十月工资）")
        src.size_hint_y = None
        src.height = dp(52)
        card.add_widget(src)
        err = _lbl("", theme.F_SMALL, theme.DANGER, height=dp(20))
        card.add_widget(err)
        ok = PillButton(text="存 入", size_hint_y=None, height=dp(48))
        card.add_widget(ok)

        def submit(*a):
            cents = parse_amount(amt.text)
            if not cents:
                err.text = "请输入正确的金额"
                return
            self.store.add_tx("in", cents, src.text.strip() or "存入")
            self.close_panel()
            self.refresh()

        ok.bind(on_release=submit)
        self.open_panel(card, self._panel_size(dp(300)))

    def open_expense(self):
        card = RoundCard(orientation="vertical", padding=[dp(24), dp(22)], spacing=dp(4))
        card.add_widget(_lbl("花 钱", theme.F_TITLE, height=dp(34)))
        amt = LineInput(hint="金额")
        amt.input_type = "number"
        amt.font_size = dp(28)
        amt.size_hint_y = None
        amt.height = dp(56)
        card.add_widget(amt)
        card.add_widget(_lbl("花在哪", theme.F_SMALL, theme.INK_SOFT, height=dp(24)))

        grid = GridLayout(cols=3, spacing=dp(8), size_hint_y=None, height=dp(132))
        chips = []
        for i, name in enumerate(CATEGORIES):
            c = Chip(text=name)
            c.size_hint_y = None
            c.height = dp(38)
            c.bind(on_release=lambda inst: self._pick(chips, inst))
            chips.append(c)
            grid.add_widget(c)
        card.add_widget(grid)
        err = _lbl("", theme.F_SMALL, theme.DANGER, height=dp(18))
        card.add_widget(err)
        ok = PillButton(text="花 掉", size_hint_y=None, height=dp(46))
        card.add_widget(ok)

        def submit(*a):
            cents = parse_amount(amt.text)
            if not cents:
                err.text = "请输入正确的金额"
                return
            picked = [c.text for c in chips if c.selected]
            if not picked:
                err.text = "选一个分类"
                return
            if cents > self.store.balance():
                err.text = "罐子里没有这么多钱"
                return
            self.store.add_tx("out", cents, picked[0])
            self.close_panel()
            self.refresh()

        ok.bind(on_release=submit)
        self.open_panel(card, self._panel_size(dp(430)))

    @staticmethod
    def _pick(chips, target):
        for c in chips:
            c.selected = False
        target.selected = True

    def open_settings(self):
        from .settings import open_settings
        open_settings(self, self.store)
