#!/usr/bin/env python3
"""阿陞版「棟別門牌配置圖」產生器。

資料只用本站自己的資料，不參考、不描繪任何其他網站的圖：
  - 社區簡報內嵌的 window.SITE（建物輪廓 blds、道路 roads；座標為以社區為原點的公尺，x 向東、y 向北）
  - 選用：data/doors/<社區名>.json 門牌定位（property-deck scope_check 的國土測繪中心門牌定位結果）
      格式：{"origin":{"lat":..,"lon":..},"doors":[{"no":"191","lat":25.02,"lon":121.47}, ...]} 或 {"doors":[{"no":"191","x":12.3,"y":-4.5}]}
      （origin＝簡報 SITE 的原點，沒有就用 data/communities.json 的座標）
  - data/communities.json 的社區名、臨路
輸出：data/layout/<社區名>.svg（只給 viewBox，寬度自適應，手機寬度看得完整；內容沒變不改檔）
門牌：每個門牌依國土測繪中心座標畫紅點＋獨立小標籤，標籤彼此不重疊（放不下往外推、拉引線）。


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
    # 原點：簡報 window.SITE 的原點（property-deck summary.json center，匯出時寫在 origin）。
    # 地圖 communities.json 的點不一定等於 SITE 原點（綠如意差約 12 公尺），沒有 origin 才退回用地圖的點。
    o = d.get("origin") or {}
    lat0, lon0 = (o["lat"], o["lon"]) if "lat" in o and "lon" in o else site_ll
    for r in d.get("doors", []):
        if "x" in r:
            out.append((str(r["no"]), (float(r["x"]), float(r["y"]))))
        elif "lat" in r and lat0 is not None:
            # 換算係數跟 property-deck site_data.py 產生 SITE 時相同（東西 111320×cos，南北 110574）
            x = (float(r["lon"]) - lon0) * 111320 * math.cos(math.radians(lat0))
            y = (float(r["lat"]) - lat0) * 110574
            out.append((str(r["no"]), (x, y)))
    return out


def short_nums(nums):
    def key(n):
        # 「92之1」排在 92 後面、100 前面（不可把數字全部接起來比，921 會排到 102 後面）
        parts = [int(x) for x in "".join(ch if ch.isdigit() else " " for ch in n).split()]
        return (parts or [0], n)
    nums = sorted(set(nums), key=key)
    return nums


def text_w(s, fs):
    return sum(fs * (0.58 if ord(ch) < 0x2E80 else 1.0) for ch in s)


def door_labels(nums):
    """門牌標籤文字。全部門牌同一個主號又都有之N（健華新城 309之1～之38）→ 標籤只寫「之N」，主號寫在副標；
    否則寫「191」「209之1」。回傳 ({門牌: 標籤}, 共同主號 or None)。"""
    mains = {n.split("之")[0] for n in nums}
    if len(nums) > 1 and len(mains) == 1 and all("之" in n for n in nums):
        return {n: "之" + n.split("之", 1)[1] for n in nums}, next(iter(mains))
    return {n: n for n in nums}, None


DIRS = [(1, 0), (-1, 0), (0, -1), (0, 1), (0.71, -0.71), (-0.71, -0.71), (0.71, 0.71), (-0.71, 0.71),
        (0.92, -0.38), (-0.92, -0.38), (0.92, 0.38), (-0.92, 0.38), (0.38, -0.92), (-0.38, -0.92), (0.38, 0.92), (-0.38, 0.92)]
RADII = [5, 14, 26, 40, 56, 74, 96]


def _overlap(a, b, m=2):
    return not (a[2] + m <= b[0] or b[2] + m <= a[0] or a[3] + m <= b[1] or b[3] + m <= a[1])


def _area(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0]); h = min(a[3], b[3]) - max(a[1], b[1])
    return w * h if w > 0 and h > 0 else 0


def place_labels(points, frame, fs, keep_out=()):
    """每個門牌一個小標籤，依門牌實際座標擺在點旁邊，彼此不重疊（放不下就往外推、加引線）。
    points：[(門牌, 標籤字, (px, py))]；frame：(x0, y0, x1, y1) 標籤必須在框內；keep_out：不可壓到的框（指北針、比例尺）。
    回傳 [(門牌, 標籤字, (px, py), box, 是否要引線)]；box＝(x0, y0, x1, y1)。"""
    dots = [(p[0] - 4, p[1] - 4, p[0] + 4, p[1] + 4) for _, _, p in points]
    placed = []
    order = sorted(range(len(points)), key=lambda i: (points[i][2][0], points[i][2][1]))
    for i in order:
        no, lab, (px, py) = points[i]
        bw, bh = text_w(lab, fs) + 8, fs + 6
        best = None
        for r in RADII:
            for dx, dy in DIRS:
                cx = px + dx * (r + bw / 2); cy = py + dy * (r + bh / 2)
                box = (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)
                if box[0] < frame[0] or box[1] < frame[1] or box[2] > frame[2] or box[3] > frame[3]:
                    continue
                others = [b for _, _, _, b, _ in placed] + [d for k, d in enumerate(dots) if k != i] + list(keep_out)
                cost = sum(_area(box, b) for b in others if _overlap(box, b))
                if cost == 0:
                    best = (0, box, r)
                    break
                if best is None or cost < best[0]:
                    best = (cost, box, r)
            if best and best[0] == 0:
                break
        if best is None:   # 框太小：貼在點右邊
            best = (0, (px + 6, py - bh / 2, px + 6 + bw, py + bh / 2), 5)
        placed.append((no, lab, (px, py), best[1], best[2] > 10))
    return placed


def labels_overlap(placed):
    """測試用：任兩個標籤框有重疊就回傳那一對。"""
    for i in range(len(placed)):
        for j in range(i + 1, len(placed)):
            if _overlap(placed[i][3], placed[j][3], 0):
                return placed[i][0], placed[j][0]
    return None


def render(name, site, comm, doors, out_path=None):
    """回傳 SVG 字串（out_path 給了就寫檔，內容沒變不寫）；沒有本社區建物回 None。"""
    me = [b for b in site.get("blds", []) if b.get("me")]
    if not me:
        return None
    # 門牌分配到最近的本社區棟（8 公尺內）；離太遠的不畫
    kept = []
    for no, q in doors:
        if min(dist_to_poly(q, b["p"]) for b in me) <= 8:
            kept.append((no, q))
    pts = [q for b in me for q in b["p"]] + [q for _, q in kept]
    pad = 26
    minx = min(q[0] for q in pts) - pad; maxx = max(q[0] for q in pts) + pad
    miny = min(q[1] for q in pts) - pad; maxy = max(q[1] for q in pts) + pad
    w_m, h_m = maxx - minx, maxy - miny
    W = 640; M = 20
    scale = (W - 2 * M) / max(w_m, h_m * 1.0)
    mapW, mapH = w_m * scale, h_m * scale
    ox, oy = M + (W - 2 * M - mapW) / 2, 96
    labs, common = door_labels([n for n, _ in kept])

    def P(q):
        return ox + (q[0] - minx) * scale, oy + (maxy - q[1]) * scale

    def path(poly, close=True):
        s = " ".join(("M" if i == 0 else "L") + "%.1f,%.1f" % P(q) for i, q in enumerate(poly))
        return s + (" Z" if close else "")

    e = html.escape
    nx, ny = ox + mapW - 30, oy + 34
    sx, sy = ox + 14, oy + mapH - 16
    keep_out = [(nx - 22, ny - 22, nx + 22, ny + 40), (sx - 4, sy - 20, sx + max(50 * scale, 70) + 4, sy + 4)]
    # 棟名（有名字才寫，放在棟中心）先佔位，門牌標籤不可蓋住棟名（新巨蛋 A～D 棟）
    titles = []
    for b in me:
        raw = (b.get("n") or "").replace(name, "").strip()
        title = raw if raw else (name if len(me) == 1 and not kept else "")
        if title:
            cx, cy = P(centroid(b["p"]))
            tw = text_w(title, 14)
            titles.append((title, cx, cy))
            keep_out.append((cx - tw / 2 - 3, cy - 10, cx + tw / 2 + 3, cy + 9))
    placed = place_labels([(n, labs[n], P(q)) for n, q in kept], (ox + 2, oy + 2, ox + mapW - 2, oy + mapH - 2), 12, keep_out)
    # 附註（依寬度換行）
    notes = [("棟別門牌配置示意" if kept else "棟別配置示意") + "，僅供參考；實際以現場、門牌及使用執照為準。",
             ("本圖為本店依自有查證資料繪製：建物輪廓 OpenStreetMap、門牌位置 內政部國土測繪中心門牌定位（紅點為門牌實際位置）。"
              if kept else "本圖為本店依自有查證資料繪製：建物輪廓 OpenStreetMap，紅框為本社區。")]
    note_lines = []
    for t in notes:
        cur = ""
        for ch in t:
            if text_w(cur + ch, 13) > W - 2 * M and ch not in "，。；：、）":
                note_lines.append(cur); cur = ""
            cur += ch
        note_lines.append(cur)
    H = int(oy + mapH + 24 + len(note_lines) * 19 + 26)
    o = []
    o.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" preserveAspectRatio="xMidYMin meet" '
             'style="width:100%%;height:auto;max-width:%dpx" font-family="Noto Sans TC, Microsoft JhengHei, PingFang TC, sans-serif">' % (W, H, W * 2))
    o.append('<rect width="100%" height="100%" fill="#FFFFFF"/><rect width="100%" height="6" fill="{0}"/>'.format(RED))
    o.append('<text x="%d" y="44" font-size="24" font-weight="700" fill="%s">%s</text>' % (M, INK, e(name)))
    sub = "棟別門牌配置示意" if kept else "棟別配置示意"
    if common:
        sub += "（門牌皆為 %s號之N，標籤只寫「之N」）" % common
    o.append('<text x="%d" y="72" font-size="14" fill="%s">%s</text>' % (M, GREY, e(sub)))
    o.append('<defs><clipPath id="c"><rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="10"/></clipPath></defs>' % (ox, oy, mapW, mapH))
    o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="10" fill="#F4F6F7" stroke="#DCE1E5"/>' % (ox, oy, mapW, mapH))
    o.append('<g clip-path="url(#c)">')
    for b in site.get("blds", []):
        if b.get("me"):
            continue
        if all(not (minx - 40 < q[0] < maxx + 40 and miny - 40 < q[1] < maxy + 40) for q in b["p"]):
            continue
        o.append('<path d="%s" fill="#E3E7EA" stroke="#D2D8DC" stroke-width="1"/>' % path(b["p"]))
    labels = []
    for r in site.get("roads", []):
        p = r.get("p", [])
        if len(p) < 2:
            continue
        vis = [q for q in p if minx < q[0] < maxx and miny < q[1] < maxy]
        if not any(minx - 60 < q[0] < maxx + 60 and miny - 60 < q[1] < maxy + 60 for q in p):
            continue
        wpx = {3: 12, 2: 9, 1: 7}.get(r.get("c"), 5)
        o.append('<path d="%s" fill="none" stroke="#FFFFFF" stroke-width="%d" stroke-linecap="round" stroke-linejoin="round"/>' % (path(p, False), wpx + 3))
        o.append('<path d="%s" fill="none" stroke="#F2C14E" stroke-width="%d" stroke-linecap="round" stroke-linejoin="round"/>' % (path(p, False), wpx))
        if r.get("n") and vis:
            labels.append((r["n"], vis))
    for b in me:
        o.append('<path d="%s" fill="#FFFFFF" stroke="%s" stroke-width="2.5" stroke-linejoin="round"/>' % (path(b["p"]), RED))
    o.append('</g>')
    used = set()
    for n, vis in labels:
        if n in used:
            continue
        used.add(n)
        x, y = P(vis[len(vis) // 2])
        half = text_w(n, 14) / 2 + 4   # 路名整個留在地圖框內（文化路二段在左緣被切掉）
        x = min(max(x, ox + half), ox + mapW - half)
        o.append('<text x="%.1f" y="%.1f" font-size="14" font-weight="700" fill="#8A5A00" text-anchor="middle" stroke="#FFFFFF" stroke-width="4" paint-order="stroke">%s</text>' % (x, y - 9, e(n)))
    # 棟名（有名字才寫，放在棟中心；門牌另外用小標籤）
    for title, cx, cy in titles:
        if True:
            o.append('<text x="%.1f" y="%.1f" font-size="14" font-weight="700" fill="%s" text-anchor="middle" stroke="#FFFFFF" stroke-width="4" paint-order="stroke">%s</text>' % (cx, cy + 5, RED, e(title)))
    # 門牌：紅點＝國土測繪中心門牌定位；標籤彼此不重疊，離點遠的拉引線
    for no, lab, (px, py), box, lead in placed:
        if lead:
            bx = min(max(px, box[0]), box[2]); by = min(max(py, box[1]), box[3])
            o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (px, py, bx, by, GREY))
    for no, lab, (px, py), box, lead in placed:
        o.append('<circle cx="%.1f" cy="%.1f" r="3.2" fill="%s" stroke="#FFFFFF" stroke-width="1.2"/>' % (px, py, RED))
    for no, lab, (px, py), box, lead in placed:
        o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="4" fill="#FFFFFF" fill-opacity="0.94" stroke="%s" stroke-width="1"/>' % (
            box[0], box[1], box[2] - box[0], box[3] - box[1], RED))
        o.append('<text x="%.1f" y="%.1f" font-size="12" font-weight="700" fill="%s" text-anchor="middle">%s</text>' % (
            (box[0] + box[2]) / 2, box[3] - 5, INK, e(lab)))
    # 指北針
    o.append('<circle cx="%.1f" cy="%.1f" r="18" fill="#FFFFFF" stroke="%s" stroke-width="2.5"/>' % (nx, ny, RED))
    o.append('<path d="M%.1f,%.1f L%.1f,%.1f L%.1f,%.1f L%.1f,%.1f Z" fill="%s"/>' % (nx, ny - 13, nx + 7, ny + 8, nx, ny + 3, nx - 7, ny + 8, RED))
    o.append('<text x="%.1f" y="%.1f" font-size="12" font-weight="700" fill="%s" text-anchor="middle">北</text>' % (nx, ny + 34, RED))
    # 比例尺 50m
    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2.5"/>' % (sx, sy, sx + 50 * scale, sy, INK))
    o.append('<text x="%.1f" y="%.1f" font-size="12" fill="%s">約 50 公尺</text>' % (sx, sy - 7, INK))
    fy = oy + mapH + 26
    for k, t in enumerate(note_lines):
        o.append('<text x="%d" y="%.1f" font-size="13" fill="%s">%s</text>' % (M, fy + k * 19, INK, e(t)))
    o.append('<text x="%d" y="%.1f" font-size="11" fill="%s">道路底圖 © OpenStreetMap 貢獻者</text>' % (M, fy + len(note_lines) * 19 + 4, GREY))
    o.append('</svg>')
    svg = "\n".join(o) + "\n"
    if out_path:
        write_if_changed(out_path, svg)
    return svg


VIEWER = """<!doctype html>
<html lang="zh-Hant-TW"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<title>棟別配置圖｜板橋阿陞聊房</title>
<style>html,body{margin:0;background:#fff;font-family:"Noto Sans TC","Microsoft JhengHei","PingFang TC",sans-serif;color:#1F2B33}
main{max-width:960px;margin:0 auto;padding:8px}img{display:block;width:100%;height:auto}
a{color:#C8161D;font-size:15px;display:inline-block;padding:10px 8px}</style></head>
<body><main><a href="../../map/">← 回商圈地圖</a><img id="g" alt="棟別配置圖"><p id="m" hidden>找不到這個社區的配置圖。</p></main>
<script>
(function(){var n=new URLSearchParams(location.search).get('n')||'';var g=document.getElementById('g');
if(!n||/[\\/\\\\.]/.test(n)){g.hidden=true;document.getElementById('m').hidden=false;return}
document.title=n+' 棟別配置圖｜板橋阿陞聊房';g.alt=n+' 棟別配置圖';g.src=encodeURIComponent(n)+'.svg';
g.onerror=function(){g.hidden=true;document.getElementById('m').hidden=false}})();
</script></body></html>
"""


def write_if_changed(path, text):
    if os.path.exists(path) and open(path, encoding="utf-8").read() == text:
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return True


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
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
    # 手機看圖頁：直接開 .svg 時手機瀏覽器用 980px 版面寬度，只看得到左半；地圖的「看棟別配置圖」改開這頁（有 viewport）
    write_if_changed(os.path.join(root, "data/layout/view.html"), VIEWER)
    if not only:
        idx = os.path.join(root, "data/layout/index.json")
        layouts = {n: {"doors": k} for n, k in done}
        old = json.load(open(idx, encoding="utf-8")) if os.path.exists(idx) else {}
        if old.get("layouts") != layouts:   # 內容沒變就不改（不因為日期每天產生 diff）
            with open(idx, "w", encoding="utf-8", newline="\n") as fh:
                json.dump({"updated": __import__("datetime").date.today().isoformat(), "layouts": layouts}, fh, ensure_ascii=False, indent=1)
    for n, k in done:
        print("ok", n, "門牌", k)


if __name__ == "__main__":
    main()
