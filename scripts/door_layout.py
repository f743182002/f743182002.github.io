#!/usr/bin/env python3
"""阿陞版「棟別門牌配置圖」產生器。

資料只用本站自己的資料，不參考、不描繪任何其他網站的圖：
  - 社區簡報內嵌的 window.SITE（建物輪廓 blds、道路 roads；座標為以社區為原點的公尺，x 向東、y 向北）
  - 選用：data/doors/<社區名>.json 門牌定位（property-deck scope_check 的國土測繪中心門牌定位結果）
      格式：{"doors":[{"no":"191","lat":25.02,"lon":121.47}, ...]} 或 {"doors":[{"no":"191","x":12.3,"y":-4.5}]}
  - data/communities.json 的社區名、臨路
輸出：data/layout/<社區名>.svg

用法：python3 scripts/door_layout.py [repo根目錄] [社區名 ...]
"""
import json, math, os, sys, html

RED = "#C8161D"
INK = "#1F2B33"
GREY = "#8A969E"


def load_site(path):
    s = open(path, encoding="utf-8").read()
    i = s.find("window.SITE=")
    if i < 0:
        return None
    obj, _ = json.JSONDecoder().raw_decode(s[i + len("window.SITE="):])
    return obj


def centroid(p):
    xs = [a[0] for a in p]; ys = [a[1] for a in p]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def inside(pt, poly):
    x, y = pt; c = False
    for i in range(len(poly)):
        x1, y1 = poly[i]; x2, y2 = poly[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1:
            c = not c
    return c


def dist_to_poly(pt, poly):
    if inside(pt, poly):
        return 0.0
    best = 1e18
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i - 1], poly[i]
        dx, dy = x2 - x1, y2 - y1
        t = max(0, min(1, ((pt[0] - x1) * dx + (pt[1] - y1) * dy) / (dx * dx + dy * dy + 1e-12)))
        best = min(best, math.hypot(pt[0] - x1 - t * dx, pt[1] - y1 - t * dy))
    return best


def doors_local(doors_path, site_ll):
    if not os.path.exists(doors_path):
        return []
    d = json.load(open(doors_path, encoding="utf-8"))
    out = []
    lat0, lon0 = site_ll
    for r in d.get("doors", []):
        if "x" in r:
            out.append((str(r["no"]), (float(r["x"]), float(r["y"]))))
        elif "lat" in r and lat0 is not None:
            x = (float(r["lon"]) - lon0) * 111320 * math.cos(math.radians(lat0))
            y = (float(r["lat"]) - lat0) * 111320
            out.append((str(r["no"]), (x, y)))
    return out


def short_nums(nums):
    def key(n):
        digits = "".join(ch for ch in n if ch.isdigit())
        return (int(digits) if digits else 0, n)
    nums = sorted(set(nums), key=key)
    return nums


def render(name, site, comm, doors, out_path):
    me = [b for b in site.get("blds", []) if b.get("me")]
    if not me:
        return False
    pts = [q for b in me for q in b["p"]] + [q for _, q in doors]
    pad = 32
    minx = min(q[0] for q in pts) - pad; maxx = max(q[0] for q in pts) + pad
    miny = min(q[1] for q in pts) - pad; maxy = max(q[1] for q in pts) + pad
    w_m, h_m = maxx - minx, maxy - miny
    W = 900; scale = (W - 80) / max(w_m, h_m * 1.2)
    mapW, mapH = w_m * scale, h_m * scale
    ox, oy = 40 + (W - 80 - mapW) / 2, 120
    H = int(oy + mapH + 130)

    def P(q):
        return ox + (q[0] - minx) * scale, oy + (maxy - q[1]) * scale

    def path(poly, close=True):
        s = " ".join(("M" if i == 0 else "L") + "%.1f,%.1f" % P(q) for i, q in enumerate(poly))
        return s + (" Z" if close else "")

    # 門牌分配到最近的本社區棟（8 公尺內）
    assign = {i: [] for i in range(len(me))}
    for no, q in doors:
        dists = [dist_to_poly(q, b["p"]) for b in me]
        i = min(range(len(me)), key=lambda k: dists[k])
        if dists[i] <= 8:
            assign[i].append(no)

    e = html.escape
    o = []
    o.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" font-family="Noto Sans TC, Microsoft JhengHei, PingFang TC, sans-serif">' % (W, H, W, H))
    o.append('<rect width="100%" height="100%" fill="#FFFFFF"/><rect width="100%" height="8" fill="{0}"/>'.format(RED))
    o.append('<text x="40" y="58" font-size="30" font-weight="700" fill="{0}">{1}</text>'.format(INK, e(name)))
    sub = "棟別門牌配置示意" if doors else "棟別配置示意"
    o.append('<text x="40" y="92" font-size="18" fill="{0}">{1}</text>'.format(GREY, e(sub)))
    o.append('<defs><clipPath id="c"><rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="12"/></clipPath></defs>' % (ox, oy, mapW, mapH))
    o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="12" fill="#F4F6F7" stroke="#DCE1E5"/>' % (ox, oy, mapW, mapH))
    o.append('<g clip-path="url(#c)">')
    # 周邊建物
    for b in site.get("blds", []):
        if b.get("me"):
            continue
        if all(not (minx - 40 < q[0] < maxx + 40 and miny - 40 < q[1] < maxy + 40) for q in b["p"]):
            continue
        o.append('<path d="%s" fill="#E3E7EA" stroke="#D2D8DC" stroke-width="1"/>' % path(b["p"]))
    # 道路
    labels = []
    for r in site.get("roads", []):
        p = r.get("p", [])
        if len(p) < 2:
            continue
        vis = [q for q in p if minx < q[0] < maxx and miny < q[1] < maxy]
        near = any(minx - 60 < q[0] < maxx + 60 and miny - 60 < q[1] < maxy + 60 for q in p)
        if not near:
            continue
        wpx = {3: 16, 2: 12, 1: 9}.get(r.get("c"), 7)
        o.append('<path d="%s" fill="none" stroke="#FFFFFF" stroke-width="%d" stroke-linecap="round" stroke-linejoin="round"/>' % (path(p, False), wpx + 4))
        o.append('<path d="%s" fill="none" stroke="#F2C14E" stroke-width="%d" stroke-linecap="round" stroke-linejoin="round"/>' % (path(p, False), wpx))
        if r.get("n") and vis:
            labels.append((r["n"], vis))
    # 本社區各棟
    for i, b in enumerate(me):
        o.append('<path d="%s" fill="#FFFFFF" stroke="%s" stroke-width="3.5" stroke-linejoin="round"/>' % (path(b["p"]), RED))
    o.append('</g>')
    # 路名（每條一個，放在可見段中點）
    used = set()
    for n, vis in labels:
        if n in used:
            continue
        used.add(n)
        q = vis[len(vis) // 2]
        x, y = P(q)
        o.append('<text x="%.1f" y="%.1f" font-size="17" font-weight="700" fill="#8A5A00" text-anchor="middle" stroke="#FFFFFF" stroke-width="4" paint-order="stroke">%s</text>' % (x, y - 12, e(n)))
    # 棟標籤與門牌
    for i, b in enumerate(me):
        cx, cy = P(centroid(b["p"]))
        nums = short_nums(assign[i])
        raw = (b.get("n") or "").replace(name, "").strip()
        title = raw if raw else (name if len(me) == 1 else "")
        lines = [title] if title else []
        if nums:
            lines += [" ".join(nums[k:k + 4]) + ("號" if k + 4 >= len(nums) else "") for k in range(0, len(nums), 4)]
        y0 = cy - (len(lines) - 1) * 11
        for k, t in enumerate(lines):
            head = (k == 0 and bool(title))
            fs = 17 if head else 15
            o.append('<text x="%.1f" y="%.1f" font-size="%d" font-weight="%s" fill="%s" text-anchor="middle" stroke="#FFFFFF" stroke-width="4" paint-order="stroke">%s</text>' % (cx, y0 + k * 22, fs, "700" if head else "600", RED if head else INK, e(t)))
    # 指北針
    nx, ny = ox + mapW - 44, oy + 48
    o.append('<circle cx="%.1f" cy="%.1f" r="26" fill="#FFFFFF" stroke="%s" stroke-width="3"/>' % (nx, ny, RED))
    o.append('<path d="M%.1f,%.1f L%.1f,%.1f L%.1f,%.1f L%.1f,%.1f Z" fill="%s"/>' % (nx, ny - 18, nx + 9, ny + 10, nx, ny + 4, nx - 9, ny + 10, RED))
    o.append('<text x="%.1f" y="%.1f" font-size="15" font-weight="700" fill="%s" text-anchor="middle">北</text>' % (nx, ny + 46, RED))
    # 比例尺 50m
    sx, sy = ox + 20, oy + mapH - 22
    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="3"/>' % (sx, sy, sx + 50 * scale, sy, INK))
    o.append('<text x="%.1f" y="%.1f" font-size="13" fill="%s">約 50 公尺</text>' % (sx, sy - 8, INK))
    # 附註
    fy = oy + mapH + 36
    notes = [("棟別門牌配置示意" if doors else "棟別配置示意") + "，僅供參考；實際以現場、門牌及使用執照為準。",
             ("本圖為本店依自有查證資料繪製：建物輪廓 OpenStreetMap、門牌位置 內政部國土測繪中心門牌定位。" if doors else "本圖為本店依自有查證資料繪製：建物輪廓 OpenStreetMap，紅框為本社區。"),
             "道路底圖 © OpenStreetMap 貢獻者"]
    for k, t in enumerate(notes):
        o.append('<text x="40" y="%.1f" font-size="%d" fill="%s">%s</text>' % (fy + k * 26, 16 if k < 2 else 13, INK if k < 2 else GREY, e(t)))
    o.append('</svg>')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    open(out_path, "w", encoding="utf-8").write("\n".join(o))
    return True


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    only = set(sys.argv[2:])
    comms = json.load(open(os.path.join(root, "data/communities.json"), encoding="utf-8"))["communities"]
    done = []
    for c in comms:
        n = c["name"]
        if only and n not in only:
            continue
        deck = os.path.join(root, "community", n, "index.html")
        if not os.path.exists(deck):
            continue
        site = load_site(deck)
        if not site:
            continue
        doors = doors_local(os.path.join(root, "data/doors", n + ".json"), (c.get("lat"), c.get("lon")))
        if render(n, site, c, doors, os.path.join(root, "data/layout", n + ".svg")):
            done.append((n, len(doors)))
    if not only:
        json.dump({"updated": __import__("datetime").date.today().isoformat(),
                   "layouts": {n: {"doors": k} for n, k in done}},
                  open(os.path.join(root, "data/layout/index.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for n, k in done:
        print("ok", n, "門牌", k)


if __name__ == "__main__":
    main()
