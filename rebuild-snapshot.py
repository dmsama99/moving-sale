#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重建 site/index.html 里的 BAKED 快照。

数据来自线上 Google 表格，俏皮话来自 flavors.json（表格的 flavor 列不再是来源）。
快照只是「表格连不上时」的兜底，页面正常运行时读的是实时表格 + flavors.json。

    python3 rebuild-snapshot.py
"""
import io
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(HERE, "index.html")
FLAVORS = os.path.join(HERE, "flavors.json")

TRUTHY = {"TRUE", "1", "YES", "Y", "是", "已出", "售出", "SOLD", "X", "✓"}


def num(v):
    v = (v or "").replace("$", "").replace(",", "").strip()
    if not v:
        return None
    try:
        f = float(v)
    except ValueError:
        return None
    return int(f) if f == int(f) else f


def yes(v):
    return (v or "").strip().upper() in TRUTHY


def parse_csv(text):
    """和页面里的 parseCSV 同样的语义，避免两边对 CSV 的理解不一致。"""
    out, row, cur, q = [], [], "", False
    i = 0
    while i < len(text):
        c = text[i]
        if q:
            if c == '"':
                if i + 1 < len(text) and text[i + 1] == '"':
                    cur += '"'
                    i += 1
                else:
                    q = False
            else:
                cur += c
        elif c == '"':
            q = True
        elif c == ",":
            row.append(cur)
            cur = ""
        elif c == "\n":
            row.append(cur)
            out.append(row)
            row, cur = [], ""
        elif c != "\r":
            cur += c
        i += 1
    if cur or row:
        row.append(cur)
        out.append(row)
    return out


def main():
    src = io.open(HTML, encoding="utf-8").read()
    m = re.search(r"const CONFIG = \{.*?SHEET_CSV_URL:\s*\"([^\"]+)\"", src, re.S)
    if not m:
        sys.exit("在 index.html 里找不到 SHEET_CSV_URL")
    url = m.group(1)

    flavors = json.load(io.open(FLAVORS, encoding="utf-8"))
    old = json.loads(re.search(r"const BAKED = (\[.*?\]);\n", src, re.S).group(1))
    year = {b["id"]: b.get("year") for b in old if b.get("year")}

    with urllib.request.urlopen(url, timeout=30) as r:
        cells = parse_csv(r.read().decode("utf-8-sig"))
    head = [h.strip().lower() for h in cells[0]]
    rows = [dict(zip(head, r + [""] * len(head))) for r in cells[1:]]

    baked, ghosts, missing = [], 0, []
    for r in rows:
        iid = (r.get("id") or "").strip()
        if not iid:            # 拉过复选框的空行在 CSV 里是 "FALSE" 而不是空
            ghosts += 1
            continue
        total = num(r.get("total")) or 1
        rem_raw = (r.get("remaining") or "").strip()
        rem = total if rem_raw == "" else (num(rem_raw) or 0)
        o = {
            "id": iid,
            "name": (r.get("name") or "").strip(),
            "cat": (r.get("category") or "其他").strip(),
            "price": num(r.get("price")),
            "cost": num(r.get("cost")),
            "total": total,
            "remaining": 0 if yes(r.get("sold")) else max(0, min(total, rem)),
            "rot": num(r.get("rotate")) or 0,
            "note": (r.get("note") or "").strip(),
            "flavor": flavors.get(iid, ""),
            "link": (r.get("link") or "").strip(),
        }
        if yes(r.get("new")):
            o["isNew"] = True
        # 表格有 year 列就以表格为准，没有才用上一份快照里带下来的
        y = re.search(r"\d{4}", str(r.get("year") or ""))
        y = y.group(0) if y else year.get(iid)
        if y:
            o["year"] = y
        fit = (r.get("fit") or "").strip().lower()
        if fit:
            o["fit"] = fit
        if not o["flavor"]:
            missing.append("%s %s" % (iid, o["name"]))
        baked.append(o)

    line = ("const BAKED = [\n  "
            + ",\n  ".join(json.dumps(o, ensure_ascii=False) for o in baked)
            + "\n];\n")
    io.open(HTML, "w", encoding="utf-8").write(
        re.sub(r"const BAKED = \[.*?\];\n", lambda _: line, src, count=1, flags=re.S))

    size = os.path.getsize(HTML) / 1024
    print("快照重建完成：%d 件 / %d 个单位 / 已出 %d / 上新 %d"
          % (len(baked), sum(o["total"] for o in baked),
             sum(1 for o in baked if o["remaining"] == 0),
             sum(1 for o in baked if o.get("isNew"))))
    print("跳过幽灵行 %d，index.html %.1f KB" % (ghosts, size))
    orphan = sorted(set(flavors) - {o["id"] for o in baked})
    if missing:
        print("⚠ 缺俏皮话（去 flavors.json 补）：" + "、".join(missing))
    if orphan:
        print("⚠ flavors.json 里有表格中已不存在的 id：" + "、".join(orphan))
    if not missing and not orphan:
        print("✓ flavors.json 与表格一一对应")


if __name__ == "__main__":
    main()
