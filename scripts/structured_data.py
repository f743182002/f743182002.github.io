#!/usr/bin/env python3
"""網站結構化資料（JSON-LD）、noscript 摘要與 /llms.txt 產生器。

林津陞 2026-11-03：社區簡報的資訊多半只在畫面上（3D、日照、步行地圖、影片口播），
AI 搜尋讀不到。這支把「頁面本身已經有的資料」整理成 JSON-LD 寫進各頁 <head>，
不另外編造：

- 社區／物件簡報：頁面內嵌的 window.DECK／window.SITE（事實欄、步行路線、優點與留意）
- data/communities.json：生活圈、學區（一律註明以教育局公告為準）
- data/videos.json：YouTube 影片（網址、上傳日、章節）
- data/narration.json：影片每段的畫面字卡與口播稿（指揮艙發布時寫入）
- decks.json：頁面清單與更新日

唯一一份程式在 9b-houseflow-tools/tools/property-deck/structured_data.py；
指揮艙發布時把它複製到網站 repo 的 scripts/，GitHub Actions 每次 push 都重跑，
所以改 videos.json 加影片網址也會自動更新各頁。只用標準函式庫（Actions 要能跑）。

2026-11-11 起社區頁另外產生看得見的分析文章（<article id="analysis">，接在章節列後面）、問句型 title／h1／meta
（「○○可以買嗎？交通、日照、學區與看屋重點」）、地圖頁的社區文章清單；社區頁不再放 noscript 摘要。
使照起造人／承造人來自 data/permits.json（社區版發布時由 deck_engine.publish_permit 依使照存根判讀寫入）。
文章、常見問題（與 FAQPage 同一份）一律不寫金額（含實價登錄單價）、屋齡數字；有一頁沒過整批不寫。

法遵：JSON-LD 一樣算廣告。不寫售價、單價、屋齡數字；禁用詞與最高級擋下；
聯絡只放手機與 LINE；揭露四行固定；距離只用頁面已有的步行路線，註明實際以現場為準。

用法：python structured_data.py <網站資料夾> [--check]
  --check：只檢查，不寫檔；有頁面需要更新就回傳 1。
"""
import html
import json
import math
import re
import sys
from pathlib import Path
from urllib.parse import quote

SITE = 'https://banqiaoasheng.com/'
BRAND = '板橋阿陞聊房'
AGENT_ID = SITE + '#agent'
PERSON_ID = SITE + 'about/#lin'
WEBSITE_ID = SITE + '#website'
YOUTUBE_CHANNEL = 'https://www.youtube.com/channel/UC_OqNkkqQTT6L7xLZZvlRfQ'
LINE_URL = 'https://line.me/R/ti/p/%40banqiao.asheng'
MOBILE = '+886-925-635-678'
# 揭露四行（峯＝U+5CEF；林津陞是營業員，不是經紀人）
DISCLOSURE = ['全國不動產板橋加盟店', '經紀業 非凡不動產有限公司',
              '經紀人 謝政峯（99）北縣字第002181號', '營業員 林津陞（99）登字第148103號']
DISCLOSURE_TEXT = '｜'.join(DISCLOSURE)
WALK_NOTE = '步行路線為估算，實際以現場為準'
SCHOOL_NOTE = '學區以教育局公告為準'

LD_MARK = re.compile(r'<!-- LD:START -->.*?<!-- LD:END -->\n?', re.S)
NS_MARK = re.compile(r'<!-- LD-SUMMARY:START -->.*?<!-- LD-SUMMARY:END -->\n?', re.S)
LD_SCRIPT = re.compile(r'[ \t]*<script type="application/ld\+json">.*?</script>\n?', re.S)
# 2026-11-11 社區頁看得見的分析文章（Google 讀得到的純 HTML 文字）、頁首「看文字版分析」連結、地圖頁社區文章清單
ART_MARK = re.compile(r'<!-- ARTICLE:START -->.*?<!-- ARTICLE:END -->\n?', re.S)
ART_LINK_MARK = re.compile(r'<!-- ARTICLE-LINK:START -->.*?<!-- ARTICLE-LINK:END -->', re.S)
MAPLINKS_MARK = re.compile(r'<!-- MAPLINKS:START -->.*?<!-- MAPLINKS:END -->\n?', re.S)
# 頁尾完整揭露（SOP 3.1 完整版；峯＝U+5CEF）與買方攻略引流兩行（SOP 4.10，2026-10-29）
FULL_DISCLOSURE = ['全國不動產板橋加盟店', '經紀業｜非凡不動產有限公司',
                   '經紀人｜謝政峯（99）北縣字第002181號', '營業員｜林津陞（99）登字第148103號']
GUIDE_LINES = ['☆預約看屋請聯絡：林津陞 0925-635-678',
               '加官方 LINE：@banqiao.asheng，聊天室輸入「攻略」，系統自動傳送《買房避坑攻略》電子檔（約2萬字／38頁）']

# 禁用詞：deck_engine.BANNED ＋ SEO_BANNED（tests/test_structured_data.py 檢查兩邊一致），
# 再加 JSON-LD 專用：估價、最高級、來源內部用語、店電話。
BANNED = ['免費估價', '免費鑑價', '專業估價', '保證獲利', '穩賺', '保證增值', '投報率', '保證核貸', '增建', '頂樓加蓋', '加蓋', '夾層', '可隔套',
          '大空間', '空間大', '大坪數', '坪數大', '最便宜', '最高價收購', 'CP值最高', '屋主急售', '急售', '賠售', '低於行情', '捷運宅', '絕佳', '第一品牌', '全台最低',
          '塔樓', '雙塔', '街屋',
          '保證可裝', '一定可以', '一定能裝', '管委會不能拒絕', '不能拒絕', '不得拒絕', '友善',  # 2026-11-04 第四階段充電樁
          '保證', '增值', '估價', '鑑價',
          '最划算', '最好', '最佳', '最優', '最頂級', '最熱門', '首選', '唯一',
          '後台', 'houseflow', 'HouseFlow', '根據後台', '8258', '8100']
# 屋齡數字（2026-11-04 第二階段）：「屋齡29年」「屋齡：29 年」「屋齡約三十年」「30年屋」「三十年老屋」「29年屋齡」。
# 寫死的文字（title、meta、og、JSON-LD、llms.txt、noscript、YouTube、字幕、配音、591 文案）一律不可有；
# 只有簡報頁／地圖由瀏覽器即時計算的屋齡欄可以顯示（那段在 <script> 裡，靜態掃描不掃 script，見 static_text()）。
# deck_engine、site_map 共用這一條。
AGE_NUM = r'[\d０-９一二三四五六七八九十兩]'
AGE = re.compile(r'屋齡[\s：:〕】）)」約為近達已滿逾超過]*' + AGE_NUM + r'|' + AGE_NUM + r'+\s*年(?:老|新成)?屋(?![頂主況內外前後])|' + AGE_NUM + r'+\s*年屋齡')
# 價格與屋齡：句子裡有這些就整句拿掉（實價登錄的筆數、期間可以留，金額不留）
MONEY = re.compile(r'\d[\d,.]*\s*(?:萬(?![字人次筆個])|元|億)|[一二三四五六七八九十百千兩]+萬(?![字人次筆個])|萬元|每坪|單價|總價|售價|開價|價格|價位|行情|'
                   + AGE.pattern)
# 2026-11-04 林津陞「社區分析可以寫單價了」：社區分析（社區簡報、社區影片字幕／旁白、YouTube 說明欄、社區頁 JSON-LD）
# 可以寫實價登錄成交單價（萬/坪），例如「近一年成交單價約 60～68 萬/坪」「每坪大約八十三萬到一百萬」。
# 仍然不行：物件（listing）的售價／單價／總價、任何地方的屋齡數字、社區分析的總價／售價（只開放單價）。
# 同日補充：單價要寫清楚車位坪數與價格有沒有分算（參考樂居「成交單價皆已扣除車位的坪數及價格」）——
# 同一段文字（或同章節附註）要有 PARKING_NOTE 這類說明；不准自己估車位價拆分，只能照實價登錄原始資料有沒有拆分。
_PNUM = r'[\d０-９零一二兩三四五六七八九十百千,.]+'
_PRANGE = _PNUM + r'(?:\s*萬元?)?(?:\s*(?:～|~|〜|－|-|–|到|至)\s*' + _PNUM + r')?'
UNIT_PRICE = re.compile(
    r'(?:成交)?(?:單價|每坪)(?:[\s:：]*(?:約為|大約|大概|約|多在|落在|介於|在|為|是)?\s*' + _PRANGE + r'\s*萬元?(?:\s*[/／]\s*坪)?)?'
    r'(?:\s*[（(]\s*萬元?\s*[/／]\s*坪\s*[）)])?'
    r'|' + _PRANGE + r'\s*萬元?\s*(?:[/／]\s*坪|一坪)'
    r'|[（(]\s*萬元?\s*[/／]\s*坪\s*[）)]')
# 「含車位」只在講單價／拆分時才算（「57～69 坪（含車位）」講的是面積，不算車位分算說明）
PARKING_NOTE = re.compile(r'扣除車位(?:的)?(?:坪數)?(?:\s*[及與和、]\s*(?:車位)?價格)?|(?:單價|拆分)[^。；，,]{0,8}含車位|含車位(?:價格|價)'
                          r'|車位(?:價格)?(?:未|沒有|已|有)(?:另外)?拆分'
                          r'|(?:未|沒有|已|有)拆分(?:的)?車位(?:價格)?')


# 單價沒寫車位說明時補的預設說明（林津陞 2026-11-04：「沒寫不用擋住阿 就寫是含車位計算 無分算」）
DEFAULT_PARKING_NOTE = '單價含車位計算，車位未分算'


def unit_price_missing_parking(text, context=''):
    """社區分析：text 寫了單價（萬/坪、每坪、單價），text 與 context（同段、同章節附註）卻沒寫車位有沒有分算 → 回傳那段單價文字。"""
    m = UNIT_PRICE.search(str(text or ''))
    if m and not PARKING_NOTE.search(str(text or '') + ' ' + str(context or '')):
        return m[0]
    return None


def money_hit(text, community=False, context=''):
    """有不能寫的金額／屋齡就回傳 match（或字串）；沒有回 None。
    community=True：實價登錄單價（萬/坪）放行，但要有車位分算說明（PARKING_NOTE，可在 context）；總價、售價、屋齡照擋。"""
    t = str(text or '')
    if community:  # 單價沒寫車位說明不擋（林津陞 2026-11-04「沒寫不用擋住阿 就寫是含車位計算 無分算」；deck_engine 會自動補說明）
        t = PARKING_NOTE.sub(' ', UNIT_PRICE.sub(' ', t))
    m = MONEY.search(t)
    return m[0] if m else None


def static_text(page_html):
    """網頁的靜態文字：去掉 <script>、<style> 的內容（瀏覽器即時計算的屋齡欄只在 script 裡），留下 title、meta、og、
    JSON-LD 以外的 HTML 文字與屬性。JSON-LD（type=application/ld+json）另由 audit() 檢查，也一起留著掃。"""
    s = re.sub(r'<script(?![^>]*application/ld\+json)[^>]*>.*?</script>', ' ', str(page_html or ''), flags=re.S | re.I)
    return re.sub(r'<style[^>]*>.*?</style>', ' ', s, flags=re.S | re.I)


def static_age_problems(page_html):
    """靜態 HTML（含 noscript 摘要、meta、og、JSON-LD）不可有屋齡數字。回傳找到的字串清單。"""
    return [m[0] for m in AGE.finditer(static_text(page_html))]


# ---------------------------------------------------------------------- 文字
def clean(text, community=False):
    """去掉含金額、屋齡、禁用詞的句子；回傳剩下的文字（可能是空字串）。
    community=True（社區頁）：寫了實價登錄單價而且整段有車位分算說明的句子留著（money_hit）。"""
    text = re.sub(r'\s+', ' ', str(text or '')).strip()
    if not text:
        return ''
    parts = re.split(r'(?<=[。！？!?；])', text)
    keep = [p for p in parts if p.strip() and not money_hit(p, community, text) and not any(w in p for w in BANNED)]
    out = ''.join(keep).strip()
    if community and unit_price_missing_parking(out):  # 沒寫車位說明 → 補預設（林津陞 2026-11-04「就寫是含車位計算 無分算」）
        note = f'（{DEFAULT_PARKING_NOTE}）'
        out = out[:-1] + note + out[-1] if out[-1:] in '。！？；' else out + note
    return out


def clean_segments(text, sep='｜', community=False):
    """畫面字卡「A｜B・C」：逐段去掉有金額或禁用詞的段落（community 見 clean）。"""
    segs = [s.strip() for s in re.split(r'[｜|]', str(text or '')) if s.strip()]
    return sep.join(s for s in segs if not money_hit(s, community, text) and not any(w in s for w in BANNED))


def audit(graph, community=False):
    """最後一道：整份 JSON-LD 不可有金額、屋齡、禁用詞（社區頁的單價見 money_hit）。"""
    problems = []

    def visit(v, path):
        if isinstance(v, dict):
            for k, x in v.items():
                visit(x, f'{path}.{k}')
        elif isinstance(v, list):
            for i, x in enumerate(v):
                visit(x, f'{path}[{i}]')
        elif isinstance(v, str) and not v.startswith('http'):
            m = money_hit(v, community)
            if m:
                problems.append(f'{path} 含金額／屋齡「{m}」')
            for w in BANNED:
                if w in v:
                    problems.append(f'{path} 含禁用詞「{w}」')
    visit(graph, '$')
    return problems


def sentences(items):
    """幾段文字接成一段：每段補句號，不出現「。；」。"""
    return ''.join(x if x.endswith(('。', '！', '？')) else x + '。' for x in items if x)


def page_url(key):
    return SITE + (quote(key) + '/' if key else '')


def grab(text, name):
    """讀頁面內嵌的 window.NAME={...}；沒有就回 None。"""
    i = text.find('window.' + name + '=')
    if i < 0:
        return None
    j = text.index('{', i)
    return json.JSONDecoder().raw_decode(text[j:])[0]


def head_end(text):
    """<head> 結束位置。簡報範本沒有 <head> 標籤（瀏覽器自動補），以第一個 <body>／<header>／<main> 為界。"""
    i = text.find('</head>')
    if i >= 0:
        return i
    m = re.search(r'\n<(?:body|header|main)\b', text)
    return m.start() + 1 if m else 0


def head_of(text):
    return text[:head_end(text)]


def meta_content(text, name):
    m = re.search(r'<meta name="' + name + r'" content="([^"]*)"', head_of(text))
    return html.unescape(m[1]) if m else ''


def title_of(text):
    m = re.search(r'<title>([^<]*)</title>', head_of(text))
    return html.unescape(m[1]).strip() if m else ''


def walk_text(w):
    m = w.get('m')
    if m == 0:
        return '就在社區旁'
    dist = f"步行約{w['w']:,}公尺、" if w.get('w') else ''
    return f'{dist}約{m}分鐘' if m is not None else ''


KIND = {'station': '捷運站', 'bus_stop': '公車站', 'convenience': '便利商店', 'supermarket': '超市',
        'marketplace': '市場', 'park': '公園', 'school': '學校', 'hospital': '醫療院所', 'library': '圖書館'}


def walk_rows(site):
    """跟簡報畫面一樣：便利商店、超市各只列最近兩家。"""
    rows, seen = [], {}
    for w in (site or {}).get('walk') or []:
        k = w.get('k')
        if k in ('convenience', 'supermarket'):
            seen[k] = seen.get(k, 0) + 1
            if seen[k] > 2:
                continue
        if not w.get('n') or w.get('m') is None:
            continue
        rows.append(w)
    return rows


def walk_name(w):
    n = w['n']
    if w.get('k') == 'station':
        codes = '、'.join(w.get('codes') or [])
        n = f'捷運{n}' + (f'（{codes}）' if codes else '') + (f"{w['exit']}號出口" if w.get('exit') else '')
    return n


# ---------------------------------------------------------------------- 共用節點
def agent_nodes():
    """RealEstateAgent 與營業員本人。每一頁都放同一份（同一個 @id、同樣內容），不另寫不同版本。"""
    agent = {
        '@type': 'RealEstateAgent', '@id': AGENT_ID,
        # 2026-11-10 個人品牌：LOGO、分享圖用 assets/brand/（不用全國不動產 LOGO）；公司名稱只留在法定揭露（description、parentOrganization）
        'name': BRAND, 'alternateName': ['林津陞', '阿陞'],
        'url': SITE, 'logo': SITE + 'assets/brand/logo.png', 'image': SITE + 'assets/brand/og-1200x630.png',
        'description': '新北市板橋區的社區分析與看屋服務。' + DISCLOSURE_TEXT + '。',
        'telephone': MOBILE,
        'contactPoint': [
            {'@type': 'ContactPoint', 'telephone': MOBILE, 'contactType': '預約看屋', 'availableLanguage': 'zh-TW'},
            {'@type': 'ContactPoint', 'contactType': 'LINE 官方帳號 @banqiao.asheng', 'url': LINE_URL, 'availableLanguage': 'zh-TW'}],
        'areaServed': {'@type': 'AdministrativeArea', 'name': '新北市板橋區',
                       'containedInPlace': {'@type': 'AdministrativeArea', 'name': '新北市'}},
        'parentOrganization': {
            '@type': 'Organization', 'name': '非凡不動產有限公司', 'alternateName': '全國不動產板橋加盟店',
            'description': '經紀業',
            'employee': {'@type': 'Person', 'name': '謝政峯', 'jobTitle': '經紀人',
                         'hasCredential': {'@type': 'EducationalOccupationalCredential', 'name': '不動產經紀人證書',
                                           'identifier': '（99）北縣字第002181號'}}},
        'employee': {'@id': PERSON_ID},
        'sameAs': [YOUTUBE_CHANNEL],
    }
    person = {
        '@type': 'Person', '@id': PERSON_ID, 'name': '林津陞', 'alternateName': '阿陞',
        'jobTitle': '營業員', 'url': SITE + 'about/', 'image': SITE + 'about/lin-portrait.png',
        'telephone': MOBILE, 'worksFor': {'@id': AGENT_ID},
        'hasCredential': {'@type': 'EducationalOccupationalCredential', 'name': '不動產經紀營業員',
                          'identifier': '（99）登字第148103號'},
        'knowsLanguage': 'zh-TW', 'sameAs': [YOUTUBE_CHANNEL],
    }
    website = {'@type': 'WebSite', '@id': WEBSITE_ID, 'name': BRAND, 'url': SITE, 'inLanguage': 'zh-Hant-TW',
               'publisher': {'@id': AGENT_ID}}
    return [website, agent, person]


def breadcrumb(url, items):
    return {'@type': 'BreadcrumbList', '@id': url + '#breadcrumb',
            'itemListElement': [{'@type': 'ListItem', 'position': i + 1, 'name': n, 'item': u}
                                for i, (n, u) in enumerate(items)]}


def admin_area(county, district):
    county = county or '新北市'
    node = {'@type': 'AdministrativeArea', 'name': county}
    if district:
        node = {'@type': 'AdministrativeArea', 'name': district, 'containedInPlace': node}
    return node


def split_area(area):
    """decks.json 的 area／DECK.eyebrow「新北市板橋區・莊敬路」→ ('新北市','板橋區','莊敬路')"""
    a, _, road = str(area or '').partition('・')
    m = re.match(r'^(新北市|臺北市|台北市)?(\S*?區)?(.*)$', a.strip())
    return (m[1] or ''), (m[2] or ''), (road or m[3] or '').strip()


# ---------------------------------------------------------------------- 影片
def hms(sec):
    sec = int(round(float(sec)))
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    return 'PT' + (f'{h}H' if h else '') + (f'{m}M' if m else '') + f'{s}S'


def video_nodes(url, place_id, name, videos, narration, page_key):
    """VideoObject：YouTube 網址與章節；有口播稿就放 transcript，每段畫面字卡放成 Clip。"""
    out = []
    narr = narration or {}
    com = str(page_key or '').startswith('community/')  # 社區頁：單價（附車位分算說明）放行
    for v in videos or []:
        vid = v['id']
        watch = f'https://www.youtube.com/watch?v={vid}'
        thumb = f'https://i.ytimg.com/vi/{vid}/maxresdefault.jpg'
        node = {'@type': 'VideoObject', '@id': f'{url}#video-{vid}',
                'name': clean_segments(v.get('name'), '｜', com) or name,
                'url': watch, 'embedUrl': f'https://www.youtube.com/embed/{vid}',
                'thumbnailUrl': [thumb, f'https://i.ytimg.com/vi/{vid}/hqdefault.jpg'],
                'uploadDate': v['uploadDate'], 'inLanguage': 'zh-TW',
                'author': {'@id': PERSON_ID}, 'publisher': {'@id': AGENT_ID}, 'about': {'@id': place_id},
                'isPartOf': {'@type': 'CreativeWorkSeries', 'name': BRAND, 'url': YOUTUBE_CHANNEL}}
        if v.get('seconds'):
            node['duration'] = hms(v['seconds'])
        if v.get('contentUrl'):
            node['contentUrl'] = v['contentUrl']
        if v.get('format'):
            node['videoFrameSize'] = v['format']
        scenes = (narr.get('scenes') or []) if narr.get('video') == vid else []
        clips, t = [], 0.0
        for sc in scenes:
            d = float(sc.get('d') or 0)
            title = clean_segments(sc.get('t'), '｜', com)
            screen = clean_segments(sc.get('s'), '｜', com)
            if title and d:
                clip = {'@type': 'Clip', 'name': title, 'startOffset': int(t), 'endOffset': int(t + d),
                        'url': f'{watch}&t={int(t)}s'}
                if screen:
                    clip['description'] = '畫面字卡：' + screen
                clips.append(clip)
            t += d
        if not clips:
            for start, title in v.get('chapters') or []:
                title = clean_segments(title, community=com)
                if title:
                    clips.append({'@type': 'Clip', 'name': title, 'startOffset': int(start), 'url': f'{watch}&t={int(start)}s'})
            for i, c in enumerate(clips):
                end = clips[i + 1]['startOffset'] if i + 1 < len(clips) else v.get('seconds')
                if end:
                    c['endOffset'] = int(end)
        if clips:
            node['hasPart'] = clips
        chapters = '、'.join(c['name'] for c in clips[:10])
        desc = v.get('summary') or (f'{name}的影片介紹' + (f'，段落：{chapters}' if chapters else '') + '。')
        node['description'] = clean(desc + f'互動簡報：{url}', com) or name
        transcript = clean(''.join(sc.get('v') or '' for sc in scenes), com)
        if transcript:
            node['transcript'] = transcript
        image = {'@type': 'ImageObject', '@id': f'{url}#thumb-{vid}', 'contentUrl': thumb, 'url': thumb,
                 'caption': f'{name}影片封面', 'representativeOfPage': False}
        if v.get('thumbText'):
            image['description'] = '圖上文字：' + clean_segments(v['thumbText'], community=com)
        node['thumbnail'] = {'@id': image['@id']}
        out += [node, image]
    return out


# ---------------------------------------------------------------------- FAQ
def faq(url, qa):
    items = [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}}
             for q, a in qa if q and a]
    if not items:
        return []
    return [{'@type': 'FAQPage', '@id': url + '#faq', 'mainEntity': items, 'isPartOf': {'@id': url + '#webpage'},
             'author': {'@id': PERSON_ID}}]


def sun_text(narration, community=False):
    for sc in (narration or {}).get('scenes') or []:
        if '日照' in str(sc.get('t') or ''):
            return clean(sc.get('v'), community)
    return ''


# ---------------------------------------------------------------------- 社區／物件簡報（property-deck 產生的頁面）
def fact_rows(deck, listing=False):
    """DECK.facts 的 [標題, 數值, 單位] → (標題, 文字)；價格、費用、屋齡不列。"""
    out = []
    for r in deck.get('facts') or []:
        if not r or len(r) < 3:
            continue
        label = str(r[0]).strip()
        value = re.sub(r'\s+', ' ', f'{r[1]} {r[2]}').strip()
        value = re.sub(r'(?<=[一-鿿\d])\s+(?=[一-鿿\d（(%])', '', value)
        if not value or re.search(r'屋齡|價|費|貸', label) or MONEY.search(value):
            continue
        out.append((label, value))
    return out


def _fit(chunks, limit=120):
    """依序加入句子，超過字數上限的就跳過（第一句一定留）。同 deck_engine._fit。"""
    out = ''
    for i, c in enumerate(c for c in chunks if c):
        if i == 0 or len(out + c) <= limit:
            out += c
    return out


def deck_seo(deck, facts, walks, listing, county, district, road):
    """2026-11-02 以前發布的簡報沒有 SEO 標題與摘要：依頁面資料補（寫法同 deck_engine.seo_text）。"""
    name = str(deck.get('name') or '').strip()
    town = re.sub(r'區$', '', district) or county.rstrip('市')
    f = dict(facts)
    if listing:
        floor = deck.get('floor')
        title = f'{name} {floor}F 物件分析｜{town}{road}｜{BRAND}'
        head = f'{name}位於{county}{district}{road}' + (f"，{deck['subtitle']}" if deck.get('subtitle') else '') + '。'
        tail = ['物件分析整理日照模擬、步行地圖與周邊實價登錄。', '資料以現場及地政登記為準。']
    else:
        n = re.search(r'(\d+)', f.get('樓高', ''))
        kind = '大樓' if '大樓' in str(deck.get('subtitle') or '') or (n and int(n[1]) >= 8) else '住宅'
        title = f'{name}社區分析｜{town} {n[1]} 層{kind}｜{BRAND}' if n else f'{name}社區分析｜{town}{road}｜{BRAND}'
        bits = [f['完工'] + '完工' if f.get('完工') else '', f.get('樓高', ''),
                '地下' + f['地下層'] if f.get('地下層') else '', f.get('戶數', '').replace('（全案合計）', '')]
        head = f'{name}位於{county}{district}{road}' + ('，' + '、'.join(b for b in bits if b) if any(bits) else '') + '。'
        tail = ['社區分析整理大樓條件、日照模擬、步行地圖與實價登錄，優點與要留意的地方並列。', '資料依公開資料查證，實際以現場為準。']
    st = next((w for w in walks if w.get('k') == 'station'), None)
    life, seen = [], set()
    for w in walks:
        if w.get('k') in ('convenience', 'supermarket', 'park', 'marketplace') and w['n'] not in seen:
            seen.add(w['n'])
            life.append(f"{w['n']}" + ('就在社區旁' if w['m'] == 0 else f"步行約{w['m']}分鐘"))
    desc = _fit([head, f"捷運{st['n']}" + ('就在社區旁' if st['m'] == 0 else f"步行約{st['m']}分鐘") + '。' if st else '',
                 f"生活圈有{'、'.join(life[:2])}。" if life else ''] + tail)
    return title, clean(desc) or desc


def deck_graph(key, text, ctx):
    deck, site = grab(text, 'DECK'), grab(text, 'SITE')
    listing = not key.startswith('community/')
    com = not listing  # 社區頁：實價登錄單價（附車位分算說明）放行；物件頁照擋
    url = page_url(key)
    entry = ctx['decks'].get(key, {})
    name = str(deck.get('name') or entry.get('name') or '').strip()
    county, district, road = split_area(deck.get('eyebrow') or entry.get('area'))
    comm = ctx['communities'].get(name) if not listing else None
    narration = ctx['narration'].get(key)
    place_id = url + '#place'
    title, desc = title_of(text), meta_content(text, 'description')

    # 地址：社區版用實價登錄查詢範圍（頁面上就有的門牌區段）；物件版只到路名
    street = road
    m = re.search(r'查詢範圍：(?:新北市|臺北市)?(?:\S{1,3}區)?([^，,；]+?)(?:，|,|；)', ''.join(deck.get('dealsText') or []))
    if m and not listing:
        street = m[1].strip()
        if '（' in street and '）' not in street:  # 「360、362號（A～D 棟，…）」被逗號切斷
            street = street.split('（')[0].strip()
    address = {'@type': 'PostalAddress', 'addressCountry': 'TW', 'addressRegion': county or '新北市',
               'addressLocality': district, 'streetAddress': street}
    lat, lon = (comm or {}).get('lat') or deck.get('lat'), (comm or {}).get('lon') or deck.get('lon')

    facts = fact_rows(deck, listing)
    props = [{'@type': 'PropertyValue', 'name': k, 'value': v} for k, v in facts]
    if comm and comm.get('school'):
        props.append({'@type': 'PropertyValue', 'name': '學區', 'value': comm['school'].replace('・', '、'),
                      'description': SCHOOL_NOTE})
    walks = walk_rows(site)
    amen = [{'@type': 'LocationFeatureSpecification', 'name': walk_name(w),
             'value': walk_text(w), 'description': f"{KIND.get(w.get('k'), '生活機能')}；{WALK_NOTE}"} for w in walks]
    for row in deck.get('nearExtra') or []:
        if len(row) >= 3 and row[1]:
            amen.append({'@type': 'LocationFeatureSpecification', 'name': f'{row[0]} {row[1]}',
                         'value': '、'.join(x for x in row[2:] if x)})
    sun = sun_text(narration, com)
    if sun:
        props.append({'@type': 'PropertyValue', 'name': '日照模擬（冬至晴天，示意）', 'value': sun,
                      'description': '太陽位置以天文公式計算，周邊建物高度為估計，實際以現場為準'})

    area_name = (ctx['areas'].get((comm or {}).get('area')) or {}).get('name')
    contained = admin_area(county, district)
    if area_name:
        contained = {'@type': 'Place', 'name': area_name, 'description': '生活圈名稱參考樂居板橋區生活圈分區',
                     'containedInPlace': contained}

    cover = deck.get('cover') or ((deck.get('photos') or [[None]])[0][0])
    caps = {p[0]: p[1] for p in deck.get('photos') or [] if p and len(p) > 1}
    og = (ctx['root'] / key / 'og.jpg').exists()
    graph = []
    if og:
        graph.append({'@type': 'ImageObject', '@id': url + '#cover', 'contentUrl': url + 'og.jpg', 'url': url + 'og.jpg',
                      'width': 1200, 'height': 630,
                      'caption': f"{name}｜{caps.get(cover) or ('社區航照' if not listing else '物件照片')}",
                      'description': clean(deck.get('interiorText'), com) or None})

    place = {'@type': 'Apartment' if listing else 'ApartmentComplex', '@id': place_id,
             'name': f"{name} {deck.get('floor')}F" if listing and deck.get('floor') else name,
             'alternateName': (aliases_of(ctx.get('keywords', {}).get(name), name) or None) if not listing else None,
             'description': clean(deck.get('interiorText') if listing else (deck.get('interiorText') or deck.get('subtitle')), com) or None,
             'url': url, 'address': address,
             'geo': {'@type': 'GeoCoordinates', 'latitude': lat, 'longitude': lon} if lat and lon else None,
             'containedInPlace': contained, 'additionalProperty': props or None, 'amenityFeature': amen or None,
             'image': {'@id': url + '#cover'} if og else None}
    if listing:
        place['containedInPlace'] = {'@type': 'ApartmentComplex', '@id': page_url('community/' + name) + '#place',
                                     'name': name, 'containedInPlace': contained} \
            if ('community/' + name) in ctx['decks'] else contained
        if deck.get('floor'):
            place['floorLevel'] = f"{deck['floor']}F"
        mm = re.search(r'(\d+)房(\d+)廳(\d+)衛', ''.join(f[1] for f in facts))
        if mm:
            place['numberOfRooms'] = int(mm[1])
            place['numberOfBedrooms'] = int(mm[1])
            place['numberOfBathroomsTotal'] = int(mm[3])
        place['photo'] = [{'@type': 'ImageObject', 'caption': clean(c, com)} for pid, c in caps.items() if clean(c, com)]
    else:
        units = next((v for k, v in facts if k == '戶數'), '')
        n = re.match(r'(\d+)\s*戶', units.replace(',', ''))
        if n:
            place['numberOfAccommodationUnits'] = {'@type': 'QuantitativeValue', 'value': int(n[1]), 'unitText': '戶'}
        # 舊簡報的照片說明可能有後來才禁用的字（塔樓、街屋），整句不放
        place['photo'] = [{'@type': 'ImageObject', 'caption': f'{name}｜{clean(c, com)}'} for pid, c in caps.items() if clean(c, com)]
    graph.append({k: v for k, v in place.items() if v not in (None, [], '')})

    videos = video_nodes(url, place_id, name, ctx['videos'].get(key), narration, key)
    pros = [clean(f"{p.get('h')}：{p.get('p')}", com) for p in deck.get('pros') or []]
    cons = [clean(f"{p.get('h')}：{p.get('p')}", com) for p in deck.get('cons') or []]
    stations = [w for w in walks if w.get('k') == 'station'][:3]
    life = [w for w in walks if w.get('k') not in ('station', 'school', 'bus_stop')][:6]
    built = next((v for k, v in facts if k == '完工'), '')
    floors = next((v for k, v in facts if k == '樓高'), '')
    if com:
        street = short_street(street)
        address['streetAddress'] = street
        # 2026-11-11 文章與常見問題（FAQPage 同一份）一律不寫金額：實價登錄單價也拿掉（社區頁其他 JSON-LD 照 11/04 規則）
        sun = sun_text(narration, False)
        pros = [clean(f"{p.get('h')}：{p.get('p')}") for p in deck.get('pros') or []]
        cons = [clean(f"{p.get('h')}：{p.get('p')}") for p in deck.get('cons') or []]
    where = f'{name}位於{county}{district}{street}' + (f'，屬{area_name}' if area_name else '') + \
            (f'，{built}完工' if built else '') + (f'，{floors}' if floors else '') + '。'
    wnote = walk_source(walks) if com else WALK_NOTE
    school = (comm or {}).get('school') or ''
    permit = ctx.get('permits', {}).get(name) if com else None
    qa = [(f'{name}在哪裡？', clean(where, com)),
          (f'{name}到捷運站走路多久？',
           clean('；'.join(f'{walk_name(w)}{walk_text(w)}' for w in stations) + f'。{wnote}。', com) if stations else ''),
          (f'{name}附近的生活機能有哪些？',
           clean('；'.join(f'{walk_name(w)}{walk_text(w)}' for w in life) + f'。{wnote}。', com) if life else ''),
          (f'{name}的學區是哪裡？',
           f"依政府公開資料，{name}的學區為{school.replace('・', '、')}，{SCHOOL_NOTE}。" if school else ''),
          (f'{name}的日照情況如何？', sun),
          (f'{name}有哪些優點？' if not listing else '這個物件有哪些優點？', sentences(pros)),
          (f'看{name}時要留意什麼？' if not listing else '看這個物件時要留意什麼？', sentences(cons))]
    if permit_answer(name, permit):
        qa.insert(1, permit_answer(name, permit))

    art = None
    if com:  # 2026-11-11 社區頁：問句型標題＋看得見的分析文章（title、h1、meta、JSON-LD 同一套文字）
        town = re.sub(r'區$', '', district) or county.rstrip('市')
        st = stations[0] if stations else None
        art = {'kind': 'deck', 'name': name, 'url': url, 'key': key,
               'updated': entry.get('updated'), 'where': clean(where, com), 'area_name': area_name,
               'interior': clean(deck.get('interiorText')), 'interior_h2': clean(deck.get('interiorH2')),
               'facts': facts, 'facts_src': clean(deck.get('factsSrc')), 'permit': permit,
               'stations': [(walk_name(w), walk_text(w)) for w in stations],
               'buses': [(walk_name(w), walk_text(w)) for w in walks if w.get('k') == 'bus_stop'][:2],
               'life': [(walk_name(w), walk_text(w), KIND.get(w.get('k'), '')) for w in life],
               # 興建中、規劃中的路線站點不寫（未完工建設，SOP 3.3／技能 E 類）
               'near_extra': [(f'{r[0]} {r[1]}', '、'.join(x for x in r[2:] if x)) for r in deck.get('nearExtra') or []
                              if len(r) >= 3 and r[1] and not re.search(r'興建中|規劃|未通車|預計', ' '.join(map(str, r)))],
               'schools_walk': [(walk_name(w), walk_text(w)) for w in walks if w.get('k') == 'school'],
               'walk_note': wnote, 'school': school.replace('・', '、'),
               'sun': sun, 'sun_src': clean(deck.get('sunSrc')),
               'pros': hp_rows(deck.get('pros'), False), 'cons': hp_rows(deck.get('cons'), False),
               'deals_h2': clean(deck.get('dealsH2')), 'deals': [x for x in (clean(t) for t in deck.get('dealsText') or []) if x],
               'layouts': deck.get('layouts') or None, 'ev': deck.get('ev') or None,
               'sources': [clean(s) for s in deck.get('sources') or [] if clean(s)],
               'videos': ctx['videos'].get(key) or [], 'image': article_image(ctx, key, text, deck, name),
               'facilities': ctx.get('facilities', {}).get(name),
               'nearby': nearby_communities(ctx, name, (comm or {}).get('lat') or lat, (comm or {}).get('lon') or lon)}
        finish_article(art, ctx.get('keywords', {}).get(name), town + road,
                       f'位於{county}{district}{road}' + (f'，{built}完工' if built else '') +
                       (f"、{floors.replace(' ', '')}" if floors else '') + '。',
                       f'{walk_name(st)}{walk_text(st)}。' if st else '')
        title, desc, qa = art['title'], art['desc'], art['qa']

    if not title or title in GENERIC_TITLES or not desc:
        t2, d2 = deck_seo(deck, facts, walks, listing, county, district, road)
        title = t2 if (not title or title in GENERIC_TITLES) else title
        desc = desc or d2
    page = {'@type': ['WebPage', 'ItemPage'] if listing else 'WebPage', '@id': url + '#webpage', 'url': url,
            'name': title or name, 'headline': art['h1'] if art else None, 'description': desc or None, 'inLanguage': 'zh-Hant-TW',
            'isPartOf': {'@id': WEBSITE_ID}, 'about': {'@id': place_id}, 'mainEntity': {'@id': place_id},
            'primaryImageOfPage': {'@id': url + '#cover'} if og else None,
            'dateModified': entry.get('updated'), 'author': {'@id': PERSON_ID}, 'publisher': {'@id': AGENT_ID},
            'video': [{'@id': n['@id']} for n in videos if n['@type'] == 'VideoObject'] or None,
            'breadcrumb': {'@id': url + '#breadcrumb'}}
    crumbs = [(BRAND, SITE), (name, url)]
    graph = [{k: v for k, v in page.items() if v not in (None, [], '')}] + graph + videos + faq(url, qa) + [breadcrumb(url, crumbs)]
    summary = {'name': place['name'], 'desc': desc, 'facts': facts, 'walks': [(walk_name(w), walk_text(w)) for w in walks],
               'school': comm.get('school') if comm else '', 'pros': pros, 'cons': cons, 'article': art}
    return graph, summary


def simple_community_graph(key, text, ctx):
    """不是 property-deck 產生的社區頁（新濠一滙）：只用 decks.json 與 communities.json。"""
    url = page_url(key)
    entry = ctx['decks'].get(key, {})
    name = entry.get('name') or key.split('/')[-1]
    comm = ctx['communities'].get(name) or {}
    county, district, road = split_area(entry.get('area'))
    place_id = url + '#place'
    area_name = (ctx['areas'].get(comm.get('area')) or {}).get('name')
    contained = admin_area(county, district)
    if area_name:
        contained = {'@type': 'Place', 'name': area_name, 'description': '生活圈名稱參考樂居板橋區生活圈分區',
                     'containedInPlace': contained}
    props = [{'@type': 'PropertyValue', 'name': k, 'value': comm[f]} for k, f in
             (('完工', 'built'), ('樓高', 'floors'), ('戶數', 'units'), ('結構', 'structure')) if comm.get(f)]
    amen = []
    if comm.get('mrt'):
        amen.append({'@type': 'LocationFeatureSpecification', 'name': '捷運', 'value': comm['mrt'], 'description': WALK_NOTE})
    place = {'@type': 'ApartmentComplex', '@id': place_id, 'name': name, 'url': url,
             'description': clean(entry.get('subtitle'), True) or None,
             'address': {'@type': 'PostalAddress', 'addressCountry': 'TW', 'addressRegion': county or '新北市',
                         'addressLocality': district, 'streetAddress': road},
             'geo': {'@type': 'GeoCoordinates', 'latitude': comm['lat'], 'longitude': comm['lon']} if comm.get('lat') else None,
             'containedInPlace': contained, 'additionalProperty': props or None, 'amenityFeature': amen or None}
    videos = video_nodes(url, place_id, name, ctx['videos'].get(key), ctx['narration'].get(key), key)
    pros, cons = [clean(p, True) for p in comm.get('pros') or []], [clean(p, True) for p in comm.get('cautions') or []]
    # 舊格式頁（沒有 DECK）：捷運步行是頁面上 OpenStreetMap 步行路網估算的值
    wnote = 'OpenStreetMap 步行路網規劃，實際以現場為準'
    mrt = clean(comm.get('mrt'), True)
    town = re.sub(r'區$', '', district) or county.rstrip('市')
    built = comm.get('built') or ''
    where = clean(f'{name}位於{county}{district}{road}' + (f'，屬{area_name}' if area_name else '') + '。', True)
    facts = [(k, comm[f]) for k, f in (('完工', 'built'), ('樓高', 'floors'), ('戶數', 'units'), ('結構', 'structure')) if comm.get(f)]
    art = {'kind': 'simple', 'name': name, 'url': url, 'key': key,
           'updated': entry.get('updated'), 'where': where, 'area_name': area_name, 'interior': '', 'interior_h2': '',
           'facts': facts, 'facts_src': '', 'permit': ctx.get('permits', {}).get(name),
           'stations': [('捷運' + mrt.split(' ')[0], ' '.join(mrt.split(' ')[1:]))] if mrt else [], 'buses': [], 'life': [],
           'near_extra': [], 'schools_walk': [], 'walk_note': f'步行距離資料來源：{wnote}',
           'school': (comm.get('school') or '').replace('・', '、'), 'sun': '', 'sun_src': '',
           'pros': [(p, '') for p in pros if p], 'cons': [(p, '') for p in cons if p], 'deals_h2': '', 'deals': [],
           'layouts': None, 'ev': None, 'sources': [], 'videos': ctx['videos'].get(key) or [],
           'facilities': ctx.get('facilities', {}).get(name),
           'nearby': nearby_communities(ctx, name, comm.get('lat'), comm.get('lon'))}
    finish_article(art, ctx.get('keywords', {}).get(name), town + road,
                   f'位於{county}{district}{road}' + (f'，{built}' if built and not re.search(r'\d', built)
                                                     else (f'，{built}完工' if built else '')) + '。',
                   f'捷運{mrt}。' if mrt else '')
    title, h1, desc = art['title'], art['h1'], art['desc']
    page = {'@type': 'WebPage', '@id': url + '#webpage', 'url': url, 'name': title, 'headline': h1, 'description': desc,
            'inLanguage': 'zh-Hant-TW', 'isPartOf': {'@id': WEBSITE_ID}, 'about': {'@id': place_id},
            'mainEntity': {'@id': place_id}, 'dateModified': entry.get('updated'),
            'author': {'@id': PERSON_ID}, 'publisher': {'@id': AGENT_ID},
            'video': [{'@id': n['@id']} for n in videos if n['@type'] == 'VideoObject'] or None,
            'breadcrumb': {'@id': url + '#breadcrumb'}}
    graph = [{k: v for k, v in page.items() if v not in (None, [], '')},
             {k: v for k, v in place.items() if v not in (None, [], '')}] + videos + faq(url, art['qa']) + \
            [breadcrumb(url, [(BRAND, SITE), (name, url)])]
    return graph, {'article': art}


def describe_simple(key, ctx):
    entry = ctx['decks'].get(key, {})
    name = entry.get('name') or key
    comm = ctx['communities'].get(name) or {}
    county, district, road = split_area(entry.get('area'))
    parts = [f'{name}位於{county}{district}{road}' + (f"，{comm['built']}" if comm.get('built') else '') + '。']
    if comm.get('mrt'):
        parts.append(f"{comm['mrt']}。")
    parts.append(f"互動簡報整理{entry.get('subtitle') or '社區資訊'}，實際以現場為準。")
    return clean(''.join(parts), str(key).startswith('community/'))


# ---------------------------------------------------------------------- 獨立物件頁（S21140123：自己的 config.js／photos.js）
def js_strings(src, field):
    m = re.search(field + r"\s*:\s*\[(.*?)\]\s*,\s*\n", src, re.S)
    return re.findall(r"'([^']*)'", m[1]) if m else []


def standalone_listing_graph(key, text, ctx):
    folder = ctx['root'] / key
    cfg = (folder / 'config.js').read_text(encoding='utf-8')
    photos_src = (folder / 'photos.js').read_text(encoding='utf-8') if (folder / 'photos.js').exists() else ''
    url = page_url(key)
    entry = ctx['decks'].get(key, {})
    name = (re.search(r"title:\s*'([^']*)'", cfg) or [None, entry.get('name')])[1]
    county, district, road = split_area(entry.get('area'))
    loc = re.search(r'<p class="hero-location">([^<]*)</p>', text)
    loc_text = html.unescape(loc[1]) if loc else ''
    street = re.sub(r'\s+', '', loc_text.split('·')[0]).replace(district, '') if loc_text else road
    facts = [clean(f) for f in js_strings(cfg, 'facts')]
    facts = [f for f in facts if f]
    rooms = re.findall(r"\{id:'([^']*)',name:'([^']*)',description:'([^']*)'\}", cfg)
    notice = (re.search(r"notice:\s*'([^']*)'", cfg) or [None, ''])[1]
    hero = [html.unescape(x) for x in re.findall(r'<li>([^<]*)</li>', (re.search(r'<ul class="hero-facts">(.*?)</ul>', text, re.S) or [None, ''])[1])]
    place_id = url + '#place'
    photos = []
    if photos_src:
        i = photos_src.index('[')
        for p in json.JSONDecoder().raw_decode(photos_src[i:])[0]:
            photos.append({'@type': 'ImageObject', 'contentUrl': url + 'assets/photos/' + p['file'],
                           'caption': clean(f"{p.get('title')}：{p.get('caption')}") or p.get('title')})
    plan = {'@type': 'FloorPlan', 'name': '格局', 'description': clean('；'.join(f'{n}：{d}' for _, n, d in rooms)) or None}
    if (folder / 'assets' / 'floorplan.jpg').exists():
        plan['layoutImage'] = {'@type': 'ImageObject', 'contentUrl': url + 'assets/floorplan.jpg',
                               'caption': '原始格局圖（概繪圖，未依比例）', 'description': clean(notice) or None}
    mm = re.search(r'(\d+)房(\d+)廳(\d+)衛', ''.join(hero + facts))
    walk = next((h for h in hero if '步行' in h), '')
    place = {'@type': 'Apartment', '@id': place_id, 'name': name, 'url': url,
             'description': clean('；'.join(facts + [h for h in hero if '步行' in h])) or None,
             'address': {'@type': 'PostalAddress', 'addressCountry': 'TW', 'addressRegion': county or '新北市',
                         'addressLocality': district, 'streetAddress': street},
             'containedInPlace': admin_area(county, district),
             'numberOfRooms': int(mm[1]) if mm else None, 'numberOfBedrooms': int(mm[1]) if mm else None,
             'numberOfBathroomsTotal': int(mm[3]) if mm else None,
             'floorLevel': (re.search(r'(\d+F／\d+F)', ''.join(facts)) or [None, None])[1],
             'amenityFeature': [{'@type': 'LocationFeatureSpecification', 'name': '捷運', 'value': walk,
                                 'description': '步行規劃，實際以現場為準'}] if walk else None,
             'accommodationFloorPlan': {k: v for k, v in plan.items() if v},
             'photo': photos or None}
    desc = meta_content(text, 'description')
    videos = video_nodes(url, place_id, name, ctx['videos'].get(key), ctx['narration'].get(key), key)
    page = {'@type': ['WebPage', 'ItemPage'], '@id': url + '#webpage', 'url': url, 'name': name, 'description': desc or None,
            'inLanguage': 'zh-Hant-TW', 'isPartOf': {'@id': WEBSITE_ID}, 'about': {'@id': place_id},
            'mainEntity': {'@id': place_id}, 'dateModified': entry.get('updated'),
            'author': {'@id': PERSON_ID}, 'publisher': {'@id': AGENT_ID},
            'video': [{'@id': n['@id']} for n in videos if n['@type'] == 'VideoObject'] or None,
            'breadcrumb': {'@id': url + '#breadcrumb'}}
    graph = [{k: v for k, v in page.items() if v not in (None, [], '')},
             {k: v for k, v in place.items() if v not in (None, [], '')}] + videos + \
            [breadcrumb(url, [(BRAND, SITE), (name, url)])]
    return graph, None


# ---------------------------------------------------------------------- 首頁、地圖、關於我
def list_items(ctx, prefix):
    keys = sorted((k for k in ctx['decks'] if k.startswith('community/') == (prefix == 'community/')),
                  key=lambda k: ctx['decks'][k].get('updated') or '', reverse=True)
    return [{'@type': 'ListItem', 'position': i + 1, 'url': page_url(k),
             'name': ctx['decks'][k].get('name') + '｜' + (ctx['decks'][k].get('subtitle') or '')}
            for i, k in enumerate(keys)]


def home_graph(text, ctx):
    url = SITE
    lists = [{'@type': 'ItemList', '@id': url + '#communities', 'name': '社區分析互動簡報', 'itemListElement': list_items(ctx, 'community/')},
             {'@type': 'ItemList', '@id': url + '#listings', 'name': '物件簡報', 'itemListElement': list_items(ctx, 'S')}]
    page = {'@type': 'CollectionPage', '@id': url + '#webpage', 'url': url, 'name': title_of(text),
            'description': meta_content(text, 'description'), 'inLanguage': 'zh-Hant-TW',
            'isPartOf': {'@id': WEBSITE_ID}, 'about': {'@id': AGENT_ID}, 'author': {'@id': PERSON_ID},
            'publisher': {'@id': AGENT_ID}, 'hasPart': [{'@id': x['@id']} for x in lists],
            'significantLink': [SITE + 'map/', SITE + 'about/', 'https://tax.banqiaoasheng.com/', 'https://loan.banqiaoasheng.com/']}
    return [page] + lists, None


def map_graph(text, ctx):
    url = SITE + 'map/'
    items = []
    for i, c in enumerate(ctx['communities'].values()):
        u = SITE + quote(c['deck']) if c.get('deck') else None
        area = (ctx['areas'].get(c.get('area')) or {}).get('name')
        node = {'@type': 'ApartmentComplex', 'name': c['name'],
                'geo': {'@type': 'GeoCoordinates', 'latitude': c['lat'], 'longitude': c['lon']},
                'containedInPlace': {'@type': 'Place', 'name': area} if area else None,
                'additionalProperty': [{'@type': 'PropertyValue', 'name': k, 'value': c[f]} for k, f in
                                       (('完工', 'built'), ('樓高', 'floors'), ('戶數', 'units'), ('捷運步行', 'mrt')) if c.get(f)] or None}
        if u:
            node['@id'] = u + '#place'
            node['url'] = u
        items.append({'@type': 'ListItem', 'position': i + 1, 'item': {k: v for k, v in node.items() if v}})
    page = {'@type': 'CollectionPage', '@id': url + '#webpage', 'url': url, 'name': title_of(text),
            'description': meta_content(text, 'description'), 'inLanguage': 'zh-Hant-TW',
            'isPartOf': {'@id': WEBSITE_ID}, 'author': {'@id': PERSON_ID}, 'publisher': {'@id': AGENT_ID},
            'mainEntity': {'@id': url + '#communities'}, 'breadcrumb': {'@id': url + '#breadcrumb'}}
    lst = {'@type': 'ItemList', '@id': url + '#communities', 'name': '板橋商圈地圖上的社區',
           'description': f'座標為建物輪廓中心；捷運步行時間為步行路線估算，實際以現場為準；{SCHOOL_NOTE}。',
           'itemListElement': items}
    return [page, lst, breadcrumb(url, [(BRAND, SITE), ('商圈地圖', url)])], None


def about_graph(text, ctx):
    url = SITE + 'about/'
    page = {'@type': 'ProfilePage', '@id': url + '#webpage', 'url': url, 'name': title_of(text),
            'description': meta_content(text, 'description'), 'inLanguage': 'zh-Hant-TW',
            'isPartOf': {'@id': WEBSITE_ID}, 'mainEntity': {'@id': PERSON_ID}, 'about': {'@id': AGENT_ID},
            'breadcrumb': {'@id': url + '#breadcrumb'}}
    return [page, breadcrumb(url, [(BRAND, SITE), ('關於我', url)])], None


# ---------------------------------------------------------------------- 社區分析文章（2026-11-11）
# 林津陞 2026-11-11 同意：社區頁內容多在 canvas／3D 裡，Google 只讀得到 JSON-LD；在簡報下方加一篇看得見的文章，
# 標題改成買方搜尋的問句（「新巨蛋可以買嗎？交通、日照、學區與看屋重點」）。文章只用頁面已有資料（DECK／SITE、
# communities.json、videos.json、narration.json）與使照存根判讀（data/permits.json）；查不到的整段不寫。
# 每句都過 clean()（金額、屋齡、禁用詞整句拿掉），最後 build_site() 再整篇掃一次，有一頁沒過整批不寫。

def short_street(street):
    """實價登錄查詢範圍「文化路一段188巷31～39號（單號）、總樓層 15／19 層」→「文化路一段188巷31～39號（單號）」。"""
    s = re.split(r'、總樓層|、建築完成|。', str(street or ''))[0].strip()
    return s.rstrip('、，, ')


def walk_source(walks):
    """步行距離出處（SOP 4.2.3：每個距離都要註明資料來源）：SITE.walk 的 wsrc；沒有就寫估算。"""
    srcs = []
    for w in walks or []:
        s = str(w.get('wsrc') or '').strip()
        if s and s not in srcs:
            srcs.append(s)
    return f"步行距離資料來源：{'、'.join(srcs)}，實際以現場為準" if srcs else WALK_NOTE


# 2026-11-11 第二輪（林津陞：「優化成就是買方會搜的關鍵字」）：data/keywords.json 存每個社區的 Google 搜尋自動完成與
# 「其他人也搜尋了」；依搜尋詞出現次數排主題順序，決定 title、h1、h2 問句與 FAQ。只寫有資料的主題（沒資料整題不寫）。
# 房價、行情、租金、增值不寫（法遵）；凶宅、跳樓等負面詞只記在 keywords.json 的 excluded，不進文章。
TOPICS = {  # 主題：（標題用字，搜尋詞裡出現就算一次）
    '捷運': ('捷運', ['捷運', '站', '共構', '交通']),
    '日照': ('日照', ['日照', '採光', '西曬', '座向']),
    '學區': ('學區', ['學區', '國小', '國中', '學校']),
    '車位': ('車位', ['車位', '停車']),
    '公設': ('公設', ['公設', '健身房', '游泳池', '泳池', '操場', '中庭']),
    '管委會': ('管委會', ['管委會', '管理委員會', '管理室', '管理中心', '管理費', '保全']),
    '建商': ('建商', ['建商', '建設', '營造', '起造']),
    '格局': ('格局', ['格局', '平面圖', '坪數', '戶型', '套房']),
    '生活': ('生活機能', ['全家', '全聯', '超市', '市場', '生活', '醫院', '公園']),
    '完工': ('完工年', ['屋齡', '完工', '幾年']),
    '實價': ('實價登錄', ['實價登錄', '實價', '成交']),
}
TOPIC_DEFAULT = list(TOPICS)
NEGATIVE_WORDS = re.compile(r'凶宅|跳樓|上吊|意外|命案|自殺|法拍|釘子戶|災難|車禍|死')


def topic_order(kw):
    """依搜尋詞出現次數排主題（同分照預設順序）。kw 是 keywords.json 的一筆；沒有就用預設順序。"""
    qs = [q for q in (kw or {}).get('queries') or [] if not NEGATIVE_WORDS.search(q)]
    score = {t: sum(1 for q in qs if any(w in q for w in words)) for t, (_, words) in TOPICS.items()}
    return sorted(TOPIC_DEFAULT, key=lambda t: (-score[t], TOPIC_DEFAULT.index(t)))


def question_title(name, labels):
    lab = [x for x in labels if x][:3]
    mid = ('、'.join(lab[:-1]) + '與' + lab[-1]) if len(lab) > 1 else (lab[0] if lab else '看屋重點')
    return f'{name}可以買嗎？優缺點、{mid}｜{BRAND}'


def question_h1(name, place, labels):
    lab = [x for x in labels if x][:5]
    return f'{name}可以買嗎？{place}社區優缺點' + (f"、{'、'.join(lab)}" if lab else '') + '與看屋重點'


def question_desc(name, where, station, labels):
    """meta description：社區名＋「社區分析」開頭（搜尋「○○ 社區分析」對得上），只寫已查證的位置、完工年月、捷運步行。"""
    topics = '、'.join(['優缺點'] + [x for x in labels if x][:5])
    return clean(_fit([f'{name}社區分析：{where}', station, f'整理{topics}，以及看屋要留意的地方。',
                       '資料依政府公開資料查證，實際以現場為準。'], 120))


def _join(items, sep='、'):
    return sep.join(x for x in items if x)


def _sent(text):
    t = str(text or '').strip()
    return t if not t or t[-1] in '。！？' else t + '。'


def _first_sentences(text, n=2):
    parts = [p for p in re.split(r'(?<=[。！？])', str(text or '')) if p.strip()]
    return ''.join(parts[:n]), ''.join(parts[n:])


def webp_size(path):
    """WebP 寬高（標準函式庫讀檔頭：VP8／VP8L／VP8X）；讀不到回 None。"""
    try:
        b = Path(path).read_bytes()[:40]
    except OSError:
        return None
    if b[:4] != b'RIFF' or b[8:12] != b'WEBP':
        return None
    kind = b[12:16]
    if kind == b'VP8 ':
        return int.from_bytes(b[26:28], 'little') & 0x3FFF, int.from_bytes(b[28:30], 'little') & 0x3FFF
    if kind == b'VP8L':
        v = int.from_bytes(b[21:25], 'little')
        return (v & 0x3FFF) + 1, ((v >> 14) & 0x3FFF) + 1
    if kind == b'VP8X':
        return int.from_bytes(b[24:27], 'little') + 1, int.from_bytes(b[27:30], 'little') + 1
    return None


def article_image(ctx, key, text, deck, name):
    """文章「先說結論」配一張簡報封面航照（同資料夾的 WebP），alt 與圖說寫社區名＋畫面內容＋航照出處。"""
    imgs = grab(text, 'IMG') or {}
    cover = deck.get('cover') or 'p1'
    fn = imgs.get(cover)
    if not fn or not re.fullmatch(r'[\w.-]+\.webp', fn):
        return None
    size = webp_size(ctx['root'] / key / fn)
    if not size:
        return None
    cap = next((clean(p[1]) for p in deck.get('photos') or [] if p and p[0] == cover and len(p) > 1), '') or '社區航照'
    return {'src': fn, 'w': size[0], 'h': size[1], 'alt': f'{name}航照｜{cap}',
            'caption': f'{name}｜{cap}（航照：內政部國土測繪中心正射影像，現況以現場為準）'}


def article_sections(a):
    """文章的問答章節：每節 = {topic, q(h2 問句), lead(直接講結論的第一段，也是 FAQ 答案), body(HTML)}。
    資料只來自 a（頁面已有資料＋使照判讀）；沒資料的主題不產生。順序：結論 → 依關鍵字排的主題 → 優缺點 → 看屋確認。"""
    e = html.escape
    name, f = a['name'], dict(a['facts'])
    secs = {}

    # 位置、完工、樓層
    built, floors = f.get('完工', ''), f.get('樓高', '')
    if built or floors:
        bits = _join([f'{built}完工' if built and re.search(r'\d', built) else built, floors,
                      f"地下{f['地下層']}" if f.get('地下層') else '',
                      re.sub(r'（全案合計）$', '', f.get('戶數', '')), f.get('棟數', ''), f.get('結構', '')], '、')
        rows = [(k, re.sub(r'（全案合計）$', '', v) if v.startswith('全案') else v) for k, v in a['facts']]
        p = a.get('permit')
        if p:
            rows = [r for r in rows if r[0] not in ('建設', '營造')]
            rows.append(('使用執照', p['license']))
        body = '<table><tbody>' + ''.join(f'<tr><th scope="row">{e(k)}</th><td>{e(v)}</td></tr>' for k, v in rows) + '</tbody></table>'
        notes = _join([a.get('facts_src'), '使用執照依新北市政府工務局使用執照存根影像。' if p else ''], '')
        if notes:
            body += f'<p class="sa-note">{e(notes)}</p>'
        secs['完工'] = {'q': f'{name}是哪一年完工的？幾層樓、幾戶？', 'lead': clean(f'{name}{bits}。'), 'body': body}

    # 捷運
    st = a['stations']
    if st:
        lead = '；'.join(f'{n}{t}' for n, t in st) + '。'
        body = ''
        if a['buses']:
            body += '<p>最近的公車站：' + '；'.join(f'{e(n)}{e(t)}' for n, t in a['buses']) + '。</p>'
        body += f'<p class="sa-note">{e(a["walk_note"])}。</p>'
        secs['捷運'] = {'q': f'{name}到捷運站走路多久？', 'lead': clean(lead), 'body': body}

    # 生活機能
    if a['life'] or a['near_extra']:
        lead = '步行可到：' + '；'.join(f'{n}{t}' for n, t, _ in a['life'][:5]) + '。' if a['life'] else ''
        body = ('<ul>' + _li([(f'{n}（{k}）' if k else n, t) for n, t, k in a['life']]) + '</ul>') if a['life'] else ''
        if a['near_extra']:
            body += '<ul>' + _li(a['near_extra']) + '</ul>'
        if a['life']:
            body += f'<p class="sa-note">{e(a["walk_note"])}。地點名稱與位置參考政府開放資料與連鎖店官方門市查詢。</p>'
        if lead:
            secs['生活'] = {'q': f'{name}生活機能方便嗎？超市、超商、市場走路多久？', 'lead': clean(lead), 'body': body}

    # 學區
    if a['school']:
        body = '<p>學區每年可能調整，入學前記得再向學校或教育局確認。</p>'
        if a['schools_walk']:
            body += '<p>走路到學校：' + '；'.join(f'{e(n)}{e(t)}' for n, t in a['schools_walk']) + f'（{e(a["walk_note"])}）。</p>'
        secs['學區'] = {'q': f'{name}學區是哪裡？', 'lead': f'依政府公開資料，{name}的學區為{a["school"]}，實際以教育局公告為準。', 'body': body}

    # 日照
    if a['sun']:
        lead, rest = _first_sentences(a['sun'], 2)
        body = (f'<p>{e(rest)}</p>' if rest else '') + \
            '<p>日照會因為面向、樓層、前後棟距差很多，看屋時建議上午、下午各去一次，站到窗邊看實際的採光與視野。</p>' + \
            (f'<p class="sa-note">{e(a["sun_src"])}</p>' if a.get('sun_src') else '')
        secs['日照'] = {'q': f'{name}日照好嗎？冬天曬得到太陽嗎？', 'lead': lead, 'body': body}

    # 車位
    ev = a.get('ev') or {}
    car = []
    if f.get('停車位'):
        car.append(f"依使照資料，停車位為{f['停車位']}")
    if f.get('機車位'):
        car.append(f"機車位{f['機車位']}")
    if f.get('車位'):
        car.append(f"車位類型：{f['車位']}")
    deal_car = next((x for x in a['deals'] if re.match(r'^\s*車位[：:]', x)), '')
    if deal_car:
        car.append('實價登錄交易中，' + re.sub(r'^\s*車位[：:]\s*', '', re.split(r'(?<=[。])', deal_car)[0]).rstrip('。'))
    if car:
        asks = [x for x in (clean(y) for y in ev.get('ask') or []) if x]
        body = '<p>看屋時建議確認車位的產權登記方式、位置與進出動線，機車位是否需要另外申請。</p>'
        if asks:
            body += '<h3>電動車充電：可以先問管委會的事</h3><ul>' + ''.join(f'<li>{e(x)}</li>' for x in asks) + '</ul>'
            note = re.sub(r'[；;，,、]$', '。', clean(ev.get('note')))
            if note:
                body += f'<p class="sa-note">{e(note)}</p>'
        secs['車位'] = {'q': f'{name}有車位嗎？車位有多少？', 'lead': clean('；'.join(car) + '。'), 'body': body}

    # 公設（2026-11-11：簡報事實欄沒有的，用 data/facilities.json 補；只收建商資料或本店物件照片佐證的項目）
    fac = a.get('facilities') or {}
    if fac.get('items') and not f.get('公設'):
        f['公設'] = '、'.join(fac['items'])
    if fac.get('ratio') and not f.get('公設比'):
        f['公設比'] = fac['ratio']
    if f.get('公設') or f.get('公設比'):
        lead = _join([f"公設有{f['公設']}" if f.get('公設') else '', f"公設比{f['公設比']}" if f.get('公設比') else ''], '；') + '。'
        body = ''.join(f'<p>{e(x)}</p>' for x in (clean(t) for t in fac.get('notes') or []) if x)
        body += '<p>公設實際開放時間與使用規定，以管委會公告與規約為準，看屋時可以請管理室帶看。</p>'
        if fac.get('src'):
            body += f'<p class="sa-note">公設資料來源：{e(clean(fac["src"]))}</p>'
        secs['公設'] = {'q': f'{name}公設有哪些？公設比多少？', 'lead': clean(lead), 'body': body}

    # 管委會
    if f.get('管理'):
        secs['管委會'] = {'q': f'{name}有管委會嗎？管理方式怎麼樣？', 'lead': clean(f"管理方式：{f['管理']}。"),
                        'body': '<p>看屋時可以向管理室確認：社區規約、管理費收取方式、公共基金與近期公共修繕計畫，'
                                '以及有沒有進行中的社區爭議。</p>'}

    # 建商
    p = a.get('permit')
    ans = permit_answer(name, p)
    if ans:
        secs['建商'] = {'q': ans[0], 'lead': ans[1], 'body': ''}
    elif f.get('建設') or f.get('營造'):
        secs['建商'] = {'q': f'{name}是哪家建設公司蓋的？',
                      'lead': clean(_join([f"建設：{f['建設']}" if f.get('建設') else '', f"營造：{f['營造']}" if f.get('營造') else ''], '；') + '。'),
                      'body': ''}

    # 格局（實價登錄戶型分布）
    lay = a.get('layouts') or {}
    rows = [r for r in lay.get('rows') or [] if r.get('count')]
    if rows:
        top = max(rows, key=lambda r: r['count'])
        mp = top.get('main_ping') or []
        lead = (f"依實價登錄申報資料（{lay.get('cutoff') or ''}），{name}有成交紀錄的住宅以{top['label']}最多（{top['count']}筆）"
                + (f"，主建物約{mp[0]}～{mp[1]}坪" if len(mp) == 2 else '') + '。')
        body = ('<table><thead><tr><th scope="col">房數</th><th scope="col">筆數</th><th scope="col">主建物坪數</th></tr></thead><tbody>' +
                ''.join(f'<tr><td>{e(str(r.get("label")))}</td><td>{e(str(r.get("count")))}</td><td>'
                        + (e(f'{r["main_ping"][0]}～{r["main_ping"][1]} 坪') if len(r.get('main_ping') or []) == 2 else '')
                        + '</td></tr>' for r in rows) + '</tbody></table>')
        notes = ''.join(x for x in (clean(y) for y in lay.get('notes') or []) if x)
        if notes:
            body += f'<p class="sa-note">{e(notes)}</p>'
        secs['格局'] = {'q': f'{name}格局有哪些？幾房、幾坪？', 'lead': clean(lead), 'body': body}

    # 實價登錄（只寫筆數與期間；金額句已拿掉）
    deals = []
    for x in a['deals']:
        x = re.sub(r'^這[是些][^。]*。', '', x.strip()).strip()
        x = re.sub(r'[；;，,、]$', '。', x)
        if x and not re.match(r'^\s*車位[：:]', x):
            deals.append(x)
    if deals:
        lead, rest = _first_sentences(deals[0], 1)
        body = ''.join(f'<p>{e(x)}</p>' for x in ([rest] if rest else []) + deals[1:])
        secs['實價'] = {'q': f'{name}實價登錄有幾筆成交？', 'lead': lead, 'body': body}

    out = []
    # 結論（第一節）
    pros_h = [h or b for h, b in a['pros']][:3]
    cons_h = [h or b for h, b in a['cons']][:3]
    lead = _sent(a['where']) + (f'走到{st[0][0]}{st[0][1]}。' if st else '') + \
        (f"優點是{'、'.join(pros_h)}；" if pros_h else '') + (f"要留意的是{'、'.join(cons_h)}。" if cons_h else '')
    lead = lead.replace('；。', '。').rstrip('；') + ('' if lead.endswith('。') else '。')
    body = '<p>適不適合，要看你最在意的是什麼。下面把買方最常搜尋的問題一題一題整理，每題第一段先講結論，數字都標了出處，實際狀況還是以現場為準。</p>'
    im = a.get('image')
    if im:
        body += (f'<figure><img src="{e(im["src"], quote=True)}" alt="{e(im["alt"], quote=True)}" width="{im["w"]}" height="{im["h"]}" '
                 f'loading="lazy" decoding="async"><figcaption>{e(im["caption"])}</figcaption></figure>')
    if a.get('interior'):
        body += f'<h3>{e(a.get("interior_h2") or "從空中看" + name)}</h3><p>{e(a["interior"])}</p>'
    out.append({'topic': '結論', 'q': f'{name}可以買嗎？先說結論', 'lead': clean(lead), 'body': body})
    order = a.get('topic_order') or TOPIC_DEFAULT
    out += [dict(secs[t], topic=t) for t in order if t in secs]
    # 優缺點、看屋確認
    if a['pros'] or a['cons']:
        lead = (f"優點：{'；'.join(pros_h)}。" if pros_h else '') + (f"要留意：{'；'.join(cons_h)}。" if cons_h else '')
        body = ''.join((f'<h3>{e(h)}</h3>' if h else '') + (f'<p>{e(b)}</p>' if b else '') for h, b in a['pros'])
        out.append({'topic': '優缺點', 'q': f'{name}優缺點有哪些？', 'lead': clean(lead), 'body': body})
    if a['cons']:
        lead = f"看{name}要先確認的是：{'；'.join(cons_h)}。"
        body = ''.join((f'<h3>{e(h)}</h3>' if h else '') + (f'<p>{e(b)}</p>' if b else '') for h, b in a['cons'])
        out.append({'topic': '看屋', 'q': f'{name}缺點是什麼？看屋時要確認什麼？', 'lead': clean(lead), 'body': body})
    return [s for s in out if s['lead']]


KEYWORD_SEEDS = ['', '優缺點', '可以買嗎', '缺點', '日照', '捷運', '學區', '管委會', '車位', '公設', '建商', '評價', '社區',
                 '格局', '坪數']


def fetch_keywords(name, seeds=KEYWORD_SEEDS, pause=0.4, bases=None):
    """Google 搜尋框自動完成（社區名＋空白、＋優缺點…），只留含社區名的詞；負面詞放 excluded。只用標準函式庫。
    bases：keywords.json 有 alias 時改用別名查（「大禾 」會帶出大禾拉麵、大禾設計這類同名店家）。"""
    import time
    import urllib.request
    got = []
    for b, s in [(b, s) for b in (bases or [name]) for s in seeds]:
        q = f'{b} {s}'.strip() + ('' if s else ' ')
        u = 'https://suggestqueries.google.com/complete/search?client=chrome&hl=zh-TW&gl=tw&q=' + quote(q)
        d = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=20)
                       .read().decode('utf-8', 'replace'))
        got += [re.sub(r'\s+', '', x) for x in d[1] if re.sub(r'\s+', '', x) not in got]
        time.sleep(pause)
    mine = [x for x in dict.fromkeys(got) if name in x and not re.search(r'[乐价录卖电]', x)]
    return {'queries': [x for x in mine if not NEGATIVE_WORDS.search(x)],
            'excluded': [x for x in mine if NEGATIVE_WORDS.search(x)]}


def save_keywords(root, name, fetched=None):
    """data/keywords.json 合併新抓的自動完成（保留原本人工查的「其他人也搜尋了」等）。"""
    kf = Path(root) / 'data' / 'keywords.json'
    data = json.loads(kf.read_text(encoding='utf-8')) if kf.exists() else {}
    old = data.get(name) or {}
    new = fetched if fetched is not None else fetch_keywords(name, bases=aliases_of(old, name) or None)
    entry = {**({'alias': old['alias']} if old.get('alias') else {}),
             'queries': list(dict.fromkeys((old.get('queries') or []) + new['queries'])),
             'related': old.get('related') or [],
             'excluded': list(dict.fromkeys((old.get('excluded') or []) + new['excluded'])),
             'checked': __import__('datetime').date.today().isoformat(),
             'source': old.get('source') or 'Google 搜尋自動完成（社區名＋空白與優缺點、可以買嗎、日照、捷運、學區、管委會、車位、公設、建商等）'}
    if entry != old:
        data[name] = entry
        write_json(kf, data)
    return entry


def aliases_of(kw, name):
    """keywords.json 的 alias：買方實際搜尋的社區名（例：大禾 → 興富發大禾；2026-11-11 Google 自動完成幾乎都是「興富發大禾」）。"""
    al = (kw or {}).get('alias') or []
    al = [al] if isinstance(al, str) else al
    return [x.strip() for x in al if isinstance(x, str) and x.strip() and x.strip() != name and not NEGATIVE_WORDS.search(x)]


def display_name(name, alias):
    """title／h1 用的名字：別名含原名（興富發大禾 ⊃ 大禾）就用別名，否則「原名（別名）」。"""
    if not alias:
        return name
    return alias[0] if name in alias[0] else f'{name}（{alias[0]}）'


def finish_article(a, kw, place, where_short, station):
    """依關鍵字排序主題，產生章節、title、h1、meta description、FAQ（＝章節問句＋第一段）。"""
    a['topic_order'] = topic_order(kw)
    a['keywords'] = [q for q in (kw or {}).get('queries') or [] if not NEGATIVE_WORDS.search(q)]
    a['alias'] = aliases_of(kw, a['name'])
    a['sections'] = article_sections(a)
    # 標題不放「實價登錄」「完工年」：搜這兩個詞的人多半要看房價，文章不寫價格，放標題會答非所問（章節照留）
    labels = [TOPICS[s['topic']][0] for s in a['sections'] if s['topic'] in TOPICS and s['topic'] not in ('實價', '完工')]
    disp = display_name(a['name'], a['alias'])
    a['title'] = question_title(disp, labels)
    a['h1'] = question_h1(disp, place, labels)
    a['desc'] = question_desc(disp, where_short, station, labels)
    a['qa'] = [(s['q'], s['lead']) for s in a['sections']]
    return a


def hp_rows(items, community=True):
    """DECK.pros／cons 的 {h, p} → [(標題, 內文)]，兩段各自過 clean()。"""
    out = []
    for p in items or []:
        h, b = clean(p.get('h'), community), clean(p.get('p'), community)
        if h or b:
            out.append((h, b))
    return out


def nearby_communities(ctx, name, lat, lon, n=4):
    """附近社區：地圖上有簡報的社區，依直線距離取最近 n 個（只拿來排序，不寫距離數字）。"""
    rows = []
    for c in ctx['communities'].values():
        if c.get('name') == name or not c.get('deck') or not c.get('lat') or not lat:
            continue
        d = math.hypot(float(c['lat']) - float(lat), (float(c['lon']) - float(lon)) * 0.91)
        rows.append((d, c))
    rows.sort(key=lambda x: x[0])
    out = []
    for _, c in rows[:n]:
        entry = ctx['decks'].get(str(c['deck']).strip('/'), {})
        county, district, road = split_area(entry.get('area'))
        out.append({'name': c['name'], 'href': '/' + quote(str(c['deck']).strip('/')) + '/',
                    'where': f"{district}{c.get('road') or road}"})
    return out


def permit_entry(annex):
    """存根判讀 annex.json → data/permits.json 的一筆。只收看得清楚的名稱（「看不清楚」「姓名欄空白」不收），去掉括號裡的負責人姓名。"""
    if not annex or not annex.get('字號'):
        return None

    def names(v):
        out = []
        for x in (v if isinstance(v, list) else [v] if v else []):
            x = str(x).strip()
            if not x or re.match(r'(看不清楚|姓名欄|空白|不明)', x):
                continue
            x = re.sub(r'等$', '', re.split(r'[（(]', x)[0].strip()).strip()
            if x and re.search(r'(公司|工程|營造|建設|開發)', x):
                out.append(x)
        return out
    e = {'license': str(annex['字號']).strip(), 'builder': names(annex.get('起造人')),
         'contractor': names(annex.get('承造人')), 'src': '新北市政府工務局使用執照存根影像'}
    return e if e['builder'] or e['contractor'] else None


# 2026-11-11 林津陞核准（大禾「可以 寫上興富發」）：存根影像起造人欄空白時，可在 permits.json 人工加
# "builder_open": ["…"]＋"builder_open_src": "參考政府公開資料"（新北市使照開放資料的起造人欄）。只限起造人名稱，
# 層數、戶數、車位等數字一律仍以存根影像為準；存根看得到起造人（builder 有值）時不用開放資料。
OPEN_KEYS = ('builder_open', 'builder_open_src')


def builder_open(permit):
    """存根起造人空白時，permits.json 人工標註的開放資料起造人（只收公司名稱）。"""
    if not permit or permit.get('builder'):
        return []
    v = permit.get('builder_open') or []
    v = [v] if isinstance(v, str) else v
    return [x.strip() for x in v if isinstance(x, str) and re.search(r'(公司|工程|營造|建設|開發)', x) and not re.search(r'\d', x)]


def save_permit(root, name, annex):
    """社區版發布時把使照起造人／承造人寫進總站 data/permits.json（文章「基本資料」與常見問題用）；判讀不到就不動。
    人工加的開放資料起造人（builder_open／builder_open_src）重新發布時保留。"""
    e = permit_entry(annex)
    if not e:
        return None
    pf = Path(root) / 'data' / 'permits.json'
    data = json.loads(pf.read_text(encoding='utf-8')) if pf.exists() else {}
    old = data.get(name) or {}
    if old.get('license') == e['license']:
        e.update({k: old[k] for k in OPEN_KEYS if old.get(k)})
    if data.get(name) != e:
        data[name] = e
        write_json(pf, data)
    return e


def permit_answer(name, permit):
    if not permit:
        return None
    b, c = '、'.join(permit.get('builder') or []), '、'.join(permit.get('contractor') or [])
    bo = '、'.join(builder_open(permit))
    if bo:  # 存根起造人欄空白：起造人照開放資料寫，註明出處
        src = permit.get('builder_open_src') or '參考政府公開資料'
        lead = f"起造人（建設公司）是{bo}（{src}；使用執照存根影像的起造人欄空白）"
        if c:
            return (f'{name}是哪家建設公司、營造廠蓋的？', f"{lead}，使用執照（{permit['license']}）登記的承造人（營造廠）是{c}。")
        return (f'{name}是哪家建設公司蓋的？', f"{lead}。")
    if b and c:
        return (f'{name}是哪家建設公司、營造廠蓋的？', f"使用執照（{permit['license']}）登記的起造人是{b}，承造人（營造廠）是{c}。")
    if c:
        return (f'{name}是哪家營造廠蓋的？', f"使用執照（{permit['license']}）登記的承造人（營造廠）是{c}。")
    return (f'{name}的起造人是誰？', f"使用執照（{permit['license']}）登記的起造人是{b}。")


ARTICLE_CSS = (
    '#analysis{background:#fff;color:#0F2233;border-top:1px solid #D7E6EF;padding:32px 16px 56px;'
    'font:16px/1.85 system-ui,"PingFang TC","Noto Sans TC","Microsoft JhengHei",sans-serif;text-align:left}'
    '#analysis .sa-in{max-width:760px;margin:0 auto}'
    '#analysis h1{font-size:25px;line-height:1.45;margin:4px 0 10px;font-weight:800;color:#0F2233;letter-spacing:.01em}'
    '#analysis h2{font-size:20px;line-height:1.5;margin:34px 0 10px;padding-top:14px;border-top:1px solid #D7E6EF;color:#0F2233}'
    '#analysis h3{font-size:17px;line-height:1.5;margin:18px 0 4px;color:#0F2233}'
    '#analysis p{margin:0 0 12px}#analysis ul,#analysis ol{margin:0 0 12px;padding-left:1.4em}#analysis li{margin:2px 0}'
    '#analysis a{color:#0F2233;text-decoration:underline;text-decoration-color:#0369A1;text-underline-offset:3px}'
    '#analysis .sa-meta,#analysis .sa-note{color:#3F4F5E;font-size:14px}'
    '#analysis .sa-lead{font-weight:600}'
    '#analysis figure{margin:10px 0 14px}#analysis figure img{display:block;width:100%;max-width:560px;height:auto;'
    'border-radius:6px;border:1px solid #D7E6EF}#analysis figcaption{font-size:13px;color:#3F4F5E;margin-top:4px}'
    '#analysis .sa-toc{background:#F2F8FB;border:1px solid #D7E6EF;border-radius:8px;padding:10px 14px;margin:8px 0 4px;font-size:15px}'
    '#analysis .sa-toc p{margin:0 0 4px;font-weight:600}#analysis .sa-toc ol{margin:0}'
    '#analysis .sa-kicker{display:inline-block;font-size:13px;color:#3F4F5E;border:1px solid #D7E6EF;border-radius:999px;padding:1px 10px}'
    '#analysis table{border-collapse:collapse;width:100%;margin:0 0 12px;font-size:15px}'
    '#analysis th,#analysis td{border-bottom:1px solid #D7E6EF;padding:6px 8px;text-align:left;vertical-align:top;'
    'white-space:normal;overflow-wrap:anywhere;font:inherit;color:#0F2233}'
    '#analysis th{white-space:nowrap;color:#3F4F5E;font-weight:600;width:7.5em}'
    '#analysis .sa-video{display:block;max-width:480px;text-decoration:none}'
    '#analysis .sa-video img{display:block;width:100%;height:auto;border-radius:6px;border:1px solid #D7E6EF}'
    '#analysis .sa-contact{background:#F2F8FB;border:1px solid #D7E6EF;border-radius:8px;padding:14px 16px;margin:12px 0}'
    '#analysis .sa-disc{font-size:13px;line-height:1.75;color:#3F4F5E;border-top:1px solid #D7E6EF;margin-top:28px;padding-top:12px}'
    '@media (max-width:520px){#analysis h1{font-size:22px}#analysis h2{font-size:19px}}')
# 簡報頁（property-deck）桌機版 html,body 固定 100% 高、簡報撐滿一個畫面：文章接在第一個畫面下面（往下捲才看到），
# 不擠壓簡報；手機版（860px 以下）本來就整頁捲動，文章照順序接在章節列後面。
ARTICLE_DECK_CSS = ('@media (min-width:861px){body{position:relative}#analysis{position:absolute;top:100%;left:0;right:0}}'
                    '@media (max-width:860px){#analysis{padding-left:0;padding-right:0}}')


def _li(rows):
    return ''.join(f'<li>{html.escape(a)}' + (f'：{html.escape(b)}' if b else '') + '</li>' for a, b in rows if a)


def article_html(a):
    """社區分析文章（純 HTML，不靠 JS）。a 由 deck_graph／simple_community_graph 準備，每段文字都已過 clean()。"""
    e = html.escape
    name = a['name']
    out = [f'<p class="sa-kicker">社區分析・文字版</p>', f'<h1>{e(a["h1"])}</h1>',
           f'<p class="sa-meta">整理：林津陞（阿陞）' + (f'｜更新：{e(a["updated"])}' if a.get('updated') else '') + '</p>']
    if a.get('alias'):  # 網路上常用的另一個名字（同一個社區）
        out.append(f'<p>{e(name)}在網路上也常寫成「' + '」「'.join(e(x) for x in a['alias']) + '」，指的是同一個社區。</p>')
    secs = a.get('sections') or []
    out.append(f'<p>帶看{e(name)}時，買方最常問的就是下面這幾題。我把查過的資料整理在這篇，每一題第一段先講結論，'
               '跟上面的互動簡報（3D 模型、日照模擬、步行地圖）是同一份資料，數字都標了出處，實際狀況還是要以現場為準。</p>')
    if len(secs) > 2:  # 目錄：讓讀者（與搜尋引擎）一眼看到這篇回答哪些問題
        out.append('<nav class="sa-toc" aria-label="本文問題"><p>這篇回答：</p><ol>' +
                   ''.join(f'<li><a href="#q-{i + 1}">{e(x["q"])}</a></li>' for i, x in enumerate(secs)) + '</ol></nav>')
    for i, x in enumerate(secs):
        out.append(f'<h2 id="q-{i + 1}">{e(x["q"])}</h2>')
        out.append(f'<p class="sa-lead">{e(x["lead"])}</p>')
        if x.get('body'):
            out.append(x['body'])

    vids = [v for v in a['videos'] if re.fullmatch(r'[\w-]{11}', str(v.get('id') or ''))]
    if vids:
        out.append(f'<h2>{e(name)}社區分析影片</h2>')
        for v in vids:
            vt = clean_segments(v.get('name'), '｜') or f'{name}社區分析'
            out.append(f'<p><a class="sa-video" href="https://www.youtube.com/watch?v={v["id"]}" target="_blank" rel="noopener">'
                       f'<img src="https://i.ytimg.com/vi/{v["id"]}/hqdefault.jpg" alt="{e(vt, quote=True)}" width="480" height="360" loading="lazy">'
                       f'</a></p><p>▶ <a href="https://www.youtube.com/watch?v={v["id"]}" target="_blank" rel="noopener">{e(vt)}</a>（YouTube）</p>')

    # 附近社區（內部連結，錨文字＝社區名＋社區分析）
    if a['nearby']:
        out.append(f'<h2>{e(name)}附近社區</h2>')
        out.append('<ul>' + ''.join(f'<li><a href="{e(c["href"], quote=True)}">{e(c["name"])}社區分析</a>'
                                    + (f'（{e(c["where"])}）' if c.get('where') else '') + '</li>' for c in a['nearby']) + '</ul>')
        out.append('<p>想一次比較位置，可以看<a href="/map/">板橋商圈地圖</a>，或回<a href="/">首頁</a>看全部社區分析。</p>')

    # 聯絡與完整揭露
    out.append(f'<h2>想看{e(name)}？</h2>')
    out.append(f'<div class="sa-contact"><p>想知道{e(name)}目前有沒有房子在賣，歡迎聯絡。</p>'
               f'<p>☆預約看屋請聯絡：林津陞 <a href="tel:0925635678">0925-635-678</a><br>'
               f'加官方 LINE：<a href="https://line.me/R/ti/p/%40banqiao.asheng" target="_blank" rel="noopener">@banqiao.asheng</a>，'
               '聊天室輸入「攻略」，系統自動傳送《買房避坑攻略》電子檔（約2萬字／38頁）</p></div>')
    src = '；'.join(x.rstrip('。') for x in a.get('sources') or [])
    out.append('<div class="sa-disc"><p>' + '<br>'.join(e(x) for x in FULL_DISCLOSURE) + '</p>'
               '<p>' + (f'資料來源：{e(src)}。' if src else '本文資料參考政府公開資料。') +
               '步行距離與日照為規劃與模擬結果，學區以教育局公告為準，房屋資訊仍須以現場、產權資料及正式文件為準。</p></div>')
    css = ARTICLE_CSS + (ARTICLE_DECK_CSS if a['kind'] == 'deck' else '')
    return ('<!-- ARTICLE:START -->\n<style>' + css + '</style>\n'
            f'<article id="analysis" aria-label="{e(name)}社區分析文字版"><div class="sa-in">\n'
            + '\n'.join(x for x in out if x) + '\n</div></article>\n<!-- ARTICLE:END -->\n')


def article_text(block):
    """文章的純文字（法遵掃描用）：去掉 style 與標籤。"""
    s = re.sub(r'<style[^>]*>.*?</style>', ' ', block, flags=re.S)
    return html.unescape(re.sub(r'<[^>]+>', ' ', s))


def article_problems(block):
    """整篇再掃一次：金額（社區頁單價規則同 money_hit）、屋齡數字、禁用詞、店電話。"""
    t = article_text(block)
    probs = []
    for line in re.split(r'[。\n]', t):
        m = money_hit(line)
        if m:
            probs.append(f'含金額「{m}」')
    probs += [f'含屋齡數字「{m[0]}」' for m in AGE.finditer(t)]
    probs += [f'含禁用詞「{w}」' for w in BANNED if w in t]
    for must in ('謝政峯（99）北縣字第002181號', '林津陞（99）登字第148103號', '非凡不動產有限公司', '0925-635-678', '@banqiao.asheng'):
        if must not in t:
            probs.append(f'少了「{must}」')
    return probs


def set_head_text(head, title, desc):
    """社區頁：<title>、meta description、og:title／og:description（有才換）跟 JSON-LD 同一套文字。"""
    a = lambda s: html.escape(s, quote=True)
    head = re.sub(r'<title>[^<]*</title>', lambda m: f'<title>{html.escape(title)}</title>', head, count=1)
    for attr, val in (('name="description"', desc), ('property="og:title"', title), ('property="og:description"', desc),
                      ('name="twitter:title"', title), ('name="twitter:description"', desc)):
        head = re.sub(r'(<meta ' + re.escape(attr) + r' content=")[^"]*(")', lambda m: m[1] + a(val) + m[2], head, count=1)
    return head


def insert_article(rest, block):
    """文章接在章節列（<nav class="rail">）後面；找不到章節列就放在 </body> 前或檔尾。"""
    rest = ART_MARK.sub('', rest)
    m = re.search(r'<nav class="rail"[^>]*>\s*</nav>\n?', rest)
    if m:
        at = m.end()
        return rest[:at] + ('' if rest[at - 1] == '\n' else '\n') + block + rest[at:]
    i = rest.rfind('</body>')
    return (rest[:i] + block + rest[i:]) if i >= 0 else rest + block


def insert_article_link(rest):
    """頁首「看商圈地圖」旁加「看文字版分析」（跳到文章）。"""
    rest = ART_LINK_MARK.sub('', rest)
    link = '<!-- ARTICLE-LINK:START --><a href="#analysis">看文字版分析</a><!-- ARTICLE-LINK:END -->'
    m = re.search(r'href="/map/">看商圈地圖</a>', rest)
    if not m:
        return rest
    return rest[:m.end()] + link + rest[m.end():]


def map_links_block(ctx):
    """商圈地圖頁的靜態社區文章清單（地圖本身是 JS 畫的，爬蟲看不到連結）。錨文字＝社區名＋社區分析。"""
    items = []
    for c in ctx['communities'].values():
        if not c.get('deck'):
            continue
        key = str(c['deck']).strip('/')
        if not (ctx['root'] / key / 'index.html').exists():
            continue
        area = (ctx['areas'].get(c.get('area')) or {}).get('name') or ''
        items.append((area, c['name'], f'<li><a href="/{quote(key)}/">{html.escape(c["name"])}社區分析</a>'
                      + (f'（{html.escape(area)}・{html.escape(c.get("road") or "")}）' if area else '') + '</li>'))
    items.sort(key=lambda x: (x[0], x[1]))
    return ('<!-- MAPLINKS:START -->\n<style>.maplinks{margin:28px auto 8px;max-width:900px}.maplinks h2{font-size:22px;margin:0 0 8px}'
            '.maplinks ul{columns:2 260px;padding-left:1.2em;margin:8px 0 0}.maplinks li{margin:3px 0;break-inside:avoid}</style>\n'
            '<section class="wrap maplinks" id="community-articles" aria-label="社區分析文章">'
            '<h2>社區分析文章</h2><p>每個社區一篇：交通、日照、學區、生活機能與看屋重點，點社區名就能看完整分析。</p>'
            '<ul>' + ''.join(x[2] for x in items) + '</ul></section>\n<!-- MAPLINKS:END -->\n')


def apply_map_links(text, ctx):
    text = MAPLINKS_MARK.sub('', text)
    i = text.find('<footer class="site-foot"')
    if i < 0:
        return text
    return text[:i] + map_links_block(ctx) + text[i:]


# ---------------------------------------------------------------------- 寫進 HTML
def ld_block(graph):
    doc = {'@context': 'https://schema.org', '@graph': agent_nodes() + graph}
    body = json.dumps(doc, ensure_ascii=False, indent=1).replace('</', '<\\/')
    return '<!-- LD:START -->\n<script type="application/ld+json">\n' + body + '\n</script>\n<!-- LD:END -->\n'


def summary_block(s, url):
    e = html.escape
    li = lambda rows: ''.join(f'<li>{e(a)}：{e(b)}</li>' for a, b in rows)
    parts = [f'<h1>{e(s["name"])}</h1>']
    if s['desc']:
        parts.append(f'<p>{e(s["desc"])}</p>')
    if s['facts']:
        parts.append(f'<h2>基本資料</h2><ul>{li(s["facts"])}</ul>')
    if s['walks']:
        parts.append(f'<h2>步行可達（{WALK_NOTE}）</h2><ul>{li(s["walks"])}</ul>')
    if s['school']:
        parts.append(f'<p>學區：{e(s["school"].replace("・", "、"))}（{SCHOOL_NOTE}）</p>')
    if any(s['pros']):
        parts.append('<h2>優點</h2><ul>' + ''.join(f'<li>{e(p)}</li>' for p in s['pros'] if p) + '</ul>')
    if any(s['cons']):
        parts.append('<h2>看屋時留意</h2><ul>' + ''.join(f'<li>{e(p)}</li>' for p in s['cons'] if p) + '</ul>')
    parts.append(f'<p>林津陞 0925-635-678｜LINE @banqiao.asheng<br>{e("｜".join(DISCLOSURE))}</p>')
    return ('<!-- LD-SUMMARY:START -->\n<noscript><section style="max-width:760px;margin:16px auto;padding:0 16px">'
            + ''.join(parts) + '</section></noscript>\n<!-- LD-SUMMARY:END -->\n')


GENERIC_TITLES = ('社區分析簡報', '物件分析簡報')  # 2026-11-02 SEO 以前發布的簡報


def head_extras(head, key, ctx, graph):
    """沒有 description／canonical 的頁面補上（值取自 JSON-LD 的 WebPage）。"""
    page = next((n for n in graph if n.get('@id', '').endswith('#webpage')), {})
    add = []
    if 'name="description"' not in head:
        d = page.get('description') or describe_simple(key, ctx)
        if d:
            add.append(f'<meta name="description" content="{html.escape(d, quote=True)}">')
    if 'rel="canonical"' not in head:
        add.append(f'<link rel="canonical" href="{page_url(key)}">')
    return add


def apply(text, key, graph, summary, ctx):
    end = head_end(text)
    head, rest = text[:end], text[end:]
    head = LD_MARK.sub('', head)
    head = LD_SCRIPT.sub('', head)  # 舊的手寫 JSON-LD（首頁、地圖）由這裡統一產生
    page = next((n for n in graph if n.get('@id', '').endswith('#webpage')), {})
    m = re.search(r'<title>([^<]*)</title>\n?', head)
    if m and m[1].strip() in GENERIC_TITLES and page.get('name') not in (None, '', m[1].strip()):
        head = head.replace(m[0], f"<title>{html.escape(page['name'])}</title>\n", 1)
        m = re.search(r'<title>([^<]*)</title>\n?', head)
    extras = head_extras(head, key, ctx, graph)
    if extras and m:
        head = head[:m.end()] + ('' if head[m.end() - 1] == '\n' else '\n') + '\n'.join(extras) + '\n' + head[m.end():]
    elif extras:
        head += '\n'.join(extras) + '\n'
    art = (summary or {}).get('article')
    if art:  # 社區頁：標題與摘要換成問句型（與 JSON-LD WebPage、文章 h1 同一套）
        head = set_head_text(head, art['title'], art['desc'])
    if not head.endswith('\n'):
        head += '\n'
    head += ld_block(graph)
    rest = NS_MARK.sub('', rest)
    if art:
        # 2026-11-11：社區頁改放看得見的文章，不再放 noscript 摘要（同一份內容出現兩次，且 noscript 內容搜尋引擎權重低）
        return head + insert_article_link(insert_article(rest, article_html(art)))
    if summary:
        # 有 <body> 放在 body 開頭；簡報範本沒有 html/head/body 標籤，放在 <main> 前（一定在 body 裡）
        b = re.search(r'<body[^>]*>\n?', rest)
        at = b.end() if b else (re.search(r'\n<main\b', rest) or re.search(r'\n<header\b', rest)).start() + 1
        rest = rest[:at] + summary_block(summary, page_url(key)) + rest[at:]
    return head + rest


def page_graph(key, text, ctx):
    if key == '':
        return home_graph(text, ctx)
    if key == 'map':
        return map_graph(text, ctx)
    if key == 'about':
        return about_graph(text, ctx)
    if grab(text, 'DECK') is not None:
        return deck_graph(key, text, ctx)
    if (ctx['root'] / key / 'config.js').exists():
        return standalone_listing_graph(key, text, ctx)
    return simple_community_graph(key, text, ctx)


def load_ctx(root):
    root = Path(root)
    rd = lambda p, d: json.loads((root / p).read_text(encoding='utf-8')) if (root / p).exists() else d
    comm = rd('data/communities.json', {})
    return {'root': root, 'decks': rd('decks.json', {}),
            'communities': {c['name']: c for c in comm.get('communities', [])},
            'areas': {a['id']: a for a in comm.get('areas', [])},
            'videos': rd('data/videos.json', {}), 'narration': rd('data/narration.json', {}),
            'permits': rd('data/permits.json', {}), 'keywords': rd('data/keywords.json', {}),
            'facilities': rd('data/facilities.json', {})}


def pages(root):
    root = Path(root)
    keys = [''] + [k for k in ('map', 'about') if (root / k / 'index.html').exists()]
    if (root / 'community').is_dir():
        keys += ['community/' + d.name for d in sorted((root / 'community').iterdir()) if (d / 'index.html').exists()]
    keys += [d.name for d in sorted(root.glob('S*')) if d.is_dir() and re.fullmatch(r'S\d+', d.name) and (d / 'index.html').exists()]
    return keys


def llms_txt(ctx, descs):
    lines = [f'# {BRAND}（banqiaoasheng.com）', '',
             '> 新北市板橋區（含中和）社區分析資料站：每個社區一份互動簡報，整理大樓條件、3D 日照模擬、捷運與生活機能步行路線、'
             '學區與實價登錄筆數，優點與看屋要留意的地方並列。資料依政府公開資料查證，步行路線為估算，學區以教育局公告為準，實際以現場為準。',
             '', f'整理：林津陞（營業員）｜{DISCLOSURE_TEXT}', '聯絡：手機 0925-635-678｜LINE @banqiao.asheng', '',
             '每頁 <head> 都有 schema.org JSON-LD（ApartmentComplex、VideoObject 含口播稿、FAQPage），內容與畫面相同。', '',
             '## 網站', '',
             f'- [首頁]({SITE}): 社區分析與物件簡報清單',
             f'- [商圈地圖]({SITE}map/): 各社區位置、生活圈、完工年、捷運步行時間',
             f'- [關於林津陞]({SITE}about/): 營業員介紹與聯絡方式',
             f'- [YouTube 板橋阿陞聊房]({YOUTUBE_CHANNEL}): 社區分析影片', '', '## 社區分析', '']
    for k in sorted((k for k in ctx['decks'] if k.startswith('community/')), key=lambda k: ctx['decks'][k].get('updated') or '', reverse=True):
        d = ctx['decks'][k]
        lines.append(f"- [{d['name']}]({page_url(k)}): {descs.get(k) or d.get('subtitle') or ''}")
    lines += ['', '## 物件簡報', '']
    for k in sorted((k for k in ctx['decks'] if not k.startswith('community/')), key=lambda k: ctx['decks'][k].get('updated') or '', reverse=True):
        d = ctx['decks'][k]
        lines.append(f"- [{d['name']}｜{d.get('subtitle') or ''}]({page_url(k)}): {d.get('area') or ''}")
    lines += ['', '## Optional', '', f'- [sitemap]({SITE}sitemap.xml)',
              '- [稅務小幫手](https://tax.banqiaoasheng.com/)', '- [青安 3.0 試算](https://loan.banqiaoasheng.com/)', '']
    return '\n'.join(lines)


def build_site(root, check=False):
    ctx = load_ctx(root)
    changed, problems, descs, writes = [], [], {}, []
    for key in pages(root):
        f = Path(root) / key / 'index.html'
        text = f.read_text(encoding='utf-8')
        graph, summary = page_graph(key, text, ctx)
        for p in audit(graph, community=key.startswith('community/')):
            problems.append(f'{key or "首頁"}：{p}')
        new = apply(text, key, graph, summary, ctx)
        if key == 'map':
            new = apply_map_links(new, ctx)
        m = ART_MARK.search(new)
        if m:
            problems += [f'{key}：文章{p}' for p in article_problems(m[0])]
        for s in static_age_problems(new):  # title、meta、og、noscript 等寫死的文字不可有屋齡數字（script 裡即時計算的不算）
            problems.append(f'{key or "首頁"}：靜態文字含屋齡數字「{s}」')
        page = next((n for n in graph if n.get('@id', '').endswith('#webpage')), {})
        descs[key] = page.get('description') or meta_content(new, 'description')
        if new != text:
            changed.append(key or '首頁')
            writes.append((f, new))
    llms = llms_txt(ctx, descs)
    problems += [f'llms.txt：{p}' for p in audit(llms)]
    if problems:  # 有一頁沒過就整批不寫
        raise SystemExit('JSON-LD 法遵檢查沒過：\n' + '\n'.join(problems))
    if not check:
        for f, new in writes:
            f.write_text(new, encoding='utf-8')
    lf = Path(root) / 'llms.txt'
    if not lf.exists() or lf.read_text(encoding='utf-8') != llms:
        changed.append('llms.txt')
        if not check:
            lf.write_text(llms, encoding='utf-8')
    return changed


# ---------------------------------------------------------------------- 指揮艙發布時用
def narration_entry(scenes, video_id=None, community=False):
    """把 scenes.voice.json 整理成 data/narration.json 的一筆（先過法遵：去掉金額句）。"""
    out = []
    for sc in scenes:
        out.append({'t': clean_segments(sc.get('t'), community=community), 's': clean_segments(sc.get('s'), community=community),
                    'v': clean(sc.get('v'), community), 'd': round(float(sc.get('d') or 0), 2)})
    return {'video': video_id, 'scenes': out}


def fetch_youtube(video_id):
    """讀 YouTube 公開影片頁：標題、上傳日、長度、說明欄章節（只用標準函式庫）。"""
    import urllib.request
    req = urllib.request.Request(f'https://www.youtube.com/watch?v={video_id}',
                                 headers={'User-Agent': 'Mozilla/5.0', 'Accept-Language': 'zh-TW'})
    t = urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'replace')
    bs = chr(92)
    s = '"((?:[^"' + bs + bs + ']|' + bs + bs + '.)*)"'

    def g(p):
        m = re.search(p, t)
        return m[1] if m else None
    title = g('"videoDetails":' + bs + '{"videoId":"[^"]+","title":' + s)
    desc = g('"shortDescription":' + s)
    up = g('"uploadDate":"([^"]+)"')
    if not (title and up):
        raise RuntimeError(f'讀不到 YouTube 影片 {video_id}（私人或已刪除？）')
    desc = json.loads('"' + desc + '"') if desc else ''
    chapters = []
    for m in re.finditer(r'^(?:(\d+):)?(\d{1,2}):(\d{2})\s+(.+)$', desc, re.M):
        chapters.append([int(m[1] or 0) * 3600 + int(m[2]) * 60 + int(m[3]), m[4].strip()])
    return {'id': video_id, 'platform': 'YouTube', 'name': json.loads('"' + title + '"'), 'uploadDate': up,
            'seconds': int(g('"lengthSeconds":"(' + bs + 'd+)"') or 0) or None, 'chapters': chapters}


def video_id_of(url):
    m = re.search(r'(?:v=|youtu\.be/|shorts/|embed/)([\w-]{11})', url) or re.fullmatch(r'([\w-]{11})', url)
    if not m:
        raise SystemExit(f'看不出 YouTube 影片編號：{url}')
    return m[1]


def add_video(root, key, url, content_url=None):
    """data/videos.json 加一支影片；口播稿長度對得上（±2 秒）就自動綁到這支影片。"""
    root = Path(root)
    vf, nf = root / 'data' / 'videos.json', root / 'data' / 'narration.json'
    videos = json.loads(vf.read_text(encoding='utf-8')) if vf.exists() else {}
    narr = json.loads(nf.read_text(encoding='utf-8')) if nf.exists() else {}
    v = fetch_youtube(video_id_of(url))
    if content_url:
        v['contentUrl'] = content_url
    lst = [x for x in videos.get(key, []) if x['id'] != v['id']] + [v]
    videos[key] = sorted(lst, key=lambda x: x['uploadDate'])
    n = narr.get(key)
    if n and not n.get('video') and v.get('seconds'):
        total = sum(float(sc.get('d') or 0) for sc in n.get('scenes') or [])
        if abs(total - v['seconds']) <= 2:
            n['video'] = v['id']
            write_json(nf, narr)
    write_json(vf, videos)
    return v


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def save_narration(root, key, scenes, video_id=None):
    nf = Path(root) / 'data' / 'narration.json'
    narr = json.loads(nf.read_text(encoding='utf-8')) if nf.exists() else {}
    old = narr.get(key) or {}
    entry = narration_entry(scenes, video_id or None, community=str(key).startswith('community/'))
    # 重新發布、影片還沒重傳：口播長度沒變就保留原本綁定的影片
    if not entry['video'] and old.get('video'):
        same = abs(sum(s['d'] for s in entry['scenes']) - sum(float(s.get('d') or 0) for s in old.get('scenes') or [])) <= 2
        entry['video'] = old['video'] if same else None
    narr[key] = entry
    write_json(nf, narr)


USAGE = """用法：
  python structured_data.py <網站資料夾> [--check]          重新產生每頁 JSON-LD、noscript 摘要、llms.txt
  python structured_data.py add-video <網站資料夾> <頁面> <YouTube網址> [影片檔網址]
        例：add-video . community/高閣 https://youtu.be/xxxxxxxxxxx
  python structured_data.py narration <網站資料夾> <頁面> <scenes.voice.json> [YouTube網址]
  python structured_data.py permit <網站資料夾> <社區名> <使照存根庫\\字號\\annex.json>
  python structured_data.py keywords <網站資料夾> <社區名>     （Google 自動完成 → data/keywords.json）"""


def main(argv):
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__ + '\n' + USAGE)
        return 0
    if argv[0] == 'add-video':
        v = add_video(argv[1], argv[2], argv[3], argv[4] if len(argv) > 4 else None)
        print(f"已加入 {argv[2]}：{v['name']}（{v['uploadDate']}）")
        argv = [argv[1]]
    elif argv[0] == 'permit':  # permit <網站資料夾> <社區名> <annex.json>：使照存根判讀寫進 data/permits.json
        e = save_permit(argv[1], argv[2], json.loads(Path(argv[3]).read_text(encoding='utf-8')))
        print(f'{argv[2]}：' + (json.dumps(e, ensure_ascii=False) if e else '存根判讀沒有看得清楚的起造人／承造人，未寫入'))
        argv = [argv[1]]
    elif argv[0] == 'keywords':  # keywords <網站資料夾> <社區名>：抓 Google 自動完成寫進 data/keywords.json
        e = save_keywords(argv[1], argv[2])
        print(f"{argv[2]}：{len(e['queries'])} 個搜尋詞（排除負面詞 {len(e['excluded'])} 個）")
        argv = [argv[1]]
    elif argv[0] == 'narration':
        scenes = json.loads(Path(argv[3]).read_text(encoding='utf-8'))
        save_narration(argv[1], argv[2], scenes, video_id_of(argv[4]) if len(argv) > 4 else None)
        argv = [argv[1]]
    check = '--check' in argv
    root = next(a for a in argv if not a.startswith('--'))
    changed = build_site(root, check)
    print(('需要更新：' if check else '已更新：') + ('、'.join(changed) if changed else '無'))
    return 1 if (check and changed) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
