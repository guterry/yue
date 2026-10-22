# -*- coding: utf-8 -*-
"""设置：背景图、备份导出/导入、关于、清空。"""

import os
from datetime import datetime

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget

from .. import theme
from ..storage import fmt_money
from ..widgets.panel import Card, PillButton, flabel, toast

IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")
SCAN_DIRS = [
    "/sdcard/DCIM/Camera",
    "/sdcard/Pictures",
    "/sdcard/Download",
    os.path.expanduser("~/Pictures"),
    os.path.expanduser("~/Desktop"),
    os.path.expanduser("~/Downloads"),
]


# ---------------------------------------------------------------- 小零件

def _gap(h):
    w = Widget(size_hint=(1, None))
    w.height = h
    return w


def _row(title, btn_text, on_press, note=""):
    box = BoxLayout(orientation="horizontal", size_hint=(1, None), height=dp(40))
    col = BoxLayout(orientation="vertical", size_hint=(1, 1))
    col.add_widget(flabel(title, theme.F_BODY, theme.INK, height=dp(21)))
    if note:
        col.add_widget(flabel(note, theme.F_TINY, theme.INK_SOFT, height=dp(15)))
    box.add_widget(col)
    btn = PillButton(text=btn_text, font_size=theme.F_SMALL,
                     size_hint=(None, None), size=(dp(78), dp(30)))
    btn.fill = (1, 1, 1, 1)
    btn.color = theme.INK
    btn.line_color = theme.INK_MID
    btn.line_width = dp(1.0)
    btn.bind(on_release=lambda *a: on_press())
    box.add_widget(btn)
    return box


def _card_box():
    card = Card()
    box = BoxLayout(orientation="vertical", size_hint=(1, 1),
                    padding=[dp(22), dp(18)], spacing=dp(8))
    card.add_widget(box)
    return card, box


def _fit(host, card, box, w):
    h = dp(36) + sum(c.height for c in box.children) + dp(8) * (len(box.children) - 1)
    return card, (w, min(h, host.height - dp(60)))


# ---------------------------------------------------------------- 备份

def backup_dir():
    from kivy.app import App
    app = App.get_running_app()
    base = app.user_data_dir if app else os.getcwd()
    d = os.path.join(base, "backups")
    os.makedirs(d, exist_ok=True)
    return d


def backup_files():
    d = backup_dir()
    out = []
    for f in sorted(os.listdir(d), reverse=True):
        if f.endswith(".json"):
            out.append(os.path.join(d, f))
    return out


def do_backup(store):
    name = "backup-%s.json" % datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(backup_dir(), name)
    store.export_json(path)
    return path


# ---------------------------------------------------------------- 面板

def open_settings(host, store):
    w = min(host.width * 0.92, dp(360))
    card, box = _card_box()

    box.add_widget(flabel("设置", theme.F_TITLE, theme.INK, height=dp(30)))

    bg = store.get_setting("bg_image", "")
    box.add_widget(_row("背景图", "换一张" if not bg else "换一张",
                        lambda: open_bg_picker(host, store),
                        note="当前：自定义图片" if bg else "当前：默认米白"))
    if bg:
        from kivy.clock import Clock
        box.add_widget(_row("", "用默认", lambda: _reset_bg(host, store), note=""))

    box.add_widget(_gap(dp(2)))

    backups = backup_files()
    box.add_widget(_row("备份数据", "导出",
                        lambda: _export(host, store),
                        note="共 %d 份备份" % len(backups) if backups else "还没有备份"))
    box.add_widget(_row("恢复备份", "选择",
                        lambda: _restore(host, store),
                        note="最近：%s" % os.path.basename(backups[0]) if backups else ""))

    box.add_widget(_gap(dp(4)))

    about = BoxLayout(orientation="vertical", size_hint=(1, None), height=dp(56))
    about.add_widget(flabel("看见余额 v0.1", theme.F_SMALL, theme.INK_MID, height=dp(18)))
    about.add_widget(flabel("把看不见的余额，变成看得见的厚度。",
                            theme.F_TINY, theme.INK_SOFT, height=dp(16)))
    about.add_widget(flabel("数据只存这台手机，不联网。", theme.F_TINY,
                            theme.INK_SOFT, height=dp(16)))
    box.add_widget(about)

    clear = PillButton(text="清空所有数据", font_size=theme.F_SMALL,
                       size_hint=(1, None), height=dp(40))
    clear.fill = (1, 1, 1, 1)
    clear.color = theme.DANGER
    clear.line_color = theme.DANGER
    clear.line_width = dp(1.0)
    clear.bind(on_release=lambda *a: _confirm_clear(host, store))
    box.add_widget(clear)

    card, size = _fit(host, card, box, w)
    host.open_panel(card, size)


def _reset_bg(host, store):
    store.set_setting("bg_image", "")
    _apply_bg()
    host.close_panel()
    toast(host, "背景已恢复")


def _apply_bg():
    from kivy.app import App
    app = App.get_running_app()
    if app and hasattr(app, "apply_bg"):
        app.apply_bg()


def _export(host, store):
    try:
        path = do_backup(store)
    except Exception:
        toast(host, "导出失败")
        return
    host.close_panel()
    toast(host, "已导出：%s" % os.path.basename(path))


def _restore(host, store):
    files = backup_files()
    if not files:
        toast(host, "还没有备份")
        return
    labels = [os.path.basename(f) for f in files][:12]
    names = dict((os.path.basename(f), f) for f in files)

    def picked(label):
        path = names.get(label)
        if not path:
            return
        try:
            store.import_json(path)
        except Exception:
            toast(host, "这个备份读不了")
            return
        _apply_bg()
        from kivy.app import App
        app = App.get_running_app()
        if app and hasattr(app, "refresh_others"):
            app.refresh_others(None)
        toast(host, "已恢复")

    host.pick_one("选择备份", labels, labels[0], picked)


def _confirm_clear(host, store):
    w = min(host.width * 0.82, dp(320))
    card, box = _card_box()
    box.add_widget(flabel("清空所有数据？", theme.F_TITLE, theme.INK, height=dp(30)))
    box.add_widget(flabel("存钱、花销、心愿都会删掉，且不能撤销。",
                          theme.F_SMALL, theme.INK_SOFT, height=dp(20)))
    row = BoxLayout(orientation="horizontal", size_hint=(1, None), height=dp(44),
                    spacing=dp(10))
    no = PillButton(text="算了", font_size=theme.F_BODY, size_hint=(1, 1))
    no.fill = (1, 1, 1, 1)
    no.color = theme.INK
    no.line_color = theme.INK_MID
    no.line_width = dp(1.0)
    yes = PillButton(text="清 空", font_size=theme.F_BODY, size_hint=(1, 1))
    yes.fill = theme.DANGER
    no.bind(on_release=lambda *a: _reopen(host, store))
    yes.bind(on_release=lambda *a: _do_clear(host, store))
    row.add_widget(no)
    row.add_widget(yes)
    box.add_widget(row)
    card, size = _fit(host, card, box, w)
    host.swap_panel(card, size)


def _reopen(host, store):
    from kivy.clock import Clock
    host.close_panel()
    Clock.schedule_once(lambda dt: open_settings(host, store), 0.18)


def _do_clear(host, store):
    store.clear_all()
    host.close_panel()
    from kivy.app import App
    app = App.get_running_app()
    if app and hasattr(app, "refresh_others"):
        app.refresh_others(None)
    toast(host, "已清空")


# ---------------------------------------------------------------- 背景图

def _scan_images(limit=40):
    found = []
    for d in SCAN_DIRS:
        if not os.path.isdir(d):
            continue
        try:
            for f in os.listdir(d):
                if f.lower().endswith(IMG_EXT):
                    p = os.path.join(d, f)
                    try:
                        found.append((os.path.getmtime(p), p))
                    except Exception:
                        pass
        except Exception:
            continue
        if len(found) >= limit * 2:
            break
    found.sort(reverse=True)
    return [p for _t, p in found][:limit]


def open_bg_picker(host, store):
    w = min(host.width * 0.92, dp(360))
    h = min(dp(430), host.height - dp(60))
    card, box = _card_box()
    box.add_widget(flabel("挑一张背景", theme.F_TITLE, theme.INK, height=dp(30)))

    files = _scan_images()
    hint = flabel("找到 %d 张图片，点一张就换" % len(files) if files
                  else "没找到图片，把图片放进相册再试", theme.F_SMALL,
                  theme.INK_SOFT, height=dp(36))
    box.add_widget(hint)

    from kivy.uix.scrollview import ScrollView
    sv = ScrollView(size_hint=(1, 1), do_scroll_x=False,
                    bar_width=dp(2), scroll_type=["bars", "content"])
    lst = BoxLayout(orientation="vertical", size_hint=(1, None), spacing=0)
    sv.add_widget(lst)

    def pick(path):
        store.set_setting("bg_image", path)
        _apply_bg()
        _reopen(host, store)
        toast(host, "换好了")

    for p in files:
        b = PillButton(text=os.path.basename(p)[:26], font_size=theme.F_SMALL,
                       size_hint=(1, None), height=dp(36))
        b.fill = (1, 1, 1, 0)
        b.color = theme.INK_MID
        b.line_color = (0, 0, 0, 0)
        b.bind(on_release=lambda inst, path=p: pick(path))
        lst.add_widget(b)
    lst.height = max(h - dp(160), len(files) * dp(36) + dp(20))
    box.add_widget(sv)
    host.swap_panel(card, (w, h))
