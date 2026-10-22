# -*- coding: utf-8 -*-
"""冒烟测试：把所有页面 / 面板各跑一遍，看有没有 Traceback。

用法：  .venv\\Scripts\\python tools\\smoke.py
每次都是「起窗口 -> 打开指定面板 -> 截图 -> 退出」，不报错就算过。
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")

CASES = [
    ("0", "", "统计页"),
    ("0", "report", "月报面板"),
    ("0", "note", "备注面板"),
    ("1", "", "罐子页"),
    ("1", "income", "存钱面板"),
    ("1", "expense", "花钱面板"),
    ("1", "settings", "设置面板"),
    ("1", "bg", "背景图选择"),
    ("1", "clear", "清空确认"),
    ("2", "", "心愿页"),
    ("2", "sort", "排序面板"),
]

BAD = ("Traceback", "IndexError", "NameError", "AttributeError", "KeyError")


def run(page, panel):
    env = dict(os.environ)
    env["SEED"] = "1"
    env["PAGE"] = page
    env["SHOT"] = "shot_smoke"
    if panel:
        env["PANEL"] = panel
    else:
        env.pop("PANEL", None)
    env.pop("DEBUG_TREE", None)
    p = subprocess.run([PY, "main.py"], cwd=ROOT, env=env,
                       capture_output=True, timeout=180)
    out = (p.stdout or b"").decode("utf-8", "replace") + \
          (p.stderr or b"").decode("utf-8", "replace")
    hits = [b for b in BAD if b in out]
    return hits, out


def main():
    fail = 0
    for page, panel, desc in CASES:
        try:
            hits, out = run(page, panel)
        except subprocess.TimeoutExpired:
            print("超时  %-10s %s" % (desc, panel))
            fail += 1
            continue
        if hits:
            fail += 1
            print("失败  %-10s %s -> %s" % (desc, panel or "-", ",".join(hits)))
            for ln in out.splitlines():
                if any(b in ln for b in BAD):
                    print("      " + ln.strip()[:160])
        else:
            print("通过  %-10s %s" % (desc, panel or "-"))
    print("\n共 %d 项，失败 %d 项" % (len(CASES), fail))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
