# -*- coding: utf-8 -*-
"""生成三页截图，并横向拼成一张总览图。

用法：  .venv\\Scripts\\python tools\\shots.py
产物：  preview_all.png（三页并排）、preview_jar / _stats / _wish.png
"""
import os
import subprocess
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")

PAGES = [("1", "jar", "储钱罐"), ("0", "stats", "统计"), ("2", "wish", "我想要的")]


def shoot(page, name):
    env = dict(os.environ)
    env["SEED"] = "1"
    env["PAGE"] = page
    env["SHOT"] = "preview_" + name
    env.pop("PANEL", None)
    env.pop("DEBUG_TREE", None)
    subprocess.run([PY, "main.py"], cwd=ROOT, env=env,
                   capture_output=True, timeout=180)
    p = os.path.join(ROOT, "preview_%s.png" % name)
    return p if os.path.exists(p) else None


def main():
    imgs = []
    for page, name, title in PAGES:
        p = shoot(page, name)
        if not p:
            print("缺少截图：%s" % name)
            continue
        imgs.append((title, Image.open(p).convert("RGB")))

    if not imgs:
        print("没有可用的截图")
        return 1

    # 统一高度后横向拼接，页与页之间留一条缝
    h = min(im.height for _, im in imgs)
    gap = 18
    scaled = [(t, im.resize((int(im.width * h / im.height), h), Image.LANCZOS))
              for t, im in imgs]
    total_w = sum(im.width for _, im in scaled) + gap * (len(scaled) - 1) + gap * 2
    canvas = Image.new("RGB", (total_w, h + gap * 2), (232, 230, 226))
    x = gap
    for _, im in scaled:
        canvas.paste(im, (x, gap))
        x += im.width + gap
    out = os.path.join(ROOT, "preview_all.png")
    canvas.save(out)
    print("ok %s  (%dx%d)" % (out, canvas.width, canvas.height))
    return 0


if __name__ == "__main__":
    sys.exit(main())
