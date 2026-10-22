# -*- coding: utf-8 -*-
"""私有画布。

Kivy 2.3.1 有两个很容易踩的坑，凡是"需要反复重画"的控件都必须绕开：

1. ``widget.canvas.before.clear()`` 会让 RenderContext.pop_state 抛
   ``IndexError: list index out of range``，而且是第一次 draw 就崩，必现。
2. ``widget.canvas.clear()`` 不会崩，但它会把**子控件的 canvas 一起摘掉**，
   子控件从此再也画不出来（不报错，就是看不见）。
   统计页 / 月报的图例只显示色点不显示文字，就是这么来的。

所以：需要反复重画的控件，一律用 :func:`art` 申请一块只属于自己的 Canvas，
之后只 clear 这一块。
"""

from kivy.graphics import Canvas


def art(widget, layer="before"):
    """取（或建）控件的一块私有画布，挂一次，之后随便 clear。

    :param layer: ``"before"`` 画在子控件下面，``"after"`` 画在上面。
    """
    key = "_art_" + layer
    c = getattr(widget, key, None)
    if c is None:
        c = Canvas()
        setattr(widget, key, c)
        if layer == "before":
            widget.canvas.before.add(c)
        else:
            widget.canvas.add(c)
    return c
