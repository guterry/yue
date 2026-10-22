# -*- coding: utf-8 -*-
"""本地数据层（SQLite）+ 撤销/重做栈。

设计要点
- 金额一律以「分」为单位的整数存储，避免浮点误差。
- 所有写操作都走 self._record()，把「反向操作」压进撤销栈。
- 只存本地，不联网。
"""

import json
import os
import sqlite3
import time
from datetime import datetime

from .theme import BILLS, COINS

UNDO_LIMIT = 10


class Store:
    def __init__(self, db_path):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()
        self._undo = []
        self._redo = []

    # ------------------------------------------------------------ 建表
    def _create_tables(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tx (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                kind   TEXT    NOT NULL,           -- in / out
                amount INTEGER NOT NULL,           -- 分
                label  TEXT    NOT NULL DEFAULT '',
                note   TEXT    NOT NULL DEFAULT '',
                ts     INTEGER NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS wish (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                content  TEXT    NOT NULL,
                price    INTEGER NOT NULL,
                note     TEXT    NOT NULL DEFAULT '',
                ts       INTEGER NOT NULL,
                bought_ts INTEGER
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS setting (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT ''
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_ts ON tx(ts)")
        self.conn.commit()

    # ------------------------------------------------------------ 设置项
    def get_setting(self, key, default=""):
        row = self.conn.execute("SELECT value FROM setting WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key, value):
        self.conn.execute(
            "INSERT INTO setting(key, value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )
        self.conn.commit()

    # ------------------------------------------------------------ 撤销栈
    def _push(self, undo_fn, redo_fn):
        self._undo.append((undo_fn, redo_fn))
        if len(self._undo) > UNDO_LIMIT:
            self._undo.pop(0)
        self._redo.clear()

    def can_undo(self):
        return len(self._undo) > 0

    def can_redo(self):
        return len(self._redo) > 0

    def undo(self):
        if not self._undo:
            return False
        undo_fn, redo_fn = self._undo.pop()
        undo_fn()
        self._redo.append((undo_fn, redo_fn))
        return True

    def redo(self):
        if not self._redo:
            return False
        undo_fn, redo_fn = self._redo.pop()
        redo_fn()
        self._undo.append((undo_fn, redo_fn))
        return True

    # ------------------------------------------------------------ 读
    def balance(self):
        cur = self.conn.execute(
            "SELECT COALESCE(SUM(CASE WHEN kind='in' THEN amount ELSE -amount END),0) AS b FROM tx"
        )
        return int(cur.fetchone()["b"])

    def tx_list(self, month=None):
        """month: 'YYYY-MM'，None 表示全部。按时间倒序。"""
        rows = self.conn.execute("SELECT * FROM tx ORDER BY ts DESC, id DESC").fetchall()
        out = [dict(r) for r in rows]
        if month:
            out = [r for r in out if datetime.fromtimestamp(r["ts"]).strftime("%Y-%m") == month]
        return out

    def tx_group_by_label(self, month=None):
        res = {}
        for r in self.tx_list(month):
            if r["kind"] != "out":
                continue
            res[r["label"]] = res.get(r["label"], 0) + r["amount"]
        return res

    def month_sum(self, month, kind=None):
        """某月合计（分）。kind: None 全部 / 'in' / 'out'。"""
        total = 0
        for r in self.tx_list(month):
            if kind and r["kind"] != kind:
                continue
            total += r["amount"] if r["kind"] == "in" else -r["amount"]
        return total

    def month_top(self, month, kind="out"):
        """某月单笔最大的一笔，返回 dict 或 None。"""
        rows = [r for r in self.tx_list(month) if r["kind"] == kind]
        return max(rows, key=lambda r: r["amount"]) if rows else None

    def last_months(self, n=6, end_month=None):
        """返回最近 n 个月的年月字符串，从早到晚。"""
        if end_month:
            y, m = [int(x) for x in end_month.split("-")]
        else:
            d = datetime.now()
            y, m = d.year, d.month
        out = []
        for _ in range(n):
            out.append("%04d-%02d" % (y, m))
            m -= 1
            if m == 0:
                y, m = y - 1, 12
        return list(reversed(out))

    def months(self):
        """有数据的所有年月，倒序。"""
        seen = []
        for r in self.conn.execute("SELECT ts FROM tx ORDER BY ts DESC"):
            m = datetime.fromtimestamp(r["ts"]).strftime("%Y-%m")
            if m not in seen:
                seen.append(m)
        return seen

    def wishes(self, sort="time"):
        order = "price DESC, ts DESC" if sort == "price" else "ts DESC"
        rows = self.conn.execute(
            "SELECT * FROM wish WHERE bought_ts IS NULL ORDER BY %s" % order
        ).fetchall()
        return [dict(r) for r in rows]

    def wish_total(self):
        cur = self.conn.execute(
            "SELECT COALESCE(SUM(price),0) AS t FROM wish WHERE bought_ts IS NULL"
        )
        return int(cur.fetchone()["t"])

    # ------------------------------------------------------------ 写：流水
    def add_tx(self, kind, amount, label, note=""):
        ts = int(time.time())
        cur = self.conn.execute(
            "INSERT INTO tx(kind, amount, label, note, ts) VALUES(?,?,?,?,?)",
            (kind, int(amount), label or "", note or "", ts),
        )
        self.conn.commit()
        new_id = cur.lastrowid

        def undo():
            self.conn.execute("DELETE FROM tx WHERE id=?", (new_id,))
            self.conn.commit()

        def redo():
            self.conn.execute(
                "INSERT INTO tx(id, kind, amount, label, note, ts) VALUES(?,?,?,?,?,?)",
                (new_id, kind, int(amount), label or "", note or "", ts),
            )
            self.conn.commit()

        self._push(undo, redo)
        return new_id

    def delete_tx(self, tx_id):
        row = self.conn.execute("SELECT * FROM tx WHERE id=?", (tx_id,)).fetchone()
        if not row:
            return False
        row = dict(row)
        self.conn.execute("DELETE FROM tx WHERE id=?", (tx_id,))
        self.conn.commit()

        def undo():
            self.conn.execute(
                "INSERT INTO tx(id, kind, amount, label, note, ts) VALUES(?,?,?,?,?,?)",
                (row["id"], row["kind"], row["amount"], row["label"], row["note"], row["ts"]),
            )
            self.conn.commit()

        def redo():
            self.conn.execute("DELETE FROM tx WHERE id=?", (row["id"],))
            self.conn.commit()

        self._push(undo, redo)
        return True

    def set_tx_note(self, tx_id, note):
        row = self.conn.execute("SELECT note FROM tx WHERE id=?", (tx_id,)).fetchone()
        if not row:
            return False
        old = row["note"]
        self.conn.execute("UPDATE tx SET note=? WHERE id=?", (note or "", tx_id))
        self.conn.commit()

        def make(v):
            def fn():
                self.conn.execute("UPDATE tx SET note=? WHERE id=?", (v, tx_id))
                self.conn.commit()
            return fn

        self._push(make(old), make(note or ""))
        return True

    # ------------------------------------------------------------ 写：心愿
    def add_wish(self, content, price, note=""):
        ts = int(time.time())
        cur = self.conn.execute(
            "INSERT INTO wish(content, price, note, ts) VALUES(?,?,?,?)",
            (content, int(price), note or "", ts),
        )
        self.conn.commit()
        new_id = cur.lastrowid

        def undo():
            self.conn.execute("DELETE FROM wish WHERE id=?", (new_id,))
            self.conn.commit()

        def redo():
            self.conn.execute(
                "INSERT INTO wish(id, content, price, note, ts) VALUES(?,?,?,?,?)",
                (new_id, content, int(price), note or "", ts),
            )
            self.conn.commit()

        self._push(undo, redo)
        return new_id

    def delete_wish(self, wish_id):
        row = self.conn.execute("SELECT * FROM wish WHERE id=?", (wish_id,)).fetchone()
        if not row:
            return False
        row = dict(row)
        self.conn.execute("DELETE FROM wish WHERE id=?", (wish_id,))
        self.conn.commit()

        def undo():
            self.conn.execute(
                "INSERT INTO wish(id, content, price, note, ts, bought_ts) VALUES(?,?,?,?,?,?)",
                (row["id"], row["content"], row["price"], row["note"], row["ts"], row["bought_ts"]),
            )
            self.conn.commit()

        def redo():
            self.conn.execute("DELETE FROM wish WHERE id=?", (row["id"],))
            self.conn.commit()

        self._push(undo, redo)
        return True

    def set_wish_note(self, wish_id, note):
        row = self.conn.execute("SELECT note FROM wish WHERE id=?", (wish_id,)).fetchone()
        if not row:
            return False
        old = row["note"]
        self.conn.execute("UPDATE wish SET note=? WHERE id=?", (note or "", wish_id))
        self.conn.commit()

        def make(v):
            def fn():
                self.conn.execute("UPDATE wish SET note=? WHERE id=?", (v, wish_id))
                self.conn.commit()
            return fn

        self._push(make(old), make(note or ""))
        return True

    def buy_wish(self, wish_id):
        row = self.conn.execute("SELECT * FROM wish WHERE id=?", (wish_id,)).fetchone()
        if not row or row["bought_ts"]:
            return False
        wish = dict(row)
        ts = int(time.time())
        cur = self.conn.execute(
            "INSERT INTO tx(kind, amount, label, note, ts) VALUES('out', ?, '心愿', ?, ?)",
            (wish["price"], wish["content"], ts),
        )
        tx_id = cur.lastrowid
        self.conn.execute("UPDATE wish SET bought_ts=? WHERE id=?", (ts, wish_id))
        self.conn.commit()

        def undo():
            self.conn.execute("DELETE FROM tx WHERE id=?", (tx_id,))
            self.conn.execute("UPDATE wish SET bought_ts=NULL WHERE id=?", (wish_id,))
            self.conn.commit()

        def redo():
            self.conn.execute(
                "INSERT INTO tx(id, kind, amount, label, note, ts) VALUES(?, 'out', ?, '心愿', ?, ?)",
                (tx_id, wish["price"], wish["content"], ts),
            )
            self.conn.execute("UPDATE wish SET bought_ts=? WHERE id=?", (ts, wish_id))
            self.conn.commit()

        self._push(undo, redo)
        return True

    # ------------------------------------------------------------ 设置
    def clear_all(self):
        self.conn.execute("DELETE FROM tx")
        self.conn.execute("DELETE FROM wish")
        self.conn.commit()
        self._undo.clear()
        self._redo.clear()

    def export_json(self, path):
        data = {
            "tx": [dict(r) for r in self.conn.execute("SELECT * FROM tx ORDER BY ts")],
            "wish": [dict(r) for r in self.conn.execute("SELECT * FROM wish ORDER BY ts")],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path

    def import_json(self, path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.conn.execute("DELETE FROM tx")
        self.conn.execute("DELETE FROM wish")
        for r in data.get("tx", []):
            self.conn.execute(
                "INSERT INTO tx(id, kind, amount, label, note, ts) VALUES(?,?,?,?,?,?)",
                (r["id"], r["kind"], r["amount"], r["label"], r["note"], r["ts"]),
            )
        for r in data.get("wish", []):
            self.conn.execute(
                "INSERT INTO wish(id, content, price, note, ts, bought_ts) VALUES(?,?,?,?,?,?)",
                (r["id"], r["content"], r["price"], r["note"], r["ts"], r.get("bought_ts")),
            )
        self.conn.commit()
        self._undo.clear()
        self._redo.clear()
        return True


# ---------------------------------------------------------------- 辅助

def parse_amount(text):
    """'12.5' -> 1250（分）。非法返回 None。"""
    if text is None:
        return None
    s = str(text).strip().replace("，", "").replace(",", "").replace("￥", "").replace("¥", "")
    if not s:
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    if v <= 0 or v > 99_999_999:
        return None
    return int(round(v * 100))


def split_cash(amount):
    """把金额拆成钞票/硬币列表。返回 [(kind, denom), ...]，从下往上（大额在下）。

    kind: 'bill' / 'coin'
    """
    out = []
    left = int(amount)
    for denom, _name, _rgb, _mm in BILLS:
        while left >= denom:
            out.append(("bill", denom))
            left -= denom
    for denom, _name, _rgb in COINS:
        while left >= denom:
            out.append(("coin", denom))
            left -= denom
    return out


def fmt_money(cents, with_sign=False):
    """12345 -> '123.45'；整数时省略小数。"""
    neg = cents < 0
    cents = abs(int(cents))
    yuan = cents // 100
    jiao = cents % 100
    s = "{:,}".format(yuan)
    if jiao:
        s += "." + ("%02d" % jiao).rstrip("0")
    if with_sign and neg:
        s = "-" + s
    return s


def fmt_ts(ts):
    return datetime.fromtimestamp(ts).strftime("%m月%d日 %H:%M")
