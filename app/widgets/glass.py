# -*- coding: utf-8 -*-
"""玻璃罐材质。

不依赖任何图片资源：所有玻璃的渐变、厚度、高光都在运行时按数学公式
烘成一张小纹理（64x40），再用 Mesh 贴到罐身上。好处是任意尺寸都不糊、
不用往 APK 里塞素材、颜色随时可调。

调用方需要先 `with canvas:` 再调这里的函数，指令会追加到该画布上。
"""

import math

from kivy.graphics import Color, Ellipse, Line, Mesh
from kivy.graphics.texture import Texture
from kivy.metrics import dp

from .. import theme

_CACHE = {}


# ---------------------------------------------------------------- 工具
def _clamp(x, a=0.0, b=1.0):
    return a if x < a else (b if x > b else x)


def _g(d, s):
    """高斯衰减，用来做柔边。"""
    return math.exp(-(d * d) / (2.0 * s * s))


def _fade(v, lo, hi):
    """竖直方向两端渐隐，lo 是底部渐入区，hi 是顶部渐出区。"""

    def ss(x):
        x = _clamp(x)
        return x * x * (3.0 - 2.0 * x)

    return ss(v / lo if lo > 0 else 1.0) * ss((1.0 - v) / hi if hi > 0 else 1.0)


def _ramp(w, h, fn):
    """按 fn(u, v) -> (r,g,b,a) 烘一张纹理。u 左->右，v 下->上。"""
    buf = bytearray()
    for j in range(h):
        v = j / (h - 1) if h > 1 else 0.0
        for i in range(w):
            u = i / (w - 1) if w > 1 else 0.0
            r, g, b, a = fn(u, v)
            buf += bytes((int(_clamp(r) * 255), int(_clamp(g) * 255),
                          int(_clamp(b) * 255), int(_clamp(a) * 255)))
    tex = Texture.create(size=(w, h))
    tex.blit_buffer(bytes(buf), colorfmt="rgba", bufferfmt="ubyte")
    tex.min_filter = "linear"
    tex.mag_filter = "linear"
    return tex


# ---------------------------------------------------------------- 纹理
def tex_body():
    """罐身玻璃：左右边缘是厚玻璃（更实、偏青灰），中间最透。"""
    if "body" in _CACHE:
        return _CACHE["body"]
    T, D = theme.GLASS_TINT, theme.GLASS_DEEP

    def fn(u, v):
        e = max(_g(u, 0.055), _g(1.0 - u, 0.055))              # 最外沿
        m = max(_g(u - 0.055, 0.055), _g(1.0 - u - 0.055, 0.055))  # 稍内侧
        k = _clamp(e + m * 0.45)
        r = T[0] + (D[0] - T[0]) * k
        g = T[1] + (D[1] - T[1]) * k
        b = T[2] + (D[2] - T[2]) * k
        a = 0.070 + 0.54 * e + 0.13 * m + 0.055 * (1.0 - v)    # 底部略沉
        return (r, g, b, a)

    _CACHE["body"] = _ramp(64, 40, fn)
    return _CACHE["body"]


def tex_shine(key, u0, s, peak, lo=0.10, hi=0.14):
    """一道竖向柔光：横向高斯、纵向两端渐隐。"""
    if key in _CACHE:
        return _CACHE[key]

    def fn(u, v):
        return (1.0, 1.0, 1.0, peak * _g(u - u0, s) * _fade(v, lo, hi))

    _CACHE[key] = _ramp(64, 40, fn)
    return _CACHE[key]


def tex_vignette():
    """罐壁在钱堆两侧投下的暗部。有了它，一叠纸才像是装在圆罐里。"""
    if "vig" in _CACHE:
        return _CACHE["vig"]

    def fn(u, v):
        d = max(_g(u, 0.105), _g(1.0 - u, 0.105))
        return (0.157, 0.125, 0.235, 0.62 * d)

    _CACHE["vig"] = _ramp(48, 8, fn)
    return _CACHE["vig"]


# ---------------------------------------------------------------- 轮廓
def _prof(v):
    """罐身半宽系数：底部略微收一点，玻璃罐才不是一根直筒。"""
    return 1.0 - 0.05 * (1.0 - v) ** 1.5


def _strip(W, ya, yb, ua, ub, tex, n=9, span=None):
    """把纹理的 [ua,ub] 这一竖条，沿罐身轮廓贴成一条带。

    span 给的是整条罐身的 y 范围，用来算轮廓；只贴其中一段时也必须传，
    否则轮廓会按局部归一化，弧度就错了。
    """
    y0, y1 = span if span else (ya, yb)
    verts = []
    cx = W / 2.0
    for i in range(n + 1):
        t = i / float(n)
        y = ya + (yb - ya) * t
        v = (y - y0) / (y1 - y0) if y1 > y0 else 0.0
        hw = W * _prof(_clamp(v)) / 2.0
        verts += [cx - hw + 2 * hw * ua, y, ua, v]
        verts += [cx - hw + 2 * hw * ub, y, ub, v]
    idx = []
    for i in range(n):
        a, b, c, d = 2 * i, 2 * i + 1, 2 * i + 2, 2 * i + 3
        idx += [a, b, d, a, d, c]
    Mesh(vertices=verts, indices=idx, mode="triangles", texture=tex)


def _arc(x, y, w, h, a0, a1, n=40):
    """采样一段椭圆弧。角度用数学惯例：0 在右，pi/2 在上。"""
    cx, cy = x + w / 2.0, y + h / 2.0
    rx, ry = w / 2.0, h / 2.0
    pts = []
    for i in range(n + 1):
        t = a0 + (a1 - a0) * i / float(n)
        pts += [cx + rx * math.cos(t), cy + ry * math.sin(t)]
    return pts


# ---------------------------------------------------------------- 零件
def shadow(W, ew):
    """落地投影：几层由小到大的椭圆叠出柔边，比纯黑轻。"""
    cx = W / 2.0
    for i in range(8):
        k = i / 7.0
        a = 0.20 * (1.0 - k) ** 1.7
        sw = W * (0.98 + k * 0.46)
        sh = ew * (0.85 + k * 2.7)
        Color(*theme.SHADOW_RGB, a)
        Ellipse(pos=(cx - sw / 2.0, -sh * 0.52), size=(sw, sh))


def table(W, ew):
    """桌面：一条很淡的横线，让罐子有落点。"""
    Color(*theme.TABLE_LINE, 0.9)
    tw = W * 1.26
    Line(points=[(W - tw) / 2.0, -dp(0.5), (W + tw) / 2.0, -dp(0.5)], width=1.0)


def bottom(W, ew):
    """罐底：玻璃底比罐壁厚一点，所以更实。"""
    Color(*theme.GLASS_TINT, 0.34)
    Ellipse(pos=(0, 0), size=(W, ew))
    Color(*theme.GLASS_LINE)
    Line(points=_arc(0, 0, W, ew, math.pi, 2 * math.pi), width=dp(1.8))  # 前半弧
    Color(*theme.GLASS_DEEP, 0.30)
    Line(points=_arc(0, 0, W, ew, 0, math.pi), width=dp(1.2))            # 后半弧


def body(W, h, ew):
    """罐身：玻璃本体 + 两道高光 + 左右收边。"""
    y0, y1 = ew / 2.0, h - ew / 2.0
    if y1 <= y0:
        return

    Color(1, 1, 1, 1)                                  # 颜色交给纹理
    _strip(W, y0, y1, 0.0, 1.0, tex_body())

    # 高光：左一道宽的，右一道窄的，玻璃的"灵魂"就在这两条
    _strip(W, y0 + dp(4), y1 - dp(3), 0.02, 0.36, tex_shine("sL", 0.165, 0.062, 0.62))
    _strip(W, y0 + dp(10), y1 - dp(12), 0.72, 0.99, tex_shine("sR", 0.878, 0.030, 0.44,
                                                             0.13, 0.16))
    _strip(W, y0 + dp(16), y1 - dp(20), 0.30, 0.52, tex_shine("sM", 0.408, 0.022, 0.22,
                                                              0.18, 0.22))

    # 左右两条极细的亮边，勾出圆柱的转折
    for ua, ub, pk in ((0.008, 0.030, 0.55), (0.968, 0.992, 0.40)):
        _strip(W, y0 + dp(2), y1 - dp(2), ua, ub,
               tex_shine("eL" if ua < 0.5 else "eR", (ua + ub) / 2.0, 0.010, pk,
                         0.06, 0.08))


def vignette(W, h, ew, yb, yt):
    """钱堆两侧的暗部。yb/yt 是钱堆的上下沿，span 用整条罐身。"""
    y0, y1 = ew / 2.0, h - ew / 2.0
    if yt <= yb or y1 <= y0:
        return
    ya = max(y0, yb)
    yb2 = min(y1, yt)
    if yb2 - ya < dp(3):
        return
    Color(1, 1, 1, 1)
    _strip(W, ya, yb2, 0.0, 1.0, tex_vignette(), n=3, span=(y0, y1))


def mouth(W, h, ew):
    """罐口：厚玻璃的口沿 + 内壁 + 前唇高光。"""
    y = h - ew
    # 口沿顶面
    Color(*theme.GLASS_TINT, 0.32)
    Ellipse(pos=(0, y), size=(W, ew))
    # 外圈：厚玻璃的截面
    Color(*theme.GLASS_LINE)
    Line(points=_arc(0, y, W, ew, 0, 2 * math.pi), width=dp(3.6))
    # 内壁：往里一圈，颜色更沉
    Color(*theme.GLASS_DEEP, 0.42)
    Line(points=_arc(dp(6), y + dp(1.6), W - dp(12), ew - dp(3.2), 0, 2 * math.pi),
         width=dp(1.6))
    # 前唇高光（下半弧偏左那一段最亮）
    Color(1, 1, 1, 0.92)
    Line(points=_arc(0, y, W, ew, math.pi * 1.18, math.pi * 1.62), width=dp(2.8))
    # 后唇一点反光
    Color(1, 1, 1, 0.42)
    Line(points=_arc(0, y, W, ew, math.pi * 0.22, math.pi * 0.52), width=dp(1.6))
