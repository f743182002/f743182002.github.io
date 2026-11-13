#!/usr/bin/env python3
"""依 repo 內容重新產生 sitemap.xml 與首頁靜態清單。

由 .github/workflows/build-site.yml 在每次 push 到 main 時執行，
指揮艙發布新簡報（只改 decks.json、新增 community/<社區名>/ 或 S<編號>/）
不必改任何程式，sitemap 與首頁清單會自動更新。

1. 首頁 index.html 的 <!-- DECKS:START xxx --> ... <!-- DECKS:END xxx -->
   之間，依 decks.json 產生靜態清單（不開 JS 也看得到、搜尋引擎也讀得到）。
   如果 index.html 又被舊發布流程覆寫成純清單（沒有標記），
   會從 git 歷史找回最後一版有標記的總站首頁再產生。
2. sitemap.xml：首頁、map/、about/、buy/、sell/、area/<區域名>/（存在才列）、每個 community/<社區名>/、
   每個 S<編號>/。網址一律 https://banqiaoasheng.com/ 開頭，中文路徑編碼。

本機執行：python3 scripts/build_site.py
"""
import html
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://banqiaoasheng.com/"
INDEX = ROOT / "index.html"
MARK = re.compile(r"(<!-- DECKS:START (\w+) -->)(.*?)(<!-- DECKS:END \2 -->)", re.S)

# 和瀏覽器 encodeURI() 一樣不編碼的字元
ENCODE_URI_SAFE = "-_.!~*'();/?:@&=+$,#"


def git(*args):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def esc(s):
    return html.escape("" if s is None else str(s), quote=True).replace("&#x27;", "'")


# decks.json 的 status（2026-11-04）：社區分析／銷售中／已成交；其他（待確認、沒填）一律顯示「狀態待確認」，
# 不會把已成交或下架的物件寫成還在賣
STATUS = {"社區分析": ("社區分析", "c"), "銷售中": ("銷售中", "s"), "已成交": ("已成交", "d")}


def status_badge(d):
    label, cls = STATUS.get(d.get("status"), ("狀態待確認", "u"))
    return '<i class="st st-' + cls + '">' + label + "</i>"


def card(path, d, cta):
    # 和 index.html 裡 JS 的 card() 產生一樣的標記
    return (
        '<li><a href="' + quote(path, safe=ENCODE_URI_SAFE) + '/">' + status_badge(d) + "<b>" + esc(d.get("name"))
        + "</b><span>" + esc(d.get("subtitle")) + "</span><span>" + esc(d.get("area"))
        + '</span><span class="go">' + cta + " →</span></a></li>"
    )


def load_decks():
    return json.loads((ROOT / "decks.json").read_text(encoding="utf-8"))


def sorted_keys(decks):
    # 和 JS 一樣：依 updated 新到舊（穩定排序，同日期維持 decks.json 原順序）
    return sorted(decks, key=lambda k: decks[k].get("updated") or "", reverse=True)


def restore_index_if_overwritten(text):
    if MARK.search(text):
        return text
    for rev in git("log", "--format=%H", "--", "index.html").split():
        old = git("show", f"{rev}:index.html")
        if MARK.search(old):
            print(f"index.html 沒有 DECKS 標記（疑似被舊發布流程覆寫），已從 {rev[:7]} 還原總站首頁")
            return old
    sys.exit("index.html 沒有 <!-- DECKS:START --> 標記，git 歷史也找不到可還原的版本")


def build_index(decks):
    text = INDEX.read_text(encoding="utf-8")
    text = restore_index_if_overwritten(text)
    groups = {"community": [], "listing": []}
    for k in sorted_keys(decks):
        if k.startswith("community/"):
            # 2026-11-11 錨文字帶「社區名＋社區分析」（Google 從首頁連到社區頁時讀得到）
            groups["community"].append(card(k, decks[k], "看" + esc(decks[k].get("name")) + "社區分析"))
        else:
            groups["listing"].append(card(k, decks[k], "看物件簡報"))

    def repl(m):
        items = groups.get(m.group(2))
        if items is None:
            return m.group(0)
        body = "\n".join(items) if items else "<li>整理中</li>"
        return m.group(1) + "\n" + body + "\n" + m.group(4)

    new = MARK.sub(repl, text)
    INDEX.write_text(new, encoding="utf-8")


def lastmod(rel, decks_key=None, decks=None):
    if decks_key and decks and decks.get(decks_key, {}).get("updated"):
        return decks[decks_key]["updated"]
    d = git("log", "-1", "--format=%cs", "--", rel).strip()
    return d or None


def build_sitemap(decks):
    pages = []  # (path, lastmod)
    pages.append(("", lastmod("index.html")))
    for sub in ("map", "about", "buy", "sell"):  # buy/sell：2026-11-13 板橋買房／賣房指南
        if (ROOT / sub / "index.html").exists():
            pages.append((sub + "/", lastmod(sub)))
    for d in sorted((ROOT / "area").iterdir()) if (ROOT / "area").is_dir() else []:  # 2026-11-13 區域買房頁
        if (d / "index.html").exists():
            pages.append(("area/" + d.name + "/", lastmod("area/" + d.name)))
    for d in sorted((ROOT / "community").iterdir()) if (ROOT / "community").is_dir() else []:
        if (d / "index.html").exists():
            key = "community/" + d.name
            pages.append((key + "/", lastmod(key, key, decks)))
    for d in sorted(ROOT.glob("S*")):
        if d.is_dir() and re.fullmatch(r"S\d+", d.name) and (d / "index.html").exists():
            pages.append((d.name + "/", lastmod(d.name, d.name, decks)))

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, lm in pages:
        lines.append("  <url>")
        lines.append("    <loc>" + html.escape(SITE + quote(path, safe="/")) + "</loc>")
        if lm:
            lines.append("    <lastmod>" + lm + "</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"sitemap.xml：{len(pages)} 個網址")


def main():
    decks = load_decks()
    build_index(decks)
    build_sitemap(decks)


if __name__ == "__main__":
    main()
