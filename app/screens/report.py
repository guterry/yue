# -*- coding: utf-8 -*-
"""该月报告：月饼图 + 单笔最大 + 分类前三 + 近半年折线 + 与上月对比。"""

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget

from .. import theme
from ..storage import fmt_money
from ..util import save_png
from ..widgets.charts import LegendList, LineChart, PieChart
from ..widgets.panel import Card, PillButton, flabel, toast


def month_text(m):
    y, mo = m.split("-")
    return "%d年%d月" % (int(y), int(mo))


def prev_month(m):
    y, mo = [int(x) for x in m.split("-")]
    mo -= 1
    if mo == 0:
        y, mo = y - 1, 12
    return "%04d-%02d" % (y, mo)


def _line(left, right="", size=None, lcolor=theme.INK, rcolor=theme.INK_MID,
          height=dp(22)):
    box = BoxLayout(orientation="horizontal", size_hint=(1, None), height=height)
    box.add_widget(flabel(left, size or theme.F_BODY, lcolor))
    if right:
        r = flabel(right, size or theme.F_BODY, rcolor, halign="right")
        r.size_hint = (None, 1)
        r.width = dp(112)
        box.add_widget(r)
    return box


def _spacer(h=None):
    w = Widget(size_hint=(1, None))
    w.height = h if h is not None else dp(4)
    return w


def open_report(host, store, month):
    """host 需要实现 open_panel(card, size)。"""
    spend = abs(store.month_sum(month, "out"))
    groups = store.tx_group_by_label(month)
    items = sorted(groups.items(), key=lambda kv: -kv[1])
    top1 = store.month_top(month, "out")

    w = min(host.width * 0.92, dp(360))
    card = Card()
    box = BoxLayout(orientation="vertical", size_hint=(1, 1),
                    padding=[dp(22), dp(20)], spacing=dp(7))
    card.add_widget(box)

    box.add_widget(flabel(month_text(month) + " 报告", theme.F_TITLE, theme.INK,
                          height=dp(28)))
    box.add_widget(flabel("这个月花了", theme.F_SMALL, theme.INK_SOFT, height=dp(15)))
    box.add_widget(flabel("¥" + fmt_money(spend), dp(28), theme.INK, height=dp(36)))

    # ---- 饼图 + 图例
    row = BoxLayout(orientation="horizontal", size_hint=(1, None), height=dp(94),
                    spacing=dp(10))
    pie = PieChart(hole_color=(1, 1, 1, 1))
    pie.size_hint = (None, None)
    pie.size = (dp(94), dp(94))
    pie.data = [(n, v, theme.CAT_COLOR.get(n, theme.INK_SOFT)) for n, v in items]
    lg = LegendList()
    lg.size_hint = (1, 1)
    lg.set_items([(n, "%d%%" % round(v * 100.0 / spend) if spend else "0%",
                   theme.CAT_COLOR.get(n, theme.INK_SOFT)) for n, v in items[:4]])
    row.add_widget(pie)
    row.add_widget(lg)
    box.add_widget(row)

    # ---- 最大的一笔
    if top1:
        box.add_widget(_spacer(dp(2)))
        box.add_widget(flabel("最贵的一笔", theme.F_SMALL, theme.INK_SOFT, height=dp(15)))
        name = top1["label"] or "花掉"
        if top1["note"]:
            name += " · " + top1["note"]
        box.add_widget(_line(name, "¥" + fmt_money(top1["amount"]),
                            theme.F_BODY, theme.INK, theme.INK, dp(21)))

    # ---- 分类前三
    if items:
        box.add_widget(_spacer(dp(4)))
        box.add_widget(flabel("花得最多的三类", theme.F_SMALL, theme.INK_SOFT,
                              height=dp(15)))
        for name, amt in items[:3]:
            pct = "%d%%" % round(amt * 100.0 / spend) if spend else "0%"
            box.add_widget(_line("· " + name, fmt_money(amt) + "   " + pct,
                                theme.F_SMALL, theme.INK_MID, theme.INK_SOFT, dp(20)))

    # ---- 近半年折线
    months = store.last_months(6, end_month=month)
    vals = [abs(store.month_sum(m, "out")) for m in months]
    box.add_widget(_spacer(dp(4)))
    box.add_widget(flabel("近半年花销", theme.F_SMALL, theme.INK_SOFT, height=dp(15)))
    chart = LineChart(values=vals, size_hint=(1, None))
    chart.height = dp(54)
    box.add_widget(chart)
    box.add_widget(flabel("   ".join("%d月" % int(m.split("-")[1]) for m in months),
                          theme.F_TINY, theme.INK_SOFT, height=dp(14)))

    # ---- 与上月对比（上月没数据就不显示）
    pm = prev_month(month)
    pval = abs(store.month_sum(pm, "out"))
    if pval > 0:
        diff = spend - pval
        pct = abs(diff) * 100.0 / pval
        if diff > 0:
            txt = "比上月多花 ¥%s（+%d%%）" % (fmt_money(diff), round(pct))
            col = theme.DANGER
        elif diff < 0:
            txt = "比上月少花 ¥%s（-%d%%）" % (fmt_money(-diff), round(pct))
            col = theme.ACCENT
        else:
            txt = "和上月一样多"
            col = theme.INK_MID
        box.add_widget(_spacer(dp(2)))
        box.add_widget(flabel(txt, theme.F_SMALL, col, height=dp(18)))

    # ---- 保存
    box.add_widget(_spacer(dp(6)))
    ok = PillButton(text="保存到相册", font_size=theme.F_SMALL,
                    size_hint=(1, None), height=dp(42))
    box.add_widget(ok)

    def save(*a):
        path = save_png(card, "报告")
        if path:
            toast(host, "已保存到相册")
        else:
            toast(host, "保存失败，检查存储权限")

    ok.bind(on_release=save)

    h = min(dp(20) * 2 + sum(c.height for c in box.children) + dp(7) * (len(box.children) - 1),
            host.height - dp(40))
    host.open_panel(card, (w, h))
