# -*- coding: utf-8 -*-
"""零碎工具：把界面存成图片。"""

import os
from datetime import datetime


def pictures_dir():
    """优先存到系统相册目录（安卓），桌面预览时退回应用私有目录。"""
    for base in ("/sdcard/Pictures", "/storage/emulated/0/Pictures"):
        if os.path.isdir(base):
            return os.path.join(base, "看见余额")
    from kivy.app import App
    app = App.get_running_app()
    base = app.user_data_dir if app else os.getcwd()
    return os.path.join(base, "pictures")


def save_png(widget, prefix):
    """把某个控件画成 png，返回文件路径（失败返回 None）。"""
    d = pictures_dir()
    name = "%s-%s.png" % (prefix, datetime.now().strftime("%Y%m%d-%H%M%S"))
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        return None
    path = os.path.join(d, name)
    try:
        widget.export_to_png(path)
    except Exception:
        return None
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    return None
