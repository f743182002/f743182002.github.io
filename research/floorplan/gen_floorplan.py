#!/usr/bin/env python3
"""阿陞版標準戶型示意圖產生器（只用標準函式庫）。
用法：python3 gen_floorplan.py unit.json out.svg
輸入只能是事實資料（房廳衛數、面積、方位、自己現場畫的相鄰關係），不讀任何圖檔。"""
import json, sys, math
from xml.sax.saxutils import escape as esc

CELL, PAD, TOP, BOTTOM = 52, 40, 96, 128      # 一格 52px；格子是「相對位置」不是尺寸
RED, INK, LINE = "#C8161D", "#222222", "#555555"
FILL = {"living": "#F4F1EC", "dining": "#F4F1EC", "bed": "#ECECEC", "kitchen": "#E6EAED",
        "bath": "#E6EAED", "balcony": "#FFFFFF", "other": "#F7F7F7"}
CAP1 = "格局示意，非依比例繪製，僅供參考；實際以現場、權狀及使用執照為準"
CAP2 = "本圖為本店依公開資料與現場勘查自行繪製之示意圖，非建商原始圖面"
FORBIDDEN_KEYS = {"floor", "unit_no", "address", "door_no", "樓層", "門牌", "戶號"}
OK_SOURCES = {"權狀", "實價登錄", "現場勘查", "本店委託物件", "建商書面授權"}
BAD_SOURCES = {"建商平面圖", "591", "他店格局圖", "竣工圖", "測量成果圖"}

def check(u):
    errs = [f"不可有欄位 {k}（隱私）" for k in FORBIDDEN_KEYS if k in u]
    for s in u.get("sources", []):
        if s["type"] in BAD_SOURCES or s["type"] not in OK_SOURCES:
            errs.append(f"來源 {s['type']} 不在允許清單")
        if not s.get("evidence"):
            errs.append(f"來源 {s['type']} 缺佐證檔名")
    if not u.get("sources"):
        errs.append("沒有填資料來源")
    occ = {}
    for r in u["rooms"]:
        x, y, w, h = r["cell"]
        if x < 0 or y < 0 or x + w > u["grid"][0] or y + h > u["grid"][1]:
            errs.append(f"{r['name']} 超出格子範圍")
        for i in range(x, x + w):
            for j in range(y, y + h):
                if (i, j) in occ:
                    errs.append(f"{r['name']} 與 {occ[(i, j)]} 重疊")
                occ[(i, j)] = r["name"]
    c = u["counts"]
    beds = sum(1 for r in u["rooms"] if r["type"] == "bed")
    baths = sum(1 for r in u["rooms"] if r["type"] == "bath")
    if (beds, baths) != (c["房"], c["衛"]):
        errs.append(f"房間數 {beds}房{baths}衛 與 counts {c['房']}房{c['衛']}衛 不符")
    return sorted(set(errs))

def room_svg(r):
    x, y, w, h = r["cell"]
    px, py, pw, ph = PAD + x * CELL + 3, TOP + y * CELL + 3, w * CELL - 6, h * CELL - 6
    dash = ' stroke-dasharray="6 4"' if r["type"] == "balcony" else ""
    out = [f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="10" fill="{FILL.get(r["type"], FILL["other"])}" '
           f'stroke="{LINE}" stroke-width="2"{dash}/>']
    cx, cy = px + pw / 2, py + ph / 2
    one_line = h == 1 and r.get("note")          # 矮房間：備註併在同一行
    label = f'{r["name"]}<tspan font-size="11" font-weight="400" fill="#777">（{esc(r["note"])}）</tspan>' if one_line else esc(r["name"])
    out.append(f'<text x="{cx}" y="{cy + 5}" font-size="16" font-weight="700" fill="{INK}" text-anchor="middle">{label}</text>')
    if r.get("note") and not one_line:
        out.append(f'<text x="{cx}" y="{cy + 24}" font-size="11" fill="#777" text-anchor="middle">{esc(r["note"])}</text>')
    return out

def entrance_svg(e):
    side, pos = e["side"], e["pos"]          # pos = 第幾格（從 0 起），箭頭畫在該格中點
    gx, gy = U["grid"]
    if side in ("S", "N"):
        x = PAD + (pos + .5) * CELL; y = TOP + (gy * CELL if side == "S" else 0)
        d = 1 if side == "S" else -1
        pts = f"{x},{y + 4*d} {x-9},{y + 20*d} {x+9},{y + 20*d}"; tx, ty = x, y + 36 * d + (4 if d > 0 else 0)
    else:
        y = TOP + (pos + .5) * CELL; x = PAD + (gx * CELL if side == "E" else 0)
        d = 1 if side == "E" else -1
        pts = f"{x + 4*d},{y} {x + 20*d},{y-9} {x + 20*d},{y+9}"; tx, ty = x + 34 * d, y + 5
    return [f'<polygon points="{pts}" fill="{RED}"/>',
            f'<text x="{tx}" y="{ty}" font-size="13" font-weight="700" fill="{RED}" text-anchor="middle">入口</text>']

def north_svg(deg, cx, cy):
    t = f'rotate({deg} {cx} {cy})'
    return [f'<circle cx="{cx}" cy="{cy}" r="22" fill="#fff" stroke="{RED}" stroke-width="2"/>',
            f'<g transform="{t}"><polygon points="{cx},{cy-17} {cx-7},{cy+8} {cx},{cy+3} {cx+7},{cy+8}" fill="{RED}"/>',
            f'</g>', f'<text x="{cx + 34*math.sin(math.radians(deg))}" y="{cy - 34*math.cos(math.radians(deg)) + 4}" '
            f'font-size="12" font-weight="700" fill="{RED}" text-anchor="middle">N</text>']

def render(u):
    gx, gy = u["grid"]
    W = max(PAD * 2 + gx * CELL + 90, 560); H = TOP + gy * CELL + BOTTOM
    c, a = u["counts"], u.get("areas_ping", {})
    head = f'{u["type_label"]}｜{c["房"]}房{c["廳"]}廳{c["衛"]}衛'
    sub = "　".join(f"{k}約 {v} 坪" for k, v in a.items())
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
         f'font-family="Noto Sans TC, PingFang TC, Microsoft JhengHei, WenQuanYi Zen Hei, sans-serif">',
         f'<rect width="{W}" height="{H}" fill="#fff"/>', f'<rect x="0" y="0" width="{W}" height="6" fill="{RED}"/>',
         f'<text x="{PAD}" y="42" font-size="22" font-weight="700" fill="{INK}">{esc(u["community"])}　{esc(head)}</text>',
         f'<text x="{PAD}" y="66" font-size="13" fill="#555">{esc(sub)}</text>']
    if u.get("sample"):
        s.append(f'<text x="{W - PAD}" y="42" font-size="18" font-weight="700" fill="{RED}" text-anchor="end">範例</text>')
    for r in u["rooms"]:
        s += room_svg(r)
    s += entrance_svg(u["entrance"])
    s += north_svg(u.get("north_deg", 0), PAD + gx * CELL + 52, TOP + 30)
    srcs = "、".join(x["type"] for x in u["sources"])
    y0 = TOP + gy * CELL + 70
    s += [f'<line x1="{PAD}" y1="{y0 - 18}" x2="{W - PAD}" y2="{y0 - 18}" stroke="#ddd"/>',
          f'<text x="{PAD}" y="{y0}" font-size="12" fill="{INK}">{CAP1}</text>',
          f'<text x="{PAD}" y="{y0 + 18}" font-size="12" fill="{INK}">{CAP2}</text>',
          f'<text x="{PAD}" y="{y0 + 36}" font-size="11" fill="#777">資料來源：{esc(srcs)}｜繪製 {esc(u["drawn_on"])}</text>',
          '</svg>']
    return "\n".join(s)

if __name__ == "__main__":
    U = json.load(open(sys.argv[1], encoding="utf-8"))
    problems = check(U)
    if problems:
        sys.exit("不產圖：\n" + "\n".join(problems))
    open(sys.argv[2], "w", encoding="utf-8").write(render(U))
    print("OK", sys.argv[2])
