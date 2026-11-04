#!/usr/bin/env python3
"""阿陞版「樓層 × 門牌」戶別格子圖（大樓版的棟別比對）。

資料只用政府公開的實價登錄（社區簡報內嵌的 deals，或 data/units/<社區名>.json 的完整欄位）。
不依實際比例幾何重繪；不顯示任何金額、單價。

data/units/<社區名>.json（選用，property-deck 匯出，欄位越完整圖越準）：
  {"units":[{"addr":"莊敬路203號","floor":11,"suffix":"之3","rooms":2,"main_ping":10.2,"area_ping":14.67,"parking":false}]}
沒有這個檔時，退回用簡報內嵌 deals（只有門牌、樓層、移轉面積、車位類別）。

用法：python3 scripts/unit_grid.py [repo根目錄] 社區名 [...]
輸出：data/units/<社區名>.svg
"""
import json, os, re, sys, html

RED = "#C8161D"; INK = "#1F2B33"; GREY = "#8A969E"
CN = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def cn_floor(s):
    if isinstance(s, int):
        return s
    s = (s or "").replace("層", "").replace("樓", "")
    if s.isdigit():
        return int(s)
    if s.startswith("十"):
        return 10 + CN.get(s[1:2], 0)
    m = re.match(r"([一二三四五六七八九])十([一二三四五六七八九]?)", s)
    if m:
        return CN[m.group(1)] * 10 + (CN.get(m.group(2), 0))
    return CN.get(s)


def load_deck(path):
    s = open(path, encoding="utf-8").read()
    i = s.find('"deals":[')
    deals = json.JSONDecoder().raw_decode(s[i + 8:])[0] if i >= 0 else []
    j = s.find('"floors":')
    floors = int(re.match(r'"floors":(\d+)', s[j:]).group(1)) if j >= 0 else None
    return deals, floors


def door_no(addr):
    m = re.search(r"(\d+)(?:之(\d+))?號", addr or "")
    return (int(m.group(1)), m.group(2)) if m else (None, None)


BUCKETS = [(0, 20, "#E9C46A", "20 坪以下"), (20, 30, "#7FB3A8", "20～30 坪"),
           (30, 40, "#5B8DB8", "30～40 坪"), (40, 999, "#6D5BA8", "40 坪以上")]


def color(v):
    for lo, hi, c, _ in BUCKETS:
        if lo <= v < hi:
            return c
    return "#CCCCCC"


def render(name, units, floors, out):
    doors = sorted({u["door"] for u in units if u["door"]})
    if not doors or not floors:
        return False
    # 門牌欄：取實際出現過的門牌，依號碼排序
    cw, ch = 52, 30
    left, top = 70, 130
    W = max(760, left + cw * len(doors) + 40)
    H = top + ch * floors + 170
    e = html.escape
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" font-family="Noto Sans TC, Microsoft JhengHei, PingFang TC, sans-serif">' % (W, H, W, H),
         '<rect width="100%" height="100%" fill="#FFFFFF"/><rect width="100%" height="8" fill="{}"/>'.format(RED),
         '<text x="40" y="56" font-size="28" font-weight="700" fill="{}">{}</text>'.format(INK, e(name)),
         '<text x="40" y="88" font-size="17" fill="{}">各門牌 × 樓層 實價登錄成交戶（不依實際比例重繪）</text>'.format(GREY)]
    grid = {}
    for u in units:
        if u["door"] and u["floor"]:
            grid.setdefault((u["door"], u["floor"]), []).append(u)
    for k, d in enumerate(doors):
        x = left + k * cw
        o.append('<text x="%d" y="%d" font-size="13" font-weight="700" fill="%s" text-anchor="middle">%d號</text>' % (x + cw / 2, top - 10, INK, d))
    for f in range(floors, 0, -1):
        y = top + (floors - f) * ch
        o.append('<text x="%d" y="%d" font-size="13" fill="%s" text-anchor="end">%dF</text>' % (left - 8, y + ch / 2 + 5, GREY, f))
        for k, d in enumerate(doors):
            x = left + k * cw
            us = grid.get((d, f))
            if us:
                u = us[0]
                v = u.get("main_ping") or u.get("area_ping") or 0
                o.append('<rect x="%d" y="%d" width="%d" height="%d" rx="3" fill="%s" stroke="#FFFFFF" stroke-width="2"/>' % (x, y, cw, ch, color(v)))
                lab = ("%d房" % u["rooms"]) if u.get("rooms") else ("%.0f坪" % v)
                if len(us) > 1:
                    lab += "×%d" % len(us)
                o.append('<text x="%d" y="%d" font-size="12" font-weight="700" fill="#FFFFFF" text-anchor="middle">%s</text>' % (x + cw / 2, y + ch / 2 + 4, e(lab)))
                if u.get("parking"):
                    o.append('<circle cx="%d" cy="%d" r="3.5" fill="#FFFFFF"/>' % (x + cw - 7, y + 7))
            else:
                o.append('<rect x="%d" y="%d" width="%d" height="%d" rx="3" fill="#F1F3F4" stroke="#FFFFFF" stroke-width="2"/>' % (x, y, cw, ch))
    ly = top + floors * ch + 34
    lx = 40
    for lo, hi, c, t in BUCKETS:
        o.append('<rect x="%d" y="%d" width="18" height="18" rx="3" fill="%s"/><text x="%d" y="%d" font-size="15" fill="%s">%s</text>' % (lx, ly - 14, c, lx + 26, ly, INK, t))
        lx += 140
    o.append('<circle cx="%d" cy="%d" r="5" fill="%s"/><text x="%d" y="%d" font-size="15" fill="%s">含車位成交</text>' % (lx + 8, ly - 5, GREY, lx + 20, ly, INK))
    basis = "主建物面積" if any(u.get("main_ping") for u in units) else "建物移轉面積（含車位者面積含車位）"
    notes = ["顏色依%s；灰格為資料期間內沒有成交登錄的戶，不代表沒有住戶。" % basis,
             "資料來源：內政部不動產交易實價查詢服務網（已排除特殊交易）；不顯示金額。不依實際比例重繪，實際以現場及權狀為準。"]
    for k, t in enumerate(notes):
        o.append('<text x="40" y="%d" font-size="14" fill="%s">%s</text>' % (ly + 36 + k * 24, INK, e(t)))
    o.append("</svg>")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(o))
    return True


def main():
    root = sys.argv[1]
    for name in sys.argv[2:]:
        deals, floors = load_deck(os.path.join(root, "community", name, "index.html"))
        up = os.path.join(root, "data/units", name + ".json")
        units = []
        if os.path.exists(up):
            for r in json.load(open(up, encoding="utf-8"))["units"]:
                d, _ = door_no(r.get("addr"))
                units.append({"door": d, "floor": cn_floor(r.get("floor")), "rooms": r.get("rooms"),
                              "main_ping": r.get("main_ping"), "area_ping": r.get("area_ping"), "parking": r.get("parking")})
        else:
            for r in deals:
                d, _ = door_no(r.get("addr"))
                units.append({"door": d, "floor": cn_floor(r.get("floor")), "area_ping": r.get("area"),
                              "parking": bool(r.get("ptype"))})
        ok = render(name, units, floors, os.path.join(root, "data/units", name + ".svg"))
        print(name, "ok" if ok else "skip", len(units))


if __name__ == "__main__":
    main()
