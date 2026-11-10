#!/usr/bin/env python3
"""阿陞版「每戶成交實價」：手機看圖頁＋靜態圖產生器。

2026-11-04 林津陞定案（第三階段）＋同日重新設計（舊版一張長圖、每 5 欄切段、字太小，林津陞退件）：
- 每格寫「成交年月＋成交單價（萬元/坪）」，不寫幾房。同一戶多筆只畫最新一筆，標「共N筆」。
  （「網頁不寫金額」的例外，只限這張圖。）
- 口徑照樂居均價口徑（單價扣除車位坪數與價格；只借口徑，樣式不照抄）：全部用途都列；一樓、地下層照畫但不進色階、
  不跟住宅樓層混比；原始資料有拆分車位價與車位面積的才扣，沒拆分的標「含車位」，也不進色階與中位數。
- 新版版面：
  1. 摘要在最上面：成交單價中位數（近一年／全部，二樓以上、不含含車位、每戶只算最新一筆）、範圍、戶數、筆數、最新成交年月、公布截止日。
  2. 以「棟」分組：data/doors 的國土測繪中心門牌座標＋簡報 window.SITE 的本社區建物輪廓（me=1），把門牌歸到所在建物；
     成交門牌不在定位清單時用同主號的已定位門牌判斷；有任一戶歸不到棟（多棟社區）就整個社區一張表，不亂分。
  3. 每棟只畫該棟實際樓層（實價登錄總樓層數）；連續 2 層以上沒有成交收成一條細列（看圖頁可展開）。
  4. 成交格用單價色階（品牌藍青單色相、淺→深 5 階，亮度單調，色盲也分得出深淺）；可切換依成交年上色（中性灰單色相）。
     2026-11-10 個人品牌改版：原總站紅色階改為藍青色階（林津陞：所有網站不再用紅色當主色）。
  5. 門牌在上、樓層在左；同一個門牌的「樓之N」欄並排在門牌底下。
- 配色、版面是本站自己的（品牌深藍 #0369A1／點綴青 #06B6D4、系統字型、白底、淡藍灰邊），不參考、不照抄任何其他網站的銷控表。
- 「夾層」是禁用詞：跨層一律寫「跨層」。不寫屋齡數字。
- 內容沒變就不改檔（夜間同步重跑不產生 diff）。

用法：python3 scripts/unit_grid.py [repo根目錄] [社區名 ...]（不給社區名＝data/units 下全部 .json）
輸出：
  data/units/view.html                 手機優先看圖頁（view.html?n=<社區名>）
  data/units/<社區名>.grid.json        看圖頁讀的資料（分棟、樓層、摘要、色階都算好）
  data/units/<社區名>.svg              靜態圖（社群／列印用，同一套設計）
"""
import html
import json
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import door_layout as DL  # noqa: E402  （同資料夾：讀簡報 SITE 建物輪廓、門牌座標換算）

BRAND = "#0369A1"; BRAND_INK = "#075985"; CYAN = "#06B6D4"; INK = "#0F2233"; GREY = "#4C5E6E"; LINE = "#D7E6EF"
FILL_EMPTY = "#F6F7F8"     # 沒有成交：幾乎白
FILL_GROUND = "#FFFFFF"    # 一樓／店面：白底＋金褐細框＋「1F」標（不進色階）
EDGE_GROUND = "#A4762A"
FILL_BASE = "#FFFFFF"      # 地下層：白底＋灰藍細框（不進色階）
EDGE_BASE = "#5D7B91"
EDGE_INCL = "#8A969E"      # 含車位：白底＋灰虛線框（不進色階）
# 單價色階（品牌藍青單色相，淺→深；後兩階白字）。亮度單調遞增，色盲也分得出深淺。
PRICE_RAMP = ["#E4F4FA", "#A5DBEA", "#5BBAD8", "#0B7FB5", "#0B4A73"]
# 成交年色階（中性灰單色相，舊→新由淺到深；跟單價藍色階分開）
YEAR_RAMP = ["#E9ECEF", "#D3D8DE", "#B4BCC6", "#8E98A5", "#5F6B7A", "#3A4552"]
DARK_TEXT_FROM = 3         # 色階第幾階起用白字
FONT = "Noto Sans TC, Microsoft JhengHei, PingFang TC, sans-serif"
MAX_COLS = 5               # （舊版分段用；新版不分段，保留常數給舊呼叫者）
USE_SHORT = {"住家用": "", "住商用": "住商", "辦公用": "辦公", "商業用": "商業", "工業用": "工業"}
DISCLOSURE = "全國不動產板橋加盟店｜經紀業 非凡不動產有限公司｜經紀人 謝政峯（99）北縣字第002181號｜營業員 林津陞（99）登字第148103號"
LINE_URL = "https://line.me/R/ti/p/%40banqiao.asheng"
TEL = "0925635678"


# ───────────── 門牌與欄 ─────────────
def door_no(addr):
    m = re.search(r"(\d+)(?:之(\d+))?號", addr or "")
    return (int(m.group(1)), m.group(2)) if m else (None, None)


def door_key(addr):
    """門牌欄的鍵：(主號, 之N)。「309之5號」「309之6號」是不同門牌（健華新城 309之1～之38 號），不可併成一欄。"""
    d, sub = door_no(addr)
    return (d, int(sub) if sub else 0) if d is not None else None


def key_of_no(no):
    m = re.fullmatch(r"(\d+)(?:之(\d+))?", str(no))
    return (int(m.group(1)), int(m.group(2) or 0)) if m else None


def door_prefix(addr):
    """「文化路一段309之5號」→「文化路一段」（巷弄留著）。"""
    m = re.search(r"\d+(?:之\d+)?號$", addr or "")
    return addr[:m.start()] if m else ""


def suffix_no(s):
    m = re.match(r"之(\d+)$", s or "")
    return int(m.group(1)) if m else 0


def door_text(k):
    return ("%d之%d號" % k) if k[1] else ("%d號" % k[0])


def columns(units, door_nos=()):
    """欄＝(門牌鍵, 樓層後的之N)。另外併入 data/doors 的門牌（沒成交的留空欄、不跳號）；
    但某主號的成交是「N號 X樓之M」寫法時（新巨蛋 360號 10樓之3），同主號的「N之M號」定位門牌不另開空欄，免得跟「樓之M」混淆。"""
    cols = {(door_key(u["addr"]), suffix_no(u.get("suffix"))) for u in units if door_key(u["addr"])}
    have = {c[0] for c in cols}
    floor_suffix_mains = {c[0][0] for c in cols if c[0][1] == 0 and c[1]}
    for no in door_nos:
        k = key_of_no(no)
        if k and k not in have and not (k[1] and k[0] in floor_suffix_mains):
            cols.add((k, 0))
    return sorted(cols)


def segments(cols, max_cols=MAX_COLS):
    """（舊版相容）欄位分段：同一個門牌的欄盡量放同一段。新版看圖頁不分段。"""
    groups = []
    for c in cols:
        if groups and groups[-1][0][0] == c[0]:
            groups[-1].append(c)
        else:
            groups.append([c])
    segs, cur = [], []
    for g in groups:
        while len(g) > max_cols:
            if cur:
                segs.append(cur); cur = []
            segs.append(g[:max_cols]); g = g[max_cols:]
        if len(cur) + len(g) > max_cols:
            segs.append(cur); cur = []
        cur = cur + g
    if cur:
        segs.append(cur)
    return segs


def floor_label(f):
    return ("B%d" % -f) if f < 0 else ("%dF" % f)


def tags_of(u):
    t = []
    if u.get("parking") == "included":
        t.append("含車位")
    short = USE_SHORT.get(u.get("use"), u.get("use") or "")
    if short:
        t.append(short)
    if u.get("span"):
        t.append("跨層")
    if (u.get("n") or 1) > 1:
        t.append("共%d筆" % u["n"])
    return t


def season_text(s):
    m = re.fullmatch(r"(\d+)S(\d)", s or "")
    return "民國%s年第%s季" % (m.group(1), m.group(2)) if m else ""


def notes_of(data):
    period = (data.get("period") or "").split("～")
    start = season_text(period[0]) if period and period[0] else ""
    cutoff = data.get("cutoff") or ""
    return [
        "資料來源：內政部不動產交易實價查詢服務網（已排除特殊交易），不含預售屋（完工前簽約者）。",
        "資料期間：%s起登錄的成交，%s；之後的新成交未納入，以內政部最新資料為準。" % (start or "實價登錄", cutoff or "依內政部公布"),
        "單價（萬元/坪）已扣除有拆分的車位；標「含車位」者未拆分，單價含車位，不列入色階與中位數。",
        "同一戶（門牌＋樓層＋之幾）有多筆成交只畫最新一筆，「共N筆」是該戶在資料期間內的成交筆數。",
        "中位數只算二樓以上、每戶最新一筆；一樓／店面、地下層另外標示，不與住宅樓層混比。淡灰格是資料期間內沒有成交登錄，不代表沒有住戶。",
        "不依實際比例重繪，實際以現場及權狀為準。",
    ]


# ───────────── 分棟 ─────────────
def load_buildings(root, name):
    """回傳 (本社區建物 [{name, poly}], 已定位門牌 [(門牌字, (x, y))])；沒有簡報或門牌就回空。"""
    deck = os.path.join(root, "community", name, "index.html")
    site = DL.load_site(deck) if os.path.exists(deck) else None
    me = [b for b in (site or {}).get("blds", []) if b.get("me")]
    blds = [{"name": (b.get("n") or "").replace(name, "").strip(), "poly": b["p"]} for b in me]
    doors = DL.doors_local(os.path.join(root, "data", "doors", name + ".json"), (None, None)) if blds else []
    return blds, doors


def assign_buildings(unit_keys, blds, doors):
    """門牌鍵 → 建物索引。回傳 ({門牌鍵: 索引}, 已定位但沒在 unit_keys 的門牌 {門牌鍵: 索引}, 是否全部歸得到)。"""
    if len(blds) <= 1:
        located = {}
        for no, _ in doors:
            k = key_of_no(no)
            if k:
                located[k] = 0
        return {k: 0 for k in unit_keys}, located, True
    located = {}
    for no, q in doors:
        k = key_of_no(no)
        if not k:
            continue
        dists = [DL.dist_to_poly(q, b["poly"]) for b in blds]
        i = min(range(len(blds)), key=lambda j: dists[j])
        if dists[i] <= 8:
            located[k] = i
    out, ok = {}, True
    for k in unit_keys:
        if k in located:
            out[k] = located[k]
            continue
        cand = {i for kk, i in located.items() if kk[0] == k[0]}
        if len(cand) == 1:
            out[k] = cand.pop()
        else:
            ok = False
    return out, located, ok


def door_range(keys, prefix=""):
    keys = sorted(set(keys))
    if not keys:
        return ""
    if len(keys) == 1:
        return prefix + door_text(keys[0])
    mains = {k[0] for k in keys}
    if len(mains) == 1:
        subs = [k[1] for k in keys]
        if subs[0] == 0:
            return prefix + "%d～%d之%d號" % (keys[0][0], keys[0][0], subs[-1])
        return prefix + "%d之%d～之%d號" % (keys[0][0], subs[0], subs[-1])
    return prefix + "%s～%s" % (door_text(keys[0])[:-1], door_text(keys[-1]))


# ───────────── 摘要與色階 ─────────────
def comparable(u):
    """可以互相比較的單價：二樓以上、不是含車位未拆分。"""
    return u["floor"] >= 2 and u.get("parking") != "included" and isinstance(u.get("price"), (int, float))


def ym_num(ym):
    m = re.fullmatch(r"(\d+)/(\d+)", ym or "")
    return int(m.group(1)) * 12 + int(m.group(2)) - 1 if m else None


def num_ym(n):
    return "%d/%02d" % (n // 12, n % 12 + 1)


def med(xs):
    return round(statistics.median(xs), 1) if xs else None


def price_bins(prices):
    """色階分界：二樓以上單價的 20/40/60/80 百分位，取整數、遞增不重複。回傳分界 list（長度 0～4）。"""
    xs = sorted(prices)
    if len(xs) < 2:
        return []
    cuts = []
    for q in (0.2, 0.4, 0.6, 0.8):
        v = xs[min(len(xs) - 1, int(round(q * (len(xs) - 1))))]
        c = int(round(v))
        if c > xs[0] and c <= xs[-1] and (not cuts or c > cuts[-1]):
            cuts.append(c)
    return cuts


def bin_of(p, cuts):
    return sum(1 for c in cuts if p >= c)


def ramp_for(cuts):
    """分界 k 個 → 用 k+1 階；從色階兩端平均取，保證最淺、最深都有。"""
    n = len(cuts) + 1
    if n == 1:
        return [PRICE_RAMP[2]]
    return [PRICE_RAMP[round(i * (len(PRICE_RAMP) - 1) / (n - 1))] for i in range(n)]


def year_ramp(years):
    n = len(years)
    if n == 1:
        return [YEAR_RAMP[-2]]
    return [YEAR_RAMP[round(i * (len(YEAR_RAMP) - 1) / (n - 1))] for i in range(n)]


def summary_of(units, data):
    comp = [u for u in units if comparable(u)]
    pt = re.fullmatch(r"(\d+)/(\d+)/\d+", data.get("published_through") or "")
    yms = [ym_num(u["ym"]) for u in units if ym_num(u["ym"]) is not None]
    end = (int(pt.group(1)) * 12 + int(pt.group(2)) - 1) if pt else (max(yms) if yms else 0)
    since = end - 12
    recent = [u["price"] for u in comp if (ym_num(u["ym"]) or 0) >= since]
    allp = [u["price"] for u in comp]
    return {
        "units": len(units), "deals": sum(u.get("n") or 1 for u in units),
        "latest": num_ym(max(yms)) if yms else "",
        "recent_since": num_ym(since), "recent_n": len(recent),
        "recent_all": sum(1 for u in units if (ym_num(u["ym"]) or 0) >= since), "recent_median": med(recent) if len(recent) >= 3 else None,
        "all_n": len(allp), "all_median": med(allp) if len(allp) >= 3 else None,
        "min": min(allp) if allp else None, "max": max(allp) if allp else None,
        "ground": sum(1 for u in units if u["floor"] == 1), "base": sum(1 for u in units if u["floor"] < 0),
        "included": sum(1 for u in units if u.get("parking") == "included"),
    }


# ───────────── 模型 ─────────────
def build_model(name, data, door_nos=(), blds=(), located_doors=()):
    """看圖頁與靜態圖共用的資料：分棟、欄、樓層、格子、摘要、色階。沒有可畫的回 None。"""
    units = [u for u in data.get("units") or [] if door_key(u.get("addr")) and isinstance(u.get("floor"), int)]
    if not units:
        return None
    units.sort(key=lambda u: (door_key(u["addr"]), suffix_no(u.get("suffix")), -u["floor"]))
    prefix = door_prefix(units[0]["addr"])
    top_all = max([data.get("floors") or 0] + [u["floor"] for u in units])
    dfl = {door_key(a): n for a, n in (data.get("door_floors") or {}).items() if door_key(a) and isinstance(n, int)}
    unit_keys = sorted({door_key(u["addr"]) for u in units})
    blds = list(blds)
    amap, located, ok = assign_buildings(unit_keys, blds, list(located_doors)) if blds else ({}, {}, False)
    grouped = bool(blds) and ok and len({amap[k] for k in unit_keys}) > 1
    extra_nos = list(door_nos)
    groups = []
    if grouped:
        idxs = sorted({amap[k] for k in unit_keys} | set(located.values()),
                      key=lambda i: min([k for k, j in list(amap.items()) + list(located.items()) if j == i]))
        named = all(blds[i]["name"] for i in idxs)
        for i in idxs:
            gkeys = [k for k in unit_keys if amap[k] == i]
            gextra = [door_text(k)[:-1] for k, j in located.items() if j == i]
            gunits = [u for u in units if door_key(u["addr"]) in gkeys]
            groups.append((blds[i]["name"] if named else "", gunits, gextra))
        groups = [g for g in groups if g[1]]   # 沒有任何成交的建物不畫（例：只有門牌定位）
    else:
        groups = [("", units, extra_nos)]
    summ = summary_of(units, data)
    cuts = price_bins([u["price"] for u in units if comparable(u)])
    years = sorted({int(u["ym"].split("/")[0]) for u in units})
    out_units, out_groups = [], []
    for gname, gunits, gextra in groups:
        cols = columns(gunits, gextra)
        col_index = {c: j for j, c in enumerate(cols)}
        keys = [c[0] for c in cols]
        top = max([dfl.get(k) or 0 for k in keys] + [u["floor"] for u in gunits]) or top_all
        if not any(dfl.get(k) for k in keys):
            top = max(top, top_all)
        bmin = min([u["floor"] for u in gunits if u["floor"] < 0] or [0])
        floors = list(range(top, 0, -1)) + list(range(-1, bmin - 1, -1))
        cells = {}
        for u in gunits:
            j = col_index[(door_key(u["addr"]), suffix_no(u.get("suffix")))]
            uid = len(out_units)
            out_units.append({
                "addr": u["addr"], "f": u["floor"], "s": suffix_no(u.get("suffix")), "ym": u["ym"], "p": u["price"],
                "k": u.get("parking") or "none", "use": u.get("use") or "", "n": u.get("n") or 1, "span": 1 if u.get("span") else 0,
                "c": 1 if comparable(u) else 0,
            })
            cells["%d,%d" % (j, u["floor"])] = uid
        # 欄頭：門牌一列（同門牌合併）、樓之N 一列
        heads = []
        for (k, s) in cols:
            if heads and heads[-1]["k"] == list(k):
                heads[-1]["span"] += 1
            else:
                heads.append({"k": list(k), "t": door_text(k) if not k[1] else "%d之%d" % k, "span": 1})   # 欄頭窄：「148之1」不寫「號」
        if len(heads) > 1 and len({h["k"][0] for h in heads}) == 1 and all(h["k"][1] for h in heads):
            for h in heads:
                h["h"] = "之%d" % h["k"][1]   # 健華新城：同棟都是 309之N 號，欄頭只寫「之N」，主號寫在棟名下
        comp = [u["price"] for u in gunits if comparable(u)]
        out_groups.append({
            "title": gname or (door_range(keys) if grouped else ""),
            "doors": door_range(keys, prefix),
            "top": top, "floors": floors,
            "cols": [{"k": list(k), "s": s, "t": ("樓之%d" % s) if s else "樓", "empty": not any(
                (door_key(u["addr"]), suffix_no(u.get("suffix"))) == (k, s) for u in gunits)} for (k, s) in cols],
            "heads": heads, "sub_row": any(s for _, s in cols),
            "cells": cells, "n": len(gunits), "median": med(comp) if len(comp) >= 3 else None, "comp_n": len(comp),
        })
    return {
        "name": name, "prefix": prefix, "grouped": grouped, "buildings_known": len(blds),
        "period": data.get("period") or "", "period_text": "～".join(season_text(p) or p for p in (data.get("period") or "").split("～")),
        "cutoff": data.get("cutoff") or "", "published_through": data.get("published_through") or "",
        "summary": summ, "cuts": cuts, "ramp": ramp_for(cuts), "years": years, "year_ramp": year_ramp(years),
        "dark_from": DARK_TEXT_FROM, "notes": notes_of(data), "groups": out_groups, "units": out_units,
    }


def collapse_rows(group, cells_floors):
    """樓層列：連續 2 層以上沒有成交收成一列 ("gap", 高, 低)；其他 ("f", 樓層)。"""
    rows, run = [], []

    def flush():
        if len(run) >= 2:
            rows.append(("gap", run[0], run[-1]))
        else:
            rows.extend(("f", f) for f in run)
        run.clear()
    for f in group["floors"]:
        if f in cells_floors:
            flush()
            rows.append(("f", f))
        else:
            run.append(f)
    flush()
    return rows


# ───────────── 靜態 SVG（社群／列印） ─────────────
def text_width(s, size):
    return sum(size * (0.56 if ord(ch) < 0x2E80 else 1.0) for ch in s)


def wrap(s, size, width):
    lines, cur = [], ""
    for ch in s:
        if text_width(cur + ch, size) > width and cur and ch not in "，。；：、）」』":
            lines.append(cur); cur = ""
        cur += ch
    if cur:
        lines.append(cur)
    return lines


def cell_style(u, model, mode="price"):
    """回傳 (底色, 框色, 虛線, 字色, 標籤)。"""
    if u["f"] == 1:
        return FILL_GROUND, EDGE_GROUND, "", INK, "1F"
    if u["f"] < 0:
        return FILL_BASE, EDGE_BASE, "", INK, floor_label(u["f"])
    if mode == "price" and u["k"] == "included":
        return "#FFFFFF", EDGE_INCL, "3 2", GREY, ""
    if mode == "price":
        b = bin_of(u["p"], model["cuts"])
        ramp = model["ramp"]
    else:
        b = model["years"].index(int(u["ym"].split("/")[0]))
        ramp = model["year_ramp"]
    fill = ramp[b]
    dark = PRICE_RAMP.index(fill) >= DARK_TEXT_FROM if fill in PRICE_RAMP else YEAR_RAMP.index(fill) >= 4
    return fill, fill, "", "#FFFFFF" if dark else INK, ""


def unit_tags(u):
    t = []
    if u["k"] == "included":
        t.append("含車位")
    s = USE_SHORT.get(u["use"], u["use"])
    if s:
        t.append(s)
    if u["span"]:
        t.append("跨層")
    if u["n"] > 1:
        t.append("共%d筆" % u["n"])
    return t


def render(name, data, door_nos=(), blds=(), located_doors=()):
    """回傳靜態 SVG 字串；沒有可畫的就回 None。"""
    model = build_model(name, data, door_nos, blds, located_doors)
    if not model:
        return None
    return render_svg(model)


def render_svg(model):
    e = html.escape
    CW, CH, GH, LEFT, PAD, GAPX = 66, 50, 20, 44, 24, 28
    U = model["units"]
    # 先算每棟表格大小，再依寬度排成幾列（shelf packing）
    blocks = []
    for g in model["groups"]:
        fl = {U[uid]["f"] for uid in g["cells"].values()}
        rows = collapse_rows(g, fl)
        w = LEFT + len(g["cols"]) * CW
        h = 46 + 26 + (24 if g["sub_row"] else 0) + sum(CH if r[0] == "f" else GH for r in rows)
        blocks.append((g, rows, w, h))
    W = max(1080, max(b[2] for b in blocks) + 2 * PAD)
    inner = W - 2 * PAD
    body = []
    y = 0
    body.append('<defs><linearGradient id="band" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient></defs>' % (BRAND, CYAN))
    body.append('<rect x="0" y="0" width="%d" height="6" fill="url(#band)"/>' % W)
    body.append('<rect x="0" y="6" width="%d" height="30" fill="#F6FBFD"/>' % W)
    body.append('<text x="%d" y="26" font-size="13" fill="%s">%s</text>' % (PAD, GREY, e(DISCLOSURE)))
    y = 80
    body.append('<text x="%d" y="%d" font-size="30" font-weight="700" fill="%s">%s 每戶成交實價</text>' % (PAD, y, INK, e(model["name"])))
    y += 30
    body.append('<text x="%d" y="%d" font-size="15" fill="%s">門牌在上、樓層在左；每格是該戶最新一筆成交：上為單價（萬元/坪），下為成交年月。%s</text>' % (
        PAD, y, GREY, e(model["cutoff"])))
    # 摘要卡
    s = model["summary"]
    y += 24
    cards = []
    if s["recent_median"] is not None:
        cards.append(("近一年成交單價中位數", "%.1f" % s["recent_median"], "萬/坪", "%s 起・%d 戶" % (s["recent_since"], s["recent_n"])))
    if s["all_median"] is not None:
        cards.append(("全部期間中位數", "%.1f" % s["all_median"], "萬/坪", "範圍 %.1f～%.1f・%d 戶" % (s["min"], s["max"], s["all_n"])))
    cards.append(("有成交的戶數", "%d" % s["units"], "戶", "資料期間內共 %d 筆成交" % s["deals"]))
    cards.append(("最新一筆成交", s["latest"], "", model["cutoff"]))
    cw = (inner - 12 * (len(cards) - 1)) / len(cards)
    for i, (lab, big, unit, sub) in enumerate(cards):
        x = PAD + i * (cw + 12)
        body.append('<rect x="%.1f" y="%d" width="%.1f" height="96" rx="10" fill="#FFFFFF" stroke="%s"/>' % (x, y, cw, LINE))
        body.append('<text x="%.1f" y="%d" font-size="14" fill="%s">%s</text>' % (x + 16, y + 26, GREY, e(lab)))
        body.append('<text x="%.1f" y="%d" font-size="32" font-weight="700" fill="%s">%s<tspan font-size="15" font-weight="400" fill="%s"> %s</tspan></text>' % (
            x + 16, y + 64, BRAND_INK if i == 0 else INK, e(big), GREY, e(unit)))
        body.append('<text x="%.1f" y="%d" font-size="13" fill="%s">%s</text>' % (x + 16, y + 86, GREY, e(sub)))
    y += 96 + 34
    # 圖例
    lx = PAD
    body.append('<text x="%d" y="%d" font-size="14" font-weight="700" fill="%s">單價色階（萬/坪）</text>' % (lx, y, INK))
    lx += 130
    cuts, ramp = model["cuts"], model["ramp"]
    for i, col in enumerate(ramp):
        lo = cuts[i - 1] if i > 0 else None
        hi = cuts[i] if i < len(cuts) else None
        lab = ("%d 以下" % hi if lo is None and hi is not None else "%d 以上" % lo if hi is None and lo is not None
               else "%d～%d" % (lo, hi) if lo is not None else "全部")
        if lo is None and hi is not None:
            lab = "未滿 %d" % hi
        body.append('<rect x="%d" y="%d" width="22" height="16" rx="3" fill="%s"/>' % (lx, y - 13, col))
        body.append('<text x="%d" y="%d" font-size="13" fill="%s">%s</text>' % (lx + 27, y, INK, e(lab)))
        lx += 27 + int(text_width(lab, 13)) + 16
    for fill, edge, dash, lab in ((FILL_GROUND, EDGE_GROUND, "", "一樓／店面"), ("#FFFFFF", EDGE_INCL, "3 2", "含車位（不比較）"),
                                  (FILL_EMPTY, FILL_EMPTY, "", "無成交")):
        body.append('<rect x="%d" y="%d" width="22" height="16" rx="3" fill="%s" stroke="%s"%s/>' % (
            lx, y - 13, fill, edge, (' stroke-dasharray="%s"' % dash) if dash else ""))
        body.append('<text x="%d" y="%d" font-size="13" fill="%s">%s</text>' % (lx + 27, y, INK, e(lab)))
        lx += 27 + int(text_width(lab, 13)) + 16
    y += 24
    # 棟別表格
    x, shelf_h = PAD, 0
    for g, rows, w, h in blocks:
        if x > PAD and x + w > PAD + inner:
            x = PAD; y += shelf_h + 24; shelf_h = 0
        body.extend(svg_block(g, rows, x, y, model, CW, CH, GH, LEFT))
        x += w + GAPX
        shelf_h = max(shelf_h, h)
    y += shelf_h + 30
    # 註記
    for t in model["notes"]:
        for j, line in enumerate(wrap("・" + t, 14, inner)):
            body.append('<text x="%d" y="%d" font-size="14" fill="%s">%s</text>' % (PAD + (14 if j else 0), y, INK, e(line)))
            y += 21
    y += 8
    body.append('<text x="%d" y="%d" font-size="14" font-weight="700" fill="%s">板橋阿陞聊房 banqiaoasheng.com｜LINE @banqiao.asheng｜手機 0925-635-678</text>' % (PAD, y, BRAND_INK))
    y += 22
    H = int(y)
    head = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" preserveAspectRatio="xMidYMin meet" '
            'style="width:100%%;height:auto;max-width:%dpx" font-family="%s">' % (W, H, W, FONT))
    return "\n".join([head, '<rect width="100%" height="100%" fill="#FFFFFF"/>'] + body + ["</svg>"]) + "\n"


def svg_block(g, rows, x0, y0, model, CW, CH, GH, LEFT):
    e = html.escape
    U = model["units"]
    o = []
    title = g["title"] or g["doors"]
    o.append('<text x="%d" y="%d" font-size="19" font-weight="700" fill="%s">%s</text>' % (x0, y0 + 22, INK, e(title)))
    named = g["title"] and not re.match(r"\d", g["title"])
    sub = (g["doors"] + "・" if named or not g["title"] else "") + "%d 戶有成交" % g["n"] + ("・中位數 %.1f 萬/坪" % g["median"] if g["median"] is not None else "")
    o.append('<text x="%d" y="%d" font-size="13" fill="%s">%s</text>' % (x0, y0 + 40, GREY, e(sub)))
    y = y0 + 46
    # 門牌列
    cx = x0 + LEFT
    for hd in g["heads"]:
        w = hd["span"] * CW
        o.append('<rect x="%d" y="%d" width="%d" height="24" fill="#F1F3F4"/>' % (cx + 1, y, w - 2))
        o.append('<text x="%d" y="%d" font-size="14" font-weight="700" fill="%s" text-anchor="middle">%s</text>' % (cx + w / 2, y + 17, INK, e(hd.get("h") or hd["t"])))
        cx += w
    y += 26
    if g["sub_row"]:
        for j, c in enumerate(g["cols"]):
            o.append('<text x="%d" y="%d" font-size="13" fill="%s" text-anchor="middle">%s</text>' % (x0 + LEFT + j * CW + CW / 2, y + 15, GREY, e(c["t"])))
        y += 24
    for r in rows:
        if r[0] == "gap":
            lab = ("%d–%dF" % (r[2], r[1])) if r[2] > 0 else "%s–%s" % (floor_label(r[2]), floor_label(r[1]))
            o.append('<rect x="%d" y="%d" width="%d" height="%d" fill="#FAFAFB"/>' % (x0 + LEFT + 2, y + 3, len(g["cols"]) * CW - 4, GH - 6))
            o.append('<text x="%d" y="%d" font-size="11" fill="%s" text-anchor="end">%s</text>' % (x0 + LEFT - 6, y + 14, GREY, e(lab)))
            o.append('<text x="%d" y="%d" font-size="11" fill="#9AA5AC">無成交</text>' % (x0 + LEFT + 8, y + 14))
            y += GH
            continue
        f = r[1]
        o.append('<text x="%d" y="%d" font-size="14" font-weight="700" fill="%s" text-anchor="end">%s</text>' % (
            x0 + LEFT - 6, y + CH / 2 + 5, GREY, floor_label(f)))
        for j in range(len(g["cols"])):
            if f > g["top"]:
                continue
            uid = g["cells"].get("%d,%d" % (j, f))
            cx = x0 + LEFT + j * CW
            if uid is None:
                o.append('<rect x="%d" y="%d" width="%d" height="%d" rx="4" fill="%s"/>' % (cx + 2, y + 2, CW - 4, CH - 4, FILL_EMPTY))
                continue
            u = U[uid]
            fill, edge, dash, ink, badge = cell_style(u, model)
            o.append('<rect x="%d" y="%d" width="%d" height="%d" rx="4" fill="%s" stroke="%s" stroke-width="1.3"%s/>' % (
                cx + 2, y + 2, CW - 4, CH - 4, fill, edge, (' stroke-dasharray="%s"' % dash) if dash else ""))
            o.append('<text x="%d" y="%d" font-size="17" font-weight="700" fill="%s" text-anchor="middle">%.1f</text>' % (cx + CW / 2, y + 22, ink, u["p"]))
            o.append('<text x="%d" y="%d" font-size="12" fill="%s" text-anchor="middle">%s</text>' % (cx + CW / 2, y + 36, ink, e(u["ym"])))
            tags = unit_tags(u)
            if tags:
                t = tags[0] + ("+" if len(tags) > 1 else "")
                o.append('<text x="%d" y="%d" font-size="10.5" fill="%s" text-anchor="middle">%s</text>' % (cx + CW / 2, y + 46, ink, e(t)))
        y += CH
    return o


# ───────────── 看圖頁 ─────────────
VIEW_HTML = r"""<!doctype html>
<html lang="zh-Hant-TW"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<meta name="color-scheme" content="light">
<title>每戶成交實價｜板橋阿陞聊房</title>
<style>
:root{--brand:#0369A1;--brand-ink:#075985;--ink:#0F2233;--muted:#4C5E6E;--line:#D7E6EF;--bg:#FFFFFF;--soft:#F6FBFD;--card:#FFFFFF}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--ink);font-family:"Noto Sans TC","Microsoft JhengHei","PingFang TC",system-ui,sans-serif;-webkit-text-size-adjust:100%;line-height:1.55}
a{color:var(--brand-ink)}
.top{display:flex;align-items:center;gap:10px;padding:8px 16px;border-bottom:1px solid var(--line);background:#fff;border-top:3px solid var(--brand);border-image:linear-gradient(90deg,#0369A1,#06B6D4) 1 0 0 0}
.brand{display:flex;align-items:center;gap:10px;text-decoration:none;color:var(--ink);min-width:0}
.brand img{height:34px;width:auto;display:block}
.top .sp{flex:1}
.btn-line{display:inline-flex;align-items:center;min-height:44px;padding:0 16px;border-radius:22px;background:#06893E;color:#fff;text-decoration:none;font-weight:700;font-size:15px;white-space:nowrap}
.disc{background:#F6FBFD;color:#4C5E6E;border-bottom:1px solid var(--line);font-size:12.5px;line-height:1.6;padding:4px 16px}
main{max-width:1240px;margin:0 auto;padding:16px 16px 40px}
.crumb{font-size:14px;margin:0 0 6px}.crumb a{text-decoration:none}
h1{font-size:24px;line-height:1.3;margin:0 0 4px}
.lead{color:var(--muted);font-size:15px;margin:0 0 14px}
.sum{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,2fr);gap:10px;margin:0 0 8px}
.stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.card{border:1px solid var(--line);border-radius:12px;padding:12px 14px;background:var(--card)}
.card .l{font-size:13.5px;color:var(--muted)}
.card .v{font-size:28px;font-weight:800;line-height:1.2;margin-top:2px;font-variant-numeric:tabular-nums}
.card .v small{font-size:14px;font-weight:400;color:var(--muted);margin-left:3px}
.card .s{font-size:13px;color:var(--muted);margin-top:2px}
.card.hero{position:relative;overflow:hidden}
.card.hero::before{content:"";position:absolute;left:0;right:0;top:0;height:3px;background:linear-gradient(90deg,#0369A1,#06B6D4)}
.card.hero .v{color:var(--brand-ink)}
.basis{font-size:13px;color:var(--muted);margin:0 0 16px}
.bar{position:sticky;top:0;z-index:30;background:#fff;border-bottom:1px solid var(--line);margin:0 -16px 10px;padding:8px 16px}
.chips{display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;padding-bottom:2px}
.chips::-webkit-scrollbar{display:none}
.chip{flex:0 0 auto;min-height:40px;padding:0 14px;border-radius:20px;border:1px solid #D4D9DD;background:#fff;color:var(--ink);font-size:15px;font-family:inherit;cursor:pointer}
.chip[aria-pressed="true"]{background:var(--ink);border-color:var(--ink);color:#fff;font-weight:700}
.opts{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;margin:6px 0 8px}
.seg{display:inline-flex;border:1px solid #D4D9DD;border-radius:10px;overflow:hidden}
.seg button{min-height:40px;padding:0 10px;border:0;background:#fff;font-size:14.5px;font-family:inherit;color:var(--ink);cursor:pointer}
.seg button[aria-pressed="true"]{background:var(--brand);color:#fff;font-weight:700}
.tog{display:inline-flex;align-items:center;gap:6px;font-size:14.5px;min-height:38px;cursor:pointer}
.tog input{width:18px;height:18px;accent-color:var(--brand)}
.legend{display:flex;flex-wrap:wrap;gap:6px 12px;align-items:center;font-size:13.5px;margin:4px 0 14px}
.legend .t{font-weight:700}
.sw{display:inline-flex;align-items:center;gap:5px;white-space:nowrap}
.sw i{display:inline-block;width:22px;height:16px;border-radius:4px}
.sw i.em{background:#fff;box-shadow:inset 0 0 0 1px #E3E6E8}
.groups{display:flex;flex-wrap:wrap;gap:22px 28px;align-items:flex-start}
.g{min-width:0;max-width:100%}
.g h2{font-size:19px;margin:0;line-height:1.3}
.g .gs{font-size:13.5px;color:var(--muted);margin:2px 0 8px}
.g .gs b{color:var(--ink)}
.scroll{overflow:auto;max-height:78vh;max-width:100%;width:fit-content;border:1px solid var(--line);border-radius:10px;-webkit-overflow-scrolling:touch;overscroll-behavior-x:contain}
table{border-collapse:separate;border-spacing:0;font-variant-numeric:tabular-nums}
th,td{padding:0}
thead th{position:sticky;background:#F1F3F4;color:var(--ink);font-size:14px;font-weight:700;z-index:2;white-space:nowrap;text-align:center;border-bottom:1px solid var(--line)}
thead tr.r1 th{top:0;height:32px;border-left:1px solid #fff}
thead tr.r1 th.dh{text-align:left}
thead tr.r1 th.dh span{position:sticky;left:64px;padding:0 10px}
.hint{font-size:13px;color:var(--muted);margin:0 0 6px}
thead tr.r2 th{top:32px;height:26px;font-size:13px;font-weight:400;color:var(--muted);background:#F7F8F9}
th.fl{position:sticky;left:0;z-index:3;background:#fff;color:var(--muted);font-size:14px;font-weight:700;width:56px;min-width:56px;text-align:right;padding-right:8px;border-right:1px solid var(--line);white-space:nowrap}
thead th.fl{z-index:4;background:#F1F3F4;font-weight:400;font-size:13px}
td{width:66px;min-width:66px;height:62px;border-right:1px solid #F0F2F3;border-bottom:1px solid #F0F2F3}
td>.c{display:flex;flex-direction:column;align-items:center;justify-content:center;margin:2px;height:57px;border-radius:6px;text-align:center;line-height:1.15;cursor:pointer;border:0;width:calc(100% - 4px);font-family:inherit;padding:0}
td>.e{display:block}
.c .p{font-size:17px;font-weight:800}
.c .y{font-size:13px;margin-top:2px}
.c .tg{font-size:12px;margin-top:1px;font-weight:700;opacity:.9}
.c.gr{background:#fff;box-shadow:inset 0 0 0 1.5px #A4762A;color:var(--ink)}
.c.bs{background:#fff;box-shadow:inset 0 0 0 1.5px #5D7B91;color:var(--ink)}
.c.inc{background:#fff;box-shadow:inset 0 0 0 1.5px #AEB7BD;color:#4A565E}
.c.inc .p{font-weight:700}
.c:focus-visible{outline:3px solid #1F6FEB;outline-offset:1px}
tr.gap th.fl{font-size:13px;font-weight:400;height:26px;color:#8A969E;background:#FAFBFB}
tr.gap td{height:26px;background:#FAFBFB;border-right:0}
tr.gap td.gl{font-size:13px;color:#8A969E;padding-left:8px;white-space:nowrap;text-align:left}
td.no{background:#fff}
.notes{margin-top:28px;border-top:1px solid var(--line);padding-top:14px;font-size:14px;line-height:1.75}
.notes ul{margin:0;padding-left:20px}
.notes li{margin:2px 0}
.foot{margin-top:18px;font-size:13.5px;color:var(--muted);line-height:1.8}
.foot b{color:var(--ink)}
.dock{display:none;position:fixed;left:0;right:0;bottom:0;z-index:50;gap:8px;padding:8px 12px calc(8px + env(safe-area-inset-bottom));background:#fff;border-top:1px solid var(--line)}
.dock a{flex:1;display:flex;align-items:center;justify-content:center;min-height:46px;border-radius:12px;text-decoration:none;font-weight:700;font-size:16px}
.dock .dl{background:#06893E;color:#fff}.dock .dt{border:1.5px solid var(--brand);color:var(--brand-ink)}
.sheet{position:fixed;left:0;right:0;bottom:0;z-index:60;background:#fff;border-radius:16px 16px 0 0;box-shadow:0 -6px 24px rgba(0,0,0,.18);padding:16px 18px calc(18px + env(safe-area-inset-bottom));max-width:560px;margin:0 auto;transform:translateY(110%);transition:transform .18s ease}
.sheet{visibility:hidden}
.sheet.on{transform:none;visibility:visible}
.sheet h3{margin:0 0 4px;font-size:18px}
.sheet .big{font-size:30px;font-weight:800;color:var(--brand-ink)}
.sheet .big small{font-size:15px;color:var(--muted);font-weight:400}
.sheet dl{display:grid;grid-template-columns:auto 1fr;gap:4px 14px;margin:10px 0 0;font-size:15px}
.sheet dt{color:var(--muted)}.sheet dd{margin:0}
.sheet .x{position:absolute;right:10px;top:8px;min-width:44px;min-height:44px;border:0;background:none;font-size:24px;color:var(--muted);cursor:pointer}
.msg{padding:40px 0;font-size:16px}
@media (max-width:760px){
  .dock{display:flex}
  .top .btn-line{display:none}
  main{padding-bottom:110px}
  h1{font-size:21px}
  .sum{grid-template-columns:1fr;gap:8px}
  .stats{gap:8px}
  .stats .card .v{font-size:21px}
  .card{padding:10px 12px}
  .card .v{font-size:24px}
  .disc{font-size:12.5px}
  .brand img{height:28px}
  .groups{display:block}
  .g{margin-bottom:24px}
  .scroll{max-height:72vh}
  td{width:60px;min-width:60px}
  .c .p{font-size:16px}
}
@media print{.bar,.dock,.sheet,.top .btn-line{display:none}.scroll{max-height:none;overflow:visible}}
</style></head>
<body>
<header class="top"><a class="brand" href="../../"><img src="../../assets/brand/logo_wide.png" alt="板橋阿陞聊房" width="880" height="189"></a><span class="sp"></span>
<a class="btn-line" href="https://line.me/R/ti/p/%40banqiao.asheng" target="_blank" rel="noopener">加 LINE</a></header>
<div class="disc">全國不動產板橋加盟店｜經紀業 非凡不動產有限公司｜經紀人 謝政峯（99）北縣字第002181號｜營業員 林津陞（99）登字第148103號</div>
<main id="app"><p class="msg">讀取中…</p></main>
<div class="sheet" id="sheet" role="dialog" aria-modal="false" aria-labelledby="sh-t"><button class="x" type="button" aria-label="關閉">×</button><div id="sheet-b"></div></div>
<nav class="dock" aria-label="聯絡阿陞"><a class="dl" href="https://line.me/R/ti/p/%40banqiao.asheng" target="_blank" rel="noopener">加 LINE 問阿陞</a><a class="dt" href="tel:0925635678">☎ 0925-635-678</a></nav>
<script>
(function(){
var app=document.getElementById('app'),sheet=document.getElementById('sheet'),sb=document.getElementById('sheet-b');
var n=new URLSearchParams(location.search).get('n')||'';
function esc(s){return String(s).replace(/[&<>"']/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
function fail(){app.innerHTML='<p class="msg">找不到這個社區的成交資料。<a href="../../map/">回商圈地圖</a></p>'}
if(!n||/[\/\\.]/.test(n)){fail();return}
document.title=n+' 每戶成交實價｜板橋阿陞聊房';
var st={b:-1,mode:'price',all:false};
try{var sv=JSON.parse(localStorage.getItem('units-view')||'{}');if(sv.mode==='year')st.mode='year';if(sv.all)st.all=true}catch(e){}
function save(){try{localStorage.setItem('units-view',JSON.stringify({mode:st.mode,all:st.all}))}catch(e){}}
fetch(encodeURIComponent(n)+'.grid.json',{cache:'no-cache'}).then(function(r){if(!r.ok)throw 0;return r.json()}).then(draw).catch(fail);
var USE={'住家用':'','住商用':'住商','辦公用':'辦公','商業用':'商業','工業用':'工業'};
function fl(f){return f<0?'B'+(-f):f+'F'}
function rng(a,b){return a>0&&b>0?b+'–'+a+'F':fl(b)+'–'+fl(a)}
function f1(x){return (Math.round(x*10)/10).toFixed(1)}
function tags(u){var t=[];if(u.k==='included')t.push('含車位');var s=USE.hasOwnProperty(u.use)?USE[u.use]:u.use;if(s)t.push(s);if(u.span)t.push('跨層');if(u.n>1)t.push('共'+u.n+'筆');return t}
function draw(M){
  var S=M.summary,h='';
  h+='<p class="crumb"><a href="../../map/">← 商圈地圖</a>'+(M.layout?'　<a href="../layout/view.html?n='+encodeURIComponent(M.name)+'">看棟別配置圖</a>':'')+'</p>';
  h+='<h1>'+esc(M.name)+' 每戶成交實價</h1>';
  h+='<p class="lead">每格＝一戶最新一筆成交：單價（萬/坪）＋成交年月，點格子看細節。資料'+esc(M.cutoff)+'。</p>';
  var hero=S.recent_median!=null?['近一年成交單價中位數',S.recent_median,S.recent_since+' 起成交 '+S.recent_n+' 戶'+(S.all_median!=null?'・全部期間 '+f1(S.all_median):'')]
    :S.all_median!=null?['成交單價中位數（全部期間）',S.all_median,S.all_n+' 戶・範圍 '+f1(S.min)+'～'+f1(S.max)]:null;
  h+='<div class="sum">';
  if(hero)h+=card('hero',hero[0],f1(hero[1]),'萬/坪',hero[2]);
  else h+=card('hero','成交單價','—','','二樓以上可比較的成交不到 3 戶，不計中位數');
  h+='<div class="stats">'+card('','有成交',''+S.units,'戶','共 '+S.deals+' 筆')+card('','近一年',''+S.recent_all,'戶',S.recent_since+' 起')+card('','最新成交',S.latest,'','成交年月')+'</div></div>';
  h+='<p class="basis">中位數只算二樓以上、不含「含車位」，每戶只算最新一筆。資料期間 '+esc(M.period_text)+'。</p>';
  if(M.groups.length>1){h+='<div class="bar"><div class="chips" role="group" aria-label="選棟"><button class="chip" data-b="-1">全部 '+M.groups.length+' 棟</button>';
    M.groups.forEach(function(g,i){h+='<button class="chip" data-b="'+i+'">'+esc(g.title)+'</button>'});h+='</div></div>'}
  h+='<div class="opts"><span class="seg" role="group" aria-label="上色方式"><button data-m="price">依單價上色</button><button data-m="year">依年份上色</button></span>';
  h+='<label class="tog"><input type="checkbox" id="all">展開全部樓層</label></div>';
  h+='<div class="legend" id="lg"></div><div class="groups" id="gs"></div>';
  h+='<section class="notes"><ul>'+M.notes.map(function(t){return '<li>'+esc(t)+'</li>'}).join('')+'</ul>';
  h+='<div class="foot"><b>板橋阿陞聊房・林津陞</b>　LINE <a href="https://line.me/R/ti/p/%40banqiao.asheng" target="_blank" rel="noopener">@banqiao.asheng</a>・手機 <a href="tel:0925635678">0925-635-678</a><br>全國不動產板橋加盟店｜經紀業 非凡不動產有限公司｜經紀人 謝政峯（99）北縣字第002181號｜營業員 林津陞（99）登字第148103號<br>© 林津陞　板橋阿陞聊房</div></section>';
  app.innerHTML=h;
  app.querySelectorAll('.chip').forEach(function(b){b.onclick=function(){st.b=+b.dataset.b;render(M)}});
  app.querySelectorAll('.seg button').forEach(function(b){b.onclick=function(){st.mode=b.dataset.m;save();render(M)}});
  var al=document.getElementById('all');al.checked=st.all;al.onchange=function(){st.all=al.checked;save();render(M)};
  app.addEventListener('click',function(ev){var c=ev.target.closest('.c');if(c)show(M,+c.dataset.u)});
  render(M);
}
function card(cls,l,v,u,s){return '<div class="card '+cls+'"><div class="l">'+esc(l)+'</div><div class="v">'+esc(v)+(u?'<small>'+esc(u)+'</small>':'')+'</div><div class="s">'+esc(s)+'</div></div>'}
function binOf(p,c){var b=0;for(var i=0;i<c.length;i++)if(p>=c[i])b++;return b}
function style(M,u){
  if(u.f===1)return{cls:'gr',bg:'',fg:''};
  if(u.f<0)return{cls:'bs',bg:'',fg:''};
  if(st.mode==='price'&&u.k==='included')return{cls:'inc',bg:'',fg:''};
  var i,ramp;
  if(st.mode==='price'){i=binOf(u.p,M.cuts);ramp=M.ramp;var dark=['#0B7FB5','#0B4A73'].indexOf(ramp[i])>=0}
  else{i=M.years.indexOf(+u.ym.split('/')[0]);ramp=M.year_ramp;var dark=['#5F6B7A','#3A4552'].indexOf(ramp[i])>=0}
  return{cls:'',bg:ramp[i],fg:dark?'#FFFFFF':'#0F2233'}
}
function legend(M){
  var h='';
  if(st.mode==='price'){h+='<span class="t">單價（萬/坪）</span>';
    M.ramp.forEach(function(c,i){var lo=i?M.cuts[i-1]:null,hi=i<M.cuts.length?M.cuts[i]:null;
      var l=lo==null&&hi!=null?'未滿 '+hi:hi==null&&lo!=null?lo+' 以上':lo!=null?lo+'～'+hi:'全部';
      h+='<span class="sw"><i style="background:'+c+'"></i>'+l+'</span>'});
    h+='<span class="sw"><i style="background:#fff;box-shadow:inset 0 0 0 1.5px #8A969E"></i>含車位（不比較）</span>'}
  else{h+='<span class="t">成交年（民國）</span>';M.years.forEach(function(y,i){h+='<span class="sw"><i style="background:'+M.year_ramp[i]+'"></i>'+y+'</span>'})}
  h+='<span class="sw"><i style="background:#fff;box-shadow:inset 0 0 0 1.5px #A4762A"></i>一樓／店面</span>';
  if(M.summary.base)h+='<span class="sw"><i style="background:#fff;box-shadow:inset 0 0 0 1.5px #5D7B91"></i>地下層</span>';
  h+='<span class="sw"><i class="em"></i>無成交</span>';
  return h}
function rowsOf(g,has){
  var rows=[],run=[];
  function flush(){if(run.length>=2&&!st.all)rows.push({gap:[run[0],run[run.length-1]]});else run.forEach(function(f){rows.push({f:f})});run=[]}
  g.floors.forEach(function(f){if(has[f]){flush();rows.push({f:f})}else run.push(f)});flush();return rows}
function table(M,g){
  var has={};Object.keys(g.cells).forEach(function(k){has[+k.split(',')[1]]=1});
  var nc=g.cols.length,one=g.heads.length===1,h='<div class="scroll" data-n="'+nc+'"><table><thead>';
  if(one){h+='<tr class="r1"><th class="fl">樓層</th>';g.cols.forEach(function(c){h+='<th>'+esc(c.t)+'</th>'});h+='</tr>'}
  else{h+='<tr class="r1"><th class="fl" rowspan="'+(g.sub_row?2:1)+'">樓層</th>';
    g.heads.forEach(function(d){h+='<th colspan="'+d.span+'"'+(d.span>1?' class="dh"':'')+'><span>'+esc(d.h||d.t)+'</span></th>'});h+='</tr>';
    if(g.sub_row){h+='<tr class="r2">';g.cols.forEach(function(c){h+='<th>'+esc(c.t)+'</th>'});h+='</tr>'}}
  h+='</thead><tbody>';
  rowsOf(g,has).forEach(function(r){
    if(r.gap){h+='<tr class="gap"><th class="fl">'+rng(r.gap[0],r.gap[1])+'</th><td class="gl" colspan="'+nc+'">'+(r.gap[0]-r.gap[1]+1)+' 層沒有成交</td></tr>';return}
    h+='<tr><th class="fl">'+fl(r.f)+'</th>';
    for(var j=0;j<nc;j++){var uid=g.cells[j+','+r.f];
      if(uid==null){h+='<td><span class="e"></span></td>';continue}
      var u=M.units[uid],s=style(M,u),t=tags(u),tg=t.length?t[0]+(t.length>1?'+':''):(u.f===1?'1F':'');
      if(u.f===1&&t.length)tg=t[0]+(t.length>1?'+':'');
      h+='<td><button type="button" class="c '+s.cls+'" data-u="'+uid+'"'+(s.bg?' style="background:'+s.bg+';color:'+s.fg+'"':'')+' aria-label="'+esc(fl(u.f)+' '+f1(u.p)+' 萬每坪 '+u.ym)+'"><span class="p">'+f1(u.p)+'</span><span class="y">'+esc(u.ym)+'</span>'+(tg?'<span class="tg">'+esc(tg)+'</span>':'')+'</button></td>'}
    h+='</tr>'});
  return h+'</tbody></table></div>'}
function render(M){
  app.querySelectorAll('.chip').forEach(function(b){b.setAttribute('aria-pressed',+b.dataset.b===st.b?'true':'false')});
  app.querySelectorAll('.seg button').forEach(function(b){b.setAttribute('aria-pressed',b.dataset.m===st.mode?'true':'false')});
  document.getElementById('lg').innerHTML=legend(M);
  var h='';
  M.groups.forEach(function(g,i){if(st.b>=0&&st.b!==i)return;
    h+='<section class="g">';
    if(M.groups.length>1)h+='<h2>'+esc(g.title||g.doors)+'</h2>';
    h+='<p class="gs">'+esc(g.doors)+'・'+'<b>'+g.n+'</b> 戶有成交'+(g.median!=null?'・中位數 <b>'+f1(g.median)+'</b> 萬/坪':'')+'</p>';
    h+=table(M,g)+'</section>'});
  var gs=document.getElementById('gs');gs.innerHTML=h;
  gs.querySelectorAll('.scroll').forEach(function(sc){if(sc.scrollWidth>sc.clientWidth+4){var p=document.createElement('p');p.className='hint';p.textContent='表格較寬，左右滑動可看全部 '+sc.dataset.n+' 欄 →';sc.parentNode.insertBefore(p,sc)}});
}
function show(M,uid){
  var u=M.units[uid];if(!u)return;
  var park=u.k==='included'?'含車位（未拆分，單價含車位）':u.k==='split'?'有車位，單價已扣除車位':'無車位';
  var h='<h3 id="sh-t">'+esc(u.addr.replace(M.prefix,''))+' '+(u.f<0?'地下'+(-u.f)+'樓':u.f+'樓')+(u.s?'之'+u.s:'')+(u.span?'（跨層）':'')+'</h3>';
  h+='<div class="big">'+f1(u.p)+' <small>萬/坪</small></div><dl>';
  h+='<dt>成交年月</dt><dd>'+esc(u.ym)+'</dd><dt>車位</dt><dd>'+park+'</dd><dt>用途</dt><dd>'+esc(u.use||'—')+'</dd>';
  h+='<dt>這戶筆數</dt><dd>'+(u.n>1?'資料期間內 '+u.n+' 筆，這裡是最新一筆':'1 筆')+'</dd>';
  if(u.f===1)h+='<dt>注意</dt><dd>一樓／店面，不跟樓上住宅比</dd>';
  if(u.f<0)h+='<dt>注意</dt><dd>地下層，不跟樓上住宅比</dd>';
  h+='</dl>';sb.innerHTML=h;sheet.classList.add('on')}
sheet.querySelector('.x').onclick=function(){sheet.classList.remove('on')};
document.addEventListener('keydown',function(e){if(e.key==='Escape')sheet.classList.remove('on')});
document.addEventListener('click',function(e){if(sheet.classList.contains('on')&&!sheet.contains(e.target)&&!e.target.closest('.c'))sheet.classList.remove('on')});
})();
</script></body></html>
"""


# ───────────── 輸出 ─────────────
def write_if_changed(path, text):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            if fh.read() == text:
                return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return True


def door_numbers(root, name):
    p = os.path.join(root, "data", "doors", name + ".json")
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as fh:
        doors = json.load(fh).get("doors") or []
    return [d["no"] for d in doors if re.fullmatch(r"\d+(?:之\d+)?", d.get("no", ""))]


def build_one(root, name):
    """回傳 (model, svg)；沒有可畫的回 (None, None)。"""
    with open(os.path.join(root, "data", "units", name + ".json"), encoding="utf-8") as fh:
        data = json.load(fh)
    blds, located = load_buildings(root, name)
    model = build_model(name, data, door_numbers(root, name), blds, located)
    if not model:
        return None, None
    model["layout"] = os.path.exists(os.path.join(root, "data", "layout", name + ".svg"))
    return model, render_svg(model)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    argv = sys.argv[1:] if argv is None else argv
    root = argv[0] if argv else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    udir = os.path.join(root, "data", "units")
    names = argv[1:] or sorted(f[:-5] for f in os.listdir(udir)
                               if f.endswith(".json") and not f.endswith(".grid.json") and f != "index.json")
    changed = 0
    if write_if_changed(os.path.join(udir, "view.html"), VIEW_HTML):
        changed += 1
        print("view.html changed")
    for name in names:
        if not os.path.exists(os.path.join(udir, name + ".json")):
            print(name, "skip（沒有 data/units 資料）")
            continue
        model, svg = build_one(root, name)
        if not model:
            print(name, "skip（沒有可畫的成交）")
            continue
        js = json.dumps(model, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
        c = write_if_changed(os.path.join(udir, name + ".grid.json"), js)
        c = write_if_changed(os.path.join(udir, name + ".svg"), svg) or c
        changed += c
        print(name, "changed" if c else "same")
    # 地圖資料卡「看每戶成交實價」只對有格子圖的社區顯示（2026-11-04 林津陞核可上線）
    have = sorted(f[:-10] for f in os.listdir(udir) if f.endswith(".grid.json"))
    idx = json.dumps({"units": have}, ensure_ascii=False, indent=1) + "\n"
    if write_if_changed(os.path.join(udir, "index.json"), idx):
        changed += 1
        print("index.json changed")
    print("unit_grid: %d 個檔有變動" % changed)


if __name__ == "__main__":
    main()
