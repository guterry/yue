# -*- coding: utf-8 -*-
"""「我想要的」页：总额 + 排序 + 备忘列表 + 底部输入栏。"""

from kivy.animation import Animation
from kivy.app import App
from kivy.graphics import Color, Line, Rectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.scrollview import ScrollView

from .. import theme
from ..storage import fmt_money, fmt_ts, parse_amount
from ..widgets.icons import RedoIcon, UndoIcon
from ..widgets.panel import (CirclePlus, PanelMixin, Pill, RoundInput,
                             mk_label, note_panel, toast)
from ..widgets.swipe import RowContent, SwipeRow, lite_label


class WishRow(RowContent):
    """一条心愿。左滑出「备注 / 买下 / 删除」。"""

    def __init__(self, wish, **kw):
        super().__init__(**kw)
        self.wish = wish
        self.t1 = lite_label(wish["content"], theme.F_BODY, theme.INK)
        self.t2 = lite_label(wish["note"] or fmt_ts(wish["ts"]),
                             theme.F_SMALL, theme.INK_SOFT)
        self.t3 = lite_label("¥" + fmt_money(wish["price"]),
                             theme.F_BODY, theme.INK_MID, halign="right")
        for l in (self.t1, self.t2, self.t3):
            self.add_widget(l)
        self.bind(size=self._lay)
        self._lay()

    def _lay(self, *a):
        w, h = self.size
        self.t1.size = (w - dp(40) - dp(104), dp(21))
        self.t1.pos = (dp(20), h / 2.0 + dp(1))
        self.t2.size = (w - dp(40) - dp(104), dp(18))
        self.t2.pos = (dp(20), h / 2.0 - dp(20))
        self.t3.size = (dp(96), h)
        self.t3.pos = (w - dp(20) - dp(96), 0)


class WishScreen(RelativeLayout, PanelMixin):
    SORTS = ["按时间", "按价钱"]

    def __init__(self, store, **kw):
        self.store = store
        self._panel = None
        self._sort = "time"
        super().__init__(**kw)

        self.title = mk_label("我想要的", theme.F_TITLE, theme.INK)
        self.cap = mk_label("一共想要", theme.F_SMALL, theme.INK_SOFT)
        self.total = mk_label("¥0", theme.F_BIG, theme.INK)
        self.pill = Pill()
        self.pill.bind(on_release=lambda *a: self._pick_sort())

        # 右上：撤销 / 重做
        self.undo = UndoIcon(size_hint=(None, None))
        self.redo = RedoIcon(size_hint=(None, None))
        for ic in (self.undo, self.redo):
            self.add_widget(ic)
        self.undo.bind(on_release=lambda *a: self.do_undo())
        self.redo.bind(on_release=lambda *a: self.do_redo())

        self.scroll = ScrollView(do_scroll_x=False, do_scroll_y=True,
                                 bar_width=dp(2), scroll_type=["bars", "content"])
        self.scroll.size_hint = (None, None)
        self.list = BoxLayout(orientation="vertical", size_hint=(1, None), spacing=0)
        self.scroll.add_widget(self.list)

        for w in (self.title, self.cap, self.total, self.pill, self.scroll):
            self.add_widget(w)

        # ---- 底部输入栏
        self.bar = RelativeLayout(size_hint=(None, None))
        with self.bar.canvas.before:
            Color(1, 1, 1, 0.96)
            self._bar_bg = Rectangle()
        with self.bar.canvas:
            Color(*theme.LINE)
            self._bar_line = Line(points=[], width=1)
        self.add_widget(self.bar)

        self.in_content = RoundInput(hint="想要什么")
        self.in_price = RoundInput(hint="价格")
        self.in_price.input_type = "number"
        self.add_btn = CirclePlus(size_hint=(None, None))
        self.add_btn.bind(on_release=lambda *a: self.add_wish())
        self.in_price.bind(on_text_validate=lambda *a: self.add_wish())
        for w in (self.in_content, self.in_price, self.add_btn):
            self.bar.add_widget(w)

        self.bind(pos=self._relayout, size=self._relayout)
        self._relayout()
        self.refresh()

    # ------------------------------------------------------------ 布局
    def _relayout(self, *a):
        w, h = self.size
        if w < 10 or h < 10:
            return
        pad = dp(20)
        self.title.size = (w - pad * 2, dp(24))
        self.title.pos = (pad, h - dp(44))

        s = dp(28)
        iy = h - dp(30) - s
        self.redo.size = (s, s)
        self.redo.pos = (w - dp(18) - s, iy)
        self.undo.size = (s, s)
        self.undo.pos = (self.redo.x - dp(14) - s, iy)

        self.cap.size = (w - pad * 2, dp(17))
        self.cap.pos = (pad, h - dp(74))
        self.total.size = (w - pad * 2 - dp(110), dp(40))
        self.total.pos = (pad, h - dp(114))

        self.pill.size = (dp(104), dp(32))
        self.pill.pos = (w - pad - dp(104), h - dp(108))

        bar_h = dp(64)
        self.bar.size = (w, bar_h)
        self.bar.pos = (0, 0)
        self._bar_bg.pos = (0, 0)
        self._bar_bg.size = (w, bar_h)
        self._bar_line.points = [0, bar_h - 0.5, w, bar_h - 0.5]

        ph = dp(40)
        py = (bar_h - ph) / 2.0
        bw = dp(40)
        self.add_btn.size = (bw, bw)
        self.add_btn.pos = (w - dp(16) - bw, (bar_h - bw) / 2.0)
        self.in_price.size = (dp(80), ph)
        self.in_price.pos = (self.add_btn.x - dp(8) - dp(80), py)
        self.in_content.size = (self.in_price.x - dp(16) - dp(8), ph)
        self.in_content.pos = (dp(16), py)

        list_top = h - dp(126)
        self.scroll.size = (w, max(dp(80), list_top - bar_h))
        self.scroll.pos = (0, bar_h)

    # ------------------------------------------------------------ 数据
    def do_undo(self):
        if self.store.undo():
            self._after_change()

    def do_redo(self):
        if self.store.redo():
            self._after_change()

    def _sync_icons(self):
        self.undo.ink = theme.INK_MID if self.store.can_undo() else theme.INK_FAINT
        self.redo.ink = theme.INK_MID if self.store.can_redo() else theme.INK_FAINT

    def refresh(self):
        self._sync_icons()
        self.total.text = "¥" + fmt_money(self.store.wish_total())
        self.pill.set_text("按时间" if self._sort == "time" else "按价钱")
        self._fill_list()

    def _fill_list(self):
        self.list.clear_widgets()
        rows = self.store.wishes(self._sort)
        for wish in rows:
            content = WishRow(wish)
            row = SwipeRow([("note", "备注", theme.INK_MID),
                            ("buy", "买下", theme.ACCENT),
                            ("del", "删除", theme.DANGER)],
                           self._on_row_action, content,
                           size_hint=(1, None), height=theme.ROW_H)
            row.wish = wish
            self.list.add_widget(row)
        if not rows:
            hint = lite_label("还没有想要的东西", theme.F_SMALL, theme.INK_SOFT,
                              halign="center")
            hint.size = (self.width, dp(70))
            self.list.add_widget(hint)
        self.list.height = max(dp(70), len(rows) * theme.ROW_H)

    # ------------------------------------------------------------ 交互
    def _pick_sort(self):
        labels = list(self.SORTS)

        def picked(text):
            self._sort = "price" if text == "按价钱" else "time"
            self.refresh()

        self.pick_one("排序", labels,
                      "按时间" if self._sort == "time" else "按价钱", picked)

    def add_wish(self):
        content = self.in_content.text.strip()
        cents = parse_amount(self.in_price.text)
        if not content:
            toast(self, "写点想要的东西")
            return
        if not cents:
            toast(self, "价格填一下")
            return
        self.store.add_wish(content, cents)
        self.in_content.text = ""
        self.in_price.text = ""
        self.refresh()
        toast(self, "记下了")

    def _on_row_action(self, key, row):
        wish = row.wish
        if key == "del":
            self.store.delete_wish(wish["id"])
            self._after_change()
        elif key == "note":
            self._edit_note(wish)
        elif key == "buy":
            self._buy(wish)

    def _buy(self, wish):
        if wish["price"] > self.store.balance():
            toast(self, "罐子里的钱还不够")
            return
        self.store.buy_wish(wish["id"])
        self._after_change()
        toast(self, "买下了")

    def _edit_note(self, wish):
        def save(text):
            self.store.set_wish_note(wish["id"], text)
            self._after_change()

        note_panel(self, "备注", wish["note"], save)

    def _after_change(self):
        self.refresh()
        app = App.get_running_app()
        if app and hasattr(app, "refresh_others"):
            app.refresh_others(self)
