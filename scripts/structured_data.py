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

法遵：JSON-LD 一樣算廣告。不寫售價、單價、屋齡數字；禁用詞與最高級擋下；
聯絡只放手機與 LINE；揭露四行固定；距離只用頁面已有的步行路線，註明實際以現場為準。

用法：python structured_data.py <網站資料夾> [--check]
  --check：只檢查，不寫檔；有頁面需要更新就回傳 1。
"""
import html
import json
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
    if community:
        miss = unit_price_missing_parking(t, context)
        if miss:
            return miss
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
    return ''.join(keep).strip()


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
        'name': BRAND, 'alternateName': ['林津陞', '全國不動產板橋加盟店 林津陞'],
        'url': SITE, 'logo': SITE + 'assets/logo-nra-icon.png', 'image': SITE + 'assets/og-banqiaoasheng.png',
        'description': '新北市板橋區的社區分析與看屋服務。' + DISCLOSURE_TEXT + '。',
        'telephone': MOBILE,
        'contactPoint': [
            {'@type': 'ContactPoint', 'telephone': MOBILE, 'contactType': '預約看屋', 'availableLanguage': 'zh-TW'},
            {'@type': 'ContactPoint', 'contactType': 'LINE 官方帳號 @banqiao.asheng', 'url': LINE_URL, 'availableLanguage': 'zh-TW'}],
        'areaServed': {'@type': 'AdministrativeArea', 'name': '新北市板橋區',
                       'containedInPlace': {'@type': 'AdministrativeArea', 'name': '新北市'}},
        'brand': {'@type': 'Brand', 'name': '全國不動產'},
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
    where = f'{name}位於{county}{district}{street}' + (f'，屬{area_name}' if area_name else '') + \
            (f'，{built}完工' if built else '') + (f'，{floors}' if floors else '') + '。'
    qa = [(f'{name}在哪裡？', clean(where, com)),
          (f'{name}到捷運站走路多久？',
           clean('；'.join(f'{walk_name(w)}{walk_text(w)}' for w in stations) + f'。{WALK_NOTE}。', com) if stations else ''),
          (f'{name}附近的生活機能有哪些？',
           clean('；'.join(f'{walk_name(w)}{walk_text(w)}' for w in life) + f'。{WALK_NOTE}。', com) if life else ''),
          (f'{name}的學區是哪裡？',
           f"依政府公開資料，{name}的學區為{comm['school'].replace('・', '、')}，{SCHOOL_NOTE}。" if comm and comm.get('school') else ''),
          (f'{name}的日照情況如何？', sun),
          (f'{name}有哪些優點？' if not listing else '這個物件有哪些優點？', sentences(pros)),
          (f'看{name}時要留意什麼？' if not listing else '看這個物件時要留意什麼？', sentences(cons))]

    if not title or title in GENERIC_TITLES or not desc:
        t2, d2 = deck_seo(deck, facts, walks, listing, county, district, road)
        title = t2 if (not title or title in GENERIC_TITLES) else title
        desc = desc or d2
    page = {'@type': ['WebPage', 'ItemPage'] if listing else 'WebPage', '@id': url + '#webpage', 'url': url,
            'name': title or name, 'description': desc or None, 'inLanguage': 'zh-Hant-TW',
            'isPartOf': {'@id': WEBSITE_ID}, 'about': {'@id': place_id}, 'mainEntity': {'@id': place_id},
            'primaryImageOfPage': {'@id': url + '#cover'} if og else None,
            'dateModified': entry.get('updated'), 'author': {'@id': PERSON_ID}, 'publisher': {'@id': AGENT_ID},
            'video': [{'@id': n['@id']} for n in videos if n['@type'] == 'VideoObject'] or None,
            'breadcrumb': {'@id': url + '#breadcrumb'}}
    crumbs = [(BRAND, SITE), (name, url)]
    graph = [{k: v for k, v in page.items() if v not in (None, [], '')}] + graph + videos + faq(url, qa) + [breadcrumb(url, crumbs)]
    summary = {'name': place['name'], 'desc': desc, 'facts': facts, 'walks': [(walk_name(w), walk_text(w)) for w in walks],
               'school': comm.get('school') if comm else '', 'pros': pros, 'cons': cons}
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
    desc = meta_content(text, 'description') or describe_simple(key, ctx)
    videos = video_nodes(url, place_id, name, ctx['videos'].get(key), ctx['narration'].get(key), key)
    pros, cons = [clean(p, True) for p in comm.get('pros') or []], [clean(p, True) for p in comm.get('cautions') or []]
    page = {'@type': 'WebPage', '@id': url + '#webpage', 'url': url, 'name': title_of(text) or name, 'description': desc,
            'inLanguage': 'zh-Hant-TW', 'isPartOf': {'@id': WEBSITE_ID}, 'about': {'@id': place_id},
            'mainEntity': {'@id': place_id}, 'dateModified': entry.get('updated'),
            'author': {'@id': PERSON_ID}, 'publisher': {'@id': AGENT_ID},
            'video': [{'@id': n['@id']} for n in videos if n['@type'] == 'VideoObject'] or None,
            'breadcrumb': {'@id': url + '#breadcrumb'}}
    qa = [(f'{name}在哪裡？', clean(f'{name}位於{county}{district}{road}' + (f'，屬{area_name}' if area_name else '') + '。', True)),
          (f'{name}到捷運站走路多久？', clean(f"{comm['mrt']}。{WALK_NOTE}。", True) if comm.get('mrt') else ''),
          (f'{name}有哪些看點？', sentences(pros)),
          (f'看{name}時要留意什麼？', sentences(cons))]
    graph = [{k: v for k, v in page.items() if v not in (None, [], '')},
             {k: v for k, v in place.items() if v not in (None, [], '')}] + videos + faq(url, qa) + \
            [breadcrumb(url, [(BRAND, SITE), (name, url)])]
    return graph, None


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
    if not head.endswith('\n'):
        head += '\n'
    head += ld_block(graph)
    rest = NS_MARK.sub('', rest)
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
            'videos': rd('data/videos.json', {}), 'narration': rd('data/narration.json', {})}


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
  python structured_data.py narration <網站資料夾> <頁面> <scenes.voice.json> [YouTube網址]"""


def main(argv):
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__ + '\n' + USAGE)
        return 0
    if argv[0] == 'add-video':
        v = add_video(argv[1], argv[2], argv[3], argv[4] if len(argv) > 4 else None)
        print(f"已加入 {argv[2]}：{v['name']}（{v['uploadDate']}）")
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
