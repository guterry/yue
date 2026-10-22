# -*- coding: utf-8 -*-
"""看见余额 —— 把看不见的余额，变成看得见的厚度。

开发预览：  .venv\\Scripts\\python main.py
打包 APK：  推到 GitHub 后跑 Actions 里的「打包安卓 APK」
"""

__version__ = "0.1"

import os
import sys

# 控制台默认是 GBK，打印带 ¥ 的调试信息会炸；统一改成 utf-8
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

os.environ.setdefault("KIVY_NO_ARGS", "1")

from kivy.config import Config

Config.set("graphics", "width", "390")
Config.set("graphics", "height", "844")
Config.set("graphics", "resizable", "1")
Config.set("input", "mouse", "mouse,multitouch_on_demand")

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.stencilview import StencilView

from app import theme
from app.screens.jar_screen import JarScreen
from app.screens.stats_screen import StatsScreen
from app.screens.wish_screen import WishScreen
from app.storage import Store
from app.widgets.nav import NavBar
from app.widgets.panel import CenterPanel, PillButton, RoundCard

# ---------------------------------------------------------------- 字体

FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/msyhl.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "/system/fonts/NotoSansCJK-Regular.ttc",
    "/system/fonts/NotoSansSC-Regular.otf",
    "/system/fonts/NotoSansCJKsc-Regular.otf",
    "/system/fonts/SourceHanSansCN-Regular.otf",
    "/system/fonts/DroidSansFallback.ttf",
    "/system/fonts/DroidSansFallbackFull.ttf",
]

# 各家安卓的中文字体文件名不统一，硬编码路径靠不住，
# 所以最后兜底直接扫 /system/fonts，认名字里的关键字。
FONT_NAME_KEYS = ("cjk", "hans", "hanserif", "sc-regular", "han", "noto",
                  "sourcehan", "droid", "fallback", "miui", "huawei")


def _scan_system_fonts():
    d = "/system/fonts"
    if not os.path.isdir(d):
        return None
    try:
        names = sorted(os.listdir(d))
    except Exception:
        return None
    fallback = None
    for fn in names:
        low = fn.lower()
        if not low.endswith((".ttf", ".ttc", ".otf")):
            continue
        if not any(k in low for k in FONT_NAME_KEYS):
            continue
        if "regular" in low or "normal" in low:
            return os.path.join(d, fn)
        if fallback is None:
            fallback = os.path.join(d, fn)
    return fallback


def register_font():
    paths = list(FONT_CANDIDATES)
    scanned = _scan_system_fonts()
    if scanned:
        paths.append(scanned)
    for path in paths:
        if path and os.path.exists(path):
            try:
                LabelBase.register(name="CN", fn_regular=path)
                return path
            except Exception:
                continue
    # 实在没有中文字体：退回 Kivy 自带字体，中文会变成方块，但至少不崩
    try:
        from kivy import kivy_data_dir
        LabelBase.register(name="CN",
                           fn_regular=os.path.join(kivy_data_dir, "fonts",
                                                   "Roboto-Regular.ttf"))
    except Exception:
        pass
    return None


# ---------------------------------------------------------------- 页面容器


class PageHost(RelativeLayout):
    """三个页面横向排列，切换时一起平移。

    必须是 RelativeLayout：只有它会把子控件的坐标相对自己平移。
    """

    def __init__(self, pages, index=0, **kw):
        super().__init__(**kw)
        self.size_hint = (None, None)
        self.pages = pages
        self.cur = index
        for p in pages:
            self.add_widget(p)
        self.bind(size=self._layout)

    def _layout(self, *a):
        for i, p in enumerate(self.pages):
            p.size = self.size
            p.pos = ((i - self.cur) * self.width, 0)

    def goto(self, idx):
        if idx == self.cur or not (0 <= idx < len(self.pages)):
            return
        self.cur = idx
        for i, p in enumerate(self.pages):
            Animation(x=(i - idx) * self.width, d=0.26, t="out_cubic").start(p)


class Placeholder(RelativeLayout):
    def __init__(self, title, **kw):
        super().__init__(**kw)
        self.add_widget(Label(text=title, font_name="CN",
                              font_size=theme.F_TITLE, color=theme.INK_SOFT))

    def refresh(self):
        pass


class Root(FloatLayout):
    def __init__(self, store, **kw):
        super().__init__(**kw)
        self.store = store

        with self.canvas.before:
            self._bgc = Color(*theme.BG)
            self._bg = Rectangle()
            self._ovc = Color(1, 1, 1, 0)
            self._ov = Rectangle()

        self.stats = StatsScreen(store)
        self.jar_screen = JarScreen(store)
        self.wish = WishScreen(store)

        start = int(os.environ.get("PAGE", "1"))
        self.host = PageHost([self.stats, self.jar_screen, self.wish], start)
        self.stencil = StencilView(size_hint=(None, None))
        self.stencil.add_widget(self.host)
        self.add_widget(self.stencil)

        self.nav = NavBar(["统计", "储钱罐", "我想要的"], self._on_nav, index=start)
        self.add_widget(self.nav)

        self.bind(pos=self._layout, size=self._layout)
        self._layout()

    def _layout(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._ov.pos = self.pos
        self._ov.size = self.size
        h = max(0, self.height - theme.NAV_H)
        self.stencil.pos = (0, theme.NAV_H)
        self.stencil.size = (self.width, h)
        self.host.size = (self.width, h)
        self.host.pos = self.stencil.pos   # StencilView 不是布局，子控件不会自动跟随
        self.nav.size_hint = (None, None)
        self.nav.size = (self.width, theme.NAV_H)
        self.nav.pos = (0, 0)
        if os.environ.get("DEBUG"):
            print("ROOT", self.size, "stencil", self.stencil.pos, self.stencil.size,
                  "host", self.host.size)
            for i, p in enumerate(self.host.pages):
                print("  page", i, p.pos, p.size)
            print("  nav", self.nav.size)
            for i, it in enumerate(self.nav.items):
                print("  item", i, it.pos, it.size)

    def _on_nav(self, idx):
        self.host.goto(idx)

    def apply_bg(self, path=""):
        """有自定义背景就铺图 + 一层白雾，保证文字还看得清。"""
        tex = None
        if path:
            try:
                from kivy.core.image import Image as CoreImage
                tex = CoreImage(path).texture
            except Exception:
                tex = None
        if tex:
            self._bg.texture = tex
            self._bgc.rgba = (1, 1, 1, 1)
            self._ovc.a = 0.58
        else:
            self._bg.texture = None
            self._bgc.rgba = theme.BG
            self._ovc.a = 0

    def refresh_others(self, exclude=None):
        for p in (self.stats, self.jar_screen, self.wish):
            if p is exclude:
                continue
            if hasattr(p, "refresh"):
                p.refresh()


# ---------------------------------------------------------------- App


class KanjianApp(App):
    name = "kanjianyue"
    title = "看见余额"

    def build(self):
        Window.clearcolor = (*theme.BG[:3], 1)
        self.font_path = register_font()
        db = os.path.join(self.user_data_dir, "data.db")
        self.store = Store(db)

        if os.environ.get("SEED"):
            self._seed()

        self.root_w = Root(self.store)
        self.root_w.apply_bg(self.store.get_setting("bg_image", ""))

        panel = os.environ.get("PANEL")
        if panel:
            Clock.schedule_once(lambda dt: self._dev_panel(panel), 0.5)

        shot = os.environ.get("SHOT")
        if shot:
            Clock.schedule_once(lambda dt: self._shot(shot), 1.8)
        return self.root_w

    def _dev_panel(self, name):
        """只在预览时用：SHOT 前先把某个面板打开，方便看效果。"""
        r = self.root_w
        try:
            if name == "report":
                r.stats._open_report()
            elif name == "settings":
                r.jar_screen.open_settings()
            elif name == "income":
                r.jar_screen.open_income()
            elif name == "expense":
                r.jar_screen.open_expense()
            elif name == "sort":
                r.wish._pick_sort()
            elif name == "bg":
                from app.screens.settings import open_bg_picker
                open_bg_picker(r.jar_screen, self.store)
            elif name == "clear":
                from app.screens.settings import _confirm_clear
                _confirm_clear(r.jar_screen, self.store)
            elif name.startswith("note"):
                r.stats._edit_note(r.store.tx_list(r.stats._month)[0])
        except Exception as e:
            print("dev panel failed:", name, e)

    def apply_bg(self):
        if hasattr(self, "root_w"):
            self.root_w.apply_bg(self.store.get_setting("bg_image", ""))

    def _shot(self, path):
        if os.environ.get("DEBUG"):
            r = self.root_w
            print("SHOT root", r.size)
            for i, p in enumerate(r.host.pages):
                print("SHOT page", i, p.pos, p.size)
            print("SHOT nav", r.nav.size, "ind_x", r.nav.ind_x)
            for i, it in enumerate(r.nav.items):
                print("SHOT item", i, it.pos, it.size, it.text, it.active)
        if os.environ.get("DEBUG_TREE"):
            self._tree(self.root_w, 0)
        try:
            self.root_w.export_to_png(path + ".png")
        except Exception as e:
            print("screenshot failed:", e)
        Clock.schedule_once(lambda dt: self.stop(), 0.4)

    @staticmethod
    def _tree(w, depth):
        txt = getattr(w, "text", "")
        try:
            aw = tuple(round(v, 1) for v in w.to_window(0, 0, relative=True))
        except Exception:
            aw = None
        print("  " * depth + f"{type(w).__name__} pos={tuple(round(v,1) for v in w.pos)} "
              f"size={tuple(round(v,1) for v in w.size)} abs={aw} op={round(w.opacity,2)} {txt!r}")
        for c in w.children:
            KanjianApp._tree(c, depth + 1)

    def _seed(self):
        """只在预览时用：灌一批贴着「今天」的示例数据。"""
        import datetime as _dt

        s = self.store
        s.conn.execute("DELETE FROM tx")
        s.conn.execute("DELETE FROM wish")

        now = _dt.datetime.now()

        def ts(days_ago, hour=13):
            d = (now - _dt.timedelta(days=days_ago)).replace(
                hour=hour, minute=20, second=0, microsecond=0)
            return int(d.timestamp())

        txs = [
            ("in", 480000, "九月工资", "", ts(26)),
            ("in", 50000, "奶奶给的", "", ts(19)),
            ("in", 8800, "周末兼职", "", ts(9)),
            ("out", 45800, "饮食", "楼下那家面", ts(6)),
            ("out", 12900, "电子", "充电线", ts(4)),
            ("out", 2300, "交通", "", ts(2)),
            ("out", 8800, "娱乐", "看了一场电影", ts(35)),
            ("out", 32000, "饮食", "", ts(38)),
            ("out", 5600, "交通", "", ts(66)),
        ]
        for kind, amt, lab, note, t in txs:
            s.conn.execute(
                "INSERT INTO tx(kind, amount, label, note, ts) VALUES(?,?,?,?,?)",
                (kind, amt, lab, note, t),
            )
        for content, price, note in [("相机", 480000, "想要很久了"),
                                     ("一双好鞋", 89000, ""),
                                     ("去看海", 300000, "夏天之前")]:
            s.conn.execute(
                "INSERT INTO wish(content, price, note, ts) VALUES(?,?,?,?)",
                (content, price, note, ts(20)),
            )
        s.conn.commit()


if __name__ == "__main__":
    KanjianApp().run()
