# -*- coding: utf-8 -*-
"""统计页：一张饼图卡片 + 年月下拉 + 该月报告 + 混合时间线。"""

import datetime

from kivy.graphics import Color, Ellipse
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.scrollview import ScrollView

from .. import theme
from ..storage import fmt_money, fmt_ts
from ..widgets.charts import LegendList, PieChart
from ..widgets.icons import RedoIcon, UndoIcon
from ..widgets.panel import (Card, PanelMixin, Pill, PillButton, mk_label,
                             note_panel, toast)
from ..widgets.swipe import RowContent, SwipeRow, lite_label

MONTH_FMT = "%d年%d月"


def month_text(m):
    y, mo = m.split("-")
    return MONTH_FMT % (int(y), int(mo))


class TxRow(RowContent):
    """一条流水。左滑出「备注 / 删除」。"""

    def __init__(self, tx, **kw):
        super().__init__(**kw)
        self.tx = tx
        is_in = tx["kind"] == "in"
        rgb = theme.ACCENT if is_in else theme.CAT_COLOR.get(tx["label"], theme.INK_SOFT)
        with self.canvas:
            self._dot_c = Color(*rgb)
            self._dot = Ellipse()
        self.t1 = lite_label(tx["label"] or ("存入" if is_in else "花掉"),
                             theme.F_BODY, theme.INK)
        self.t2 = lite_label(tx["note"] or fmt_ts(tx["ts"]), theme.F_SMALL, theme.INK_SOFT)
        self.t3 = lite_label(("＋" if is_in else "－") + fmt_money(tx["amount"]),
                             theme.F_BODY, theme.ACCENT if is_in else theme.INK,
                             halign="right")
        for l in (self.t1, self.t2, self.t3):
            self.add_widget(l)
        self.bind(size=self._lay)
        self._lay()

    def _lay(self, *a):
        w, h = self.size
        r = dp(3.4)
        self._dot.pos = (dp(22) - r, h / 2.0 - r)
        self._dot.size = (r * 2, r * 2)
        self.t1.size = (w - dp(34) - dp(118), dp(20))
        self.t1.pos = (dp(34), h / 2.0 + dp(1))
        self.t2.size = (w - dp(34) - dp(118), dp(17))
        self.t2.pos = (dp(34), h / 2.0 - dp(19))
        self.t3.size = (dp(102), h)
        self.t3.pos = (w - dp(16) - dp(102), 0)


class StatsScreen(RelativeLayout, PanelMixin):
    def __init__(self, store, **kw):
        self.store = store
        self._panel = None
        self._month = datetime.datetime.now().strftime("%Y-%m")
        super().__init__(**kw)

        self.title = mk_label("统计", theme.F_TITLE, theme.INK)
        self.add_widget(self.title)

        # 右上：撤销 / 重做（和罐子页同一套图标）
        self.undo = UndoIcon(size_hint=(None, None))
        self.redo = RedoIcon(size_hint=(None, None))
        for ic in (self.undo, self.redo):
            self.add_widget(ic)
        self.undo.bind(on_release=lambda *a: self.do_undo())
        self.redo.bind(on_release=lambda *a: self.do_redo())

        self.card = Card()
        self.add_widget(self.card)
        self.pie = PieChart(hole_color=(1, 1, 1, 1))
        self.card.add_widget(self.pie)
        self.legend = LegendList()
        self.card.add_widget(self.legend)
        self.empty_lbl = mk_label("这个月还没花钱", theme.F_SMALL, theme.INK_SOFT,
                                  halign="center")
        self.card.add_widget(self.empty_lbl)

        self.pill = Pill()
        self.pill.bind(on_release=lambda *a: self._pick_month())
        self.add_widget(self.pill)

        self.report_btn = PillButton(text="该月报告", font_size=theme.F_SMALL)
        self.report_btn.size_hint = (None, None)
        self.report_btn.fill = (1, 1, 1, 1)
        self.report_btn.color = theme.INK
        self.report_btn.line_color = theme.INK_MID
        self.report_btn.line_width = dp(1.0)
        self.report_btn.bind(on_release=lambda *a: self._open_report())
        self.add_widget(self.report_btn)

        self.scroll = ScrollView(do_scroll_x=False, do_scroll_y=True,
                                 bar_width=dp(2), scroll_type=["bars", "content"])
        self.scroll.size_hint = (None, None)      # 本页是 RelativeLayout，不给 None 会被铺满
        self.list = BoxLayout(orientation="vertical", size_hint=(1, None), spacing=0)
        self.scroll.add_widget(self.list)
        self.add_widget(self.scroll)

        self.bind(pos=self._relayout, size=self._relayout)
        self._relayout()
        self.refresh()

    # ------------------------------------------------------------ 布局
    def _relayout(self, *a):
        w, h = self.size
        if w < 10:
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

        card_h = min(dp(170), h * 0.27)
        self.card.size = (w - pad * 2, card_h)
        self.card.pos = (pad, h - dp(56) - card_h)

        ph = card_h - dp(30)
        self.pie.size = (ph, ph)
        self.pie.pos = (dp(16), (card_h - ph) / 2.0)
        lx = dp(16) + ph + dp(16)
        self.legend.size = (w - pad * 2 - lx - dp(16), ph)
        self.legend.pos = (lx, (card_h - ph) / 2.0)
        self.empty_lbl.size = (w - pad * 2, card_h)
        self.empty_lbl.pos = (pad, 0)

        row_y = h - dp(56) - card_h - dp(46)
        self.pill.size = (dp(122), dp(32))
        self.pill.pos = (pad, row_y)
        self.report_btn.size = (dp(88), dp(32))
        self.report_btn.pos = (w - pad - dp(88), row_y)

        list_top = row_y - dp(12)
        self.scroll.size = (w, max(dp(100), list_top))
        self.scroll.pos = (0, 0)

        self.legend._relayout()

    # ------------------------------------------------------------ 数据
    def do_undo(self):
        if self.store.undo():
            self._after_change()

    def do_redo(self):
        if self.store.redo():
            self._after_change()

    def refresh(self):
        self._sync_icons()
        self.pill.set_text(month_text(self._month))
        groups = self.store.tx_group_by_label(self._month)
        total = sum(groups.values())
        items = sorted(groups.items(), key=lambda kv: -kv[1])
        pie_data = []
        legend_items = []
        for name, amt in items:
            rgb = theme.CAT_COLOR.get(name, theme.INK_SOFT)
            pie_data.append((name, amt, rgb))
            legend_items.append((name, "%d%%" % round(amt * 100.0 / total) if total else "0%", rgb))
        self.pie.data = pie_data
        self.legend.set_items(legend_items[:5])
        self.empty_lbl.opacity = 0 if pie_data else 1
        self.pie.opacity = 1 if pie_data else 0
        self.legend.opacity = 1 if pie_data else 0
        self._fill_list()

    def _fill_list(self):
        self.list.clear_widgets()
        rows = self.store.tx_list(self._month)
        for tx in rows:
            content = TxRow(tx)
            row = SwipeRow([("note", "备注", theme.INK_MID),
                            ("del", "删除", theme.DANGER)],
                           self._on_row_action, content,
                           size_hint=(1, None), height=theme.ROW_H)
            row.tx = tx
            self.list.add_widget(row)
        if not rows:
            hint = lite_label("还没有记录", theme.F_SMALL, theme.INK_SOFT, halign="center")
            hint.size = (self.width, dp(60))
            self.list.add_widget(hint)
        self.list.height = max(dp(60), len(rows) * theme.ROW_H)

    def _sync_icons(self):
        self.undo.ink = theme.INK_MID if self.store.can_undo() else theme.INK_FAINT
        self.redo.ink = theme.INK_MID if self.store.can_redo() else theme.INK_FAINT

    # ------------------------------------------------------------ 交互
    def _months(self):
        cur = datetime.datetime.now().strftime("%Y-%m")
        ms = [cur] + [m for m in self.store.months() if m != cur]
        return ms[:10]

    def _pick_month(self):
        ms = self._months()
        labels = [month_text(m) for m in ms]
        text2month = dict(zip(labels, ms))

        def picked(text):
            self._month = text2month.get(text, self._month)
            self.refresh()

        self.pick_one("选择月份", labels, month_text(self._month), picked)

    def _on_row_action(self, key, row):
        tx = row.tx
        if key == "del":
            self.store.delete_tx(tx["id"])
            self._after_change()
        elif key == "note":
            self._edit_note(tx)

    def _edit_note(self, tx):
        def save(text):
            self.store.set_tx_note(tx["id"], text)
            self._after_change()

        note_panel(self, "备注", tx["note"], save)

    def _after_change(self):
        self.refresh()
        from kivy.app import App
        app = App.get_running_app()
        if app and hasattr(app, "refresh_others"):
            app.refresh_others(self)

    def _open_report(self):
        from .report import open_report
        open_report(self, self.store, self._month)
