# f743182002.github.io（板橋阿陞聊房 總站）

給接手的 AI 和發布程式看的規則。

## 網站結構

- `index.html`：總站首頁（2026-11-02 起）。社區分析、物件清單是**執行時讀 `decks.json` 產生的**。
- `map/index.html`：阿陞的商圈地圖（Leaflet＋OpenStreetMap），資料來自 `data/communities.json`。
- `assets/site.css`：首頁與地圖共用的樣式。
- `community/<社區名>/`、`S<編號>/`：各社區／物件的互動簡報（由 property-deck 指揮艙發布）。

## 發布新簡報時

1. **不要再用清單覆寫 `index.html`。** 舊的發布流程會把 index.html 重寫成純清單，總站會整個不見。現在只要更新 `decks.json`（加一筆 `"community/<社區名>": {name, subtitle, area, updated, status}`），首頁就會自動列出。
2. 社區版另外在 `data/communities.json` 的 `communities` 加一筆，地圖才會出現。欄位照現有格式填，`deck` 填 `community/<社區名>/`；只能用查證表（facts_verified.json）裡已查證的值。座標用簡報 data.js 的 `SITE.lat/lon`（建物輪廓中心），不用 591 座標。指揮艙發布時會自動寫入，不用手動加（property-deck `site_map.py`：同名社區只更新那一筆、新社區加在最後；檢查不過整個發布不 push）。
3. 簡報還沒發布的社區，`deck` 填 `null`，清單會顯示「簡報製作中」。

## 簡報頁版型規則（2026-11-04 第一階段）

由 property-deck 範本（`skill/assets/template.src.html`）產生，**不要手改輸出 HTML**，要改請改範本再用指揮艙重發布（`deck_engine.py republish C_<社區名> --work-root … --keep-date`）。
- **待辦（2026-11-10）**：簡報頁還是舊的公司品牌（深紅揭露列、logo-nra、紅色主色），要照下面「個人品牌」一節改 property-deck 範本後用指揮艙重發布（本機工具處理，不手改輸出 HTML）。下面兩行是改版前的規則，範本改完後要一起更新。
- `<!doctype html><html lang="zh-Hant">`；頁首深紅揭露列（同首頁 `.disc-bar`：全國不動產板橋加盟店｜經紀業 非凡不動產有限公司｜經紀人 謝政峯（99）北縣字第002181號｜營業員 林津陞（99）登字第148103號）；頁尾完整揭露不可刪。
- 頁首：`/assets/logo-nra.png`、品牌連回 https://banqiaoasheng.com/ 、「看商圈地圖」（/map/）、同生活圈 2～3 個社區（頁面執行時讀 `data/communities.json`：同 area、deck 不是 null、排除自己）、常駐「加 LINE」按鈕（≥44px）。
- 聯絡：LINE `https://line.me/R/ti/p/%40banqiao.asheng`、手機 `tel:0925635678` 直接點，複製按鈕保留當備用。只放手機＋LINE，不放店電話。
- 章節記憶 localStorage 鍵 `'deck-ch:'+location.pathname`（每頁獨立，try/catch）。內文 ≥16px、章節按鈕 ≥44px。
- 減重：不載 Google Fonts（系統字型）；照片（≤1100px）、航照（≤1600px）、地圖圖示是同資料夾的 WebP 獨立檔、`loading="lazy"`；three.js 延後載入（封面按「看 3D 模型」或進日照章才下載）。目標每頁整頁瀏覽 ≤2 MB。
- og：每頁有 og:title／og:description／og:image（同資料夾 og.jpg，1200×630）；og 文字不寫屋齡數字、金額、禁用詞。
- 影片版：`data/videos.json` 有這頁的影片才顯示「看影片版 ▶」，按了才載入 youtube-nocookie iframe，不預先載入。
- `decks.json` 每筆有 `status`：`社區分析`（community/* 一律）、`銷售中`、`已成交`、`待確認`。物件狀態只有林津陞確認過才寫銷售中／已成交，其他一律待確認；首頁卡片顯示狀態（待確認顯示「狀態待確認」），已成交或下架的物件不可寫「還在賣」之類的字。發布程式會保留已有的 status。
- 舊版頁（不是範本做的）：`community/新濠一滙/`、`S21140123/` 由 property-deck `legacy_page.py`（`deck_engine.py legacy <路徑>`）在 `<!-- SITE-CHROME:START/END -->` 之間加揭露列與頁首、拆 WebP、重寫 og；S21140123 有 CSP，只放靜態連結（影片版連到 YouTube）。
- 只換版型的重發布不動 `data/communities.json`（地圖資料可能人工校過）。

## 結構化資料（JSON-LD）與 llms.txt（2026-11-03）

- 各頁 `<head>` 的 `<!-- LD:START -->…<!-- LD:END -->`、物件頁 `<main>` 前的 `<!-- LD-SUMMARY -->` noscript 摘要（社區頁改放可見文章，見下一節）、`/llms.txt` 都由 `scripts/structured_data.py` 產生，**不要手改**；GitHub Actions 每次 push 會重跑。
- 這支程式的唯一來源是 9b-houseflow-tools `tools/property-deck/structured_data.py`，指揮艙發布時會複製過來；要改請改那邊。
- 資料來源：頁面內嵌的 DECK／SITE、`data/communities.json`、`data/videos.json`（YouTube 影片）、`data/narration.json`（影片字卡與口播稿，發布時寫入）、`decks.json`。
- 影片上傳 YouTube 後執行 `python scripts/structured_data.py add-video . community/<社區名> https://youtu.be/<編號>` 再 commit／push（Shorts 一樣）。
- 法遵：金額、屋齡、禁用詞整句不寫；有一頁沒過，程式整批不寫檔。

## 社區頁看得見的分析文章（2026-11-11）

- 每個社區頁在章節列 `<nav class="rail">` 後面有 `<!-- ARTICLE:START -->…<!-- ARTICLE:END -->`（`<article id="analysis">`，純 HTML、Google 讀得到）；頁首「看商圈地圖」旁的 `<!-- ARTICLE-LINK -->`「看文字版分析」；地圖頁 footer 前的 `<!-- MAPLINKS -->` 社區文章清單。都由 `scripts/structured_data.py` 產生，**不要手改**，Actions 每次 push 重跑（內容沒變不改檔）。
- 社區頁的 `<title>`／meta description／og／JSON-LD `WebPage.name`、`headline` 是問句型「○○可以買嗎？優缺點、捷運、管委會與車位｜板橋阿陞聊房」：後面三個主題依 `data/keywords.json` 的買方搜尋詞排序（沒有資料的主題不列；「實價登錄」「完工年」不進標題），摘要以「○○社區分析：」開頭。
- 文章章節＝買方搜尋的問句：每個 h2 是一題（例「新巨蛋有車位嗎？車位有多少？」），h2 下第一段（`.sa-lead`）直接講結論，FAQPage 用同一份問句與第一段。第一節固定「○○可以買嗎？先說結論」，最後是「優缺點」「缺點是什麼？看屋時要確認什麼？」。
- `data/keywords.json`（林津陞 2026-11-11「優化成就是買方會搜的關鍵字」）：每個社區的 Google 自動完成與「其他人也搜尋了」。`queries` 決定主題排序；`excluded` 是凶宅、跳樓、上吊、法拍、釘子戶等負面詞，**只記錄、不寫進文章或標題**；房價、租金、行情類的詞也不回答（法遵）。社區版發布時 property-deck 自動抓自動完成合併進去；手動更新 `python scripts/structured_data.py keywords . <社區名>`（「其他人也搜尋了」要用瀏覽器看搜尋結果頁，人工補進 queries）。社區頁不再放 `<noscript>` 摘要（文章已是可見文字，避免同一份內容出現兩次）；物件頁（S*）照舊。
- 文章、常見問題（與 JSON-LD FAQPage 同一份）**不寫金額（含實價登錄單價）、屋齡數字、興建中站點**；完整揭露四行＋攻略兩行固定在文末。
- 起造人／承造人：`data/permits.json`（使照存根影像判讀，看不清楚的不收），社區版發布時 property-deck 自動寫入；手動補 `python scripts/structured_data.py permit . <社區名> <_使照存根庫\字號\annex.json>`。
- 首頁社區卡片與地圖資料卡的連結文字是「看○○社區分析」（內部連結錨文字）。

## 生活圈分類

`data/communities.json` 的 `areas`，名稱與範圍參考樂居板橋區生活圈（林津陞 2026-11-02 提供樂居地圖截圖）。`lat/lon` 是生活圈名稱在地圖上的標籤位置（依樂居地圖判讀，約略）。新社區歸到最近的生活圈；跨界的照樂居社區頁標示。不放樂居的單價數字。

## 法遵

頁首揭露列（精簡版，SOP 3.1）與頁尾完整版揭露三行都不可刪（樣式見下一節「個人品牌」：小字、中性色）；主色、LOGO、地圖標記照「個人品牌」一節（2026-11-10 起不再用紅色與全國不動產 LOGO）；只放手機＋LINE；禁用詞照 realtor-ad-compliance 技能。例外：`about/` 關於我頁的聯絡區與頁尾可以放店址（新北市板橋區文化路二段37號），林津陞 2026-11-03 確認「這個沒關係」；店電話仍不放。

門牌：社區分析頁（community/*、每戶成交格子圖、棟別配置圖）可以寫社區門牌（林津陞 2026-11-07「社區能寫門牌」）；**出售物件頁（S 開頭）只寫到路段，不可寫門牌號碼**，也不寫內部委託編號、「公司後台」。

社區分析頁不寫總價、車位價（技能 F 類）；2026-11-07 曾在輸出頁臨時手改拿掉，範本與工作資料夾的修正見 ai-collab `交辦_本地CC_網站全面檢查後續_20261107.md`。

## 個人品牌（2026-11-10 林津陞決定）

原話：「把我所有網站的公司LOGO都換成我的品牌LOGO，我之後都不要幫公司打廣告，只做我自己的個人品牌，公司名稱那些就按照法規要求用小字帶過即可」「所有網站都不要用紅色當主色了，要跟公司品牌區隔」「首頁一定要有我的照片，不然被人盜用，現在開始以我為IP」。LOGO 選「方向C」（電路節點房子＋板橋阿陞聊房字標），配色選「C 漸層科技」。

- **LOGO（2026-11-11 定案：A 字屋頂標＋中間亮藍 #1E88FF）**：林津陞原話「選A 但中間藍色 想換成天空藍」→「3 亮藍」。頁首用 `assets/brand/logo_wide.png`（圖形＋近黑粗體字，alt「板橋阿陞聊房」）；直式 `assets/brand/logo.png`、圖示 `assets/brand/icon16/32/48/128/512.png`、`assets/favicon-64.png`、`apple-touch-icon.png`、`assets/brand/logo.svg`（向量圖形）。正本在 ai-collab `素材/品牌LOGO_20261109/正式版_20261111/`（make_official.py 重產）。舊的方向C（淺藍電路房子）不再用：他說「logo藍色太不清楚」。`favicon.ico` 還是舊圖，待換。
- **不用全國不動產 LOGO**：總站頁（index、map、about、404、data/layout/view.html、data/units/view.html）不引用 `assets/logo-nra.png`、`logo-nra-icon.png`。檔案留著（簡報頁還在用）。地圖上的店位置標記改用品牌圓形圖示＋「林津陞」。
- **頁首副標**：「林津陞｜板橋在地房產顧問」，不寫公司名。about 標題與主視覺也不推公司（「…林津陞｜板橋阿陞聊房」）。
- **配色（2026-11-11 可讀性改版，林津陞：「大部分都深色 可是文字很淺 辨識度很差」，選版本 B）**：**全站一律淺色，不跟系統深色模式**（`assets/site.css` 的深色區塊改填淺色值、`color-scheme:only light`；頁面不可再寫 `prefers-color-scheme: dark` 的深色規則）。底 #F2F8FB、卡片 #FFF＋1.5px 邊框 #9DB8C9、字 #0F2233、次要字 #33475B（不可更淺）。**文字不用藍、青、淺灰**：連結用近黑字＋深藍底線，選單目前頁用淡藍底＋深藍底線。深藍 #0369A1／#075985、青 #06B6D4 只當底色、框線、底線、按鈕底。**配色方案 3（2026-11-11 林津陞看三方案後選「方案 3」；他的標準：「我不一定要紅色的字 最重要是能讓客戶好閱讀 抓得到重點」）**：主色＝LOGO 近黑 #0F2233（首頁主視覺漸層 #0F2233→#1D3A52、主入口卡、主要按鈕、頁首／頁尾細線、選單目前頁底線）；**重點色紅 #B91C1C 只用在「名稱」**（社區名、物件名、工具名、攻略書名、商圈地圖清單社區名與地圖點），區塊大標是近黑字＋48px 紅短底線，其他地方不用紅；LOGO 亮藍 #1E88FF 只當主視覺下緣細線與連結底線；底 #F4F5F7、揭露列底 #EEF1F4。主視覺上的字用純白；其他區塊淺底黑字。字級：首頁大標 44px（平板 31px、手機 27px）、說明 18.5px（手機 17px）、卡片標題約 20px、卡片說明 ≥15.5px。
- **法定揭露（不動產經紀業管理條例 §21）**：頁首下方一條細揭露列（`.disc-bar`：13px、淡藍底 #E4F4FA、近黑字 #0F2233，2026-11-11 起），文字一字不改「全國不動產板橋加盟店｜經紀業 非凡不動產有限公司｜經紀人 謝政峯（99）北縣字第002181號｜營業員 林津陞（99）登字第148103號」；頁尾完整揭露四行文字不變、用小字次要色（`.disc-full`），最後加「© 林津陞　板橋阿陞聊房」。「營業員」只出現在揭露小字裡，照片說明只寫「林津陞（阿陞）」（林津陞 2026-11-10）。
- **照片＝IP**：首頁主視覺放大張半身去背照 `about/lin-half.webp`（電腦高 440px、手機 300px）＋白底近黑字名牌「林津陞（阿陞）」，不用圓形小頭像（林津陞 11/10：「至少要有半身照 一個頭很難看」「不需要做太小 位子還很空阿」）；地圖頁標題旁有小頭像；404 有小頭像。about 頁（2026-11-11 林津陞「改關於我」）同首頁：主視覺近黑漸層＋白字＋大張半身去背照 `about/lin-half.webp` 與名牌；ABOUT 段用方形圓角半身照 `about/lin-studio-half.webp`（由 property-deck `_brand/林津陞_黑西裝紅領帶_原圖.webp` 裁，不含右下角浮水印）；舊圓形照 `lin-portrait.*` 只留給 JSON-LD 與地圖小頭像。不加新的宣傳用語。
- **地圖標記**：社區圓點深藍 #0369A1＋白圈，名稱深藍字 #075985＋白色光暈，維持加大、高對比（取代 SOP 4.9 的紅色）；生活圈標籤白底黑字青框（#0E7490）。
- **分享圖**：`assets/brand/og-1200x630.png`（LOGO、照片、板橋阿陞聊房、底部小字「經紀業 非凡不動產有限公司｜營業員 林津陞（99）登字第148103號」），index／map／about／404 手寫的 og:image、twitter:image 都指向它。舊的 `assets/og-banqiaoasheng.png`、`about/og-home*.png` 有公司 LOGO／舊配色，不再引用（JSON-LD 的 `logo`／`image` 2026-11-11 起改 `assets/brand/logo.png`、`assets/brand/og-1200x630.png`，由 structured_data.py 產生）。
- **還沒改的**：簡報頁 community/*、S*/（property-deck 範本）、Netlify 工具站（稅務小幫手、青安 3.0）。

## 網域

- 主網域 **banqiaoasheng.com**，2026-11-02 在 Cloudflare 註冊。DNS 也在 Cloudflare，所有紀錄一律設成 **DNS only（灰色雲）**，不開 Cloudflare 代理，由 GitHub、Netlify 自己簽 HTTPS 憑證。
- `www.banqiaoasheng.com`：CNAME 指到 `f743182002.github.io`。
- `tax.banqiaoasheng.com`：對應 Netlify 專案 `house116money`（稅務小幫手）。
- `loan.banqiaoasheng.com`：對應 Netlify 專案 `zesty-cocada-c738c2`（青安 3.0）。
- 以後新的互動簡報網址一律寫 `https://banqiaoasheng.com/community/<社區名>/`。舊的 `f743182002.github.io` 網址 GitHub 會自動轉址，不用改舊影片說明欄。
- 「關於我」頁在 `about/`（2026-11-02 由 Netlify lin-realtor 搬入），舊網址 lin-realtor.netlify.app 會轉到 https://banqiaoasheng.com/about/ 。

## 棟別門牌配置圖（2026-11-04）

- `scripts/door_layout.py` 產生 `data/layout/<社區名>.svg`、`data/layout/index.json` 與手機看圖頁 `data/layout/view.html`；地圖資料卡有檔案才顯示「看棟別配置圖」，連到 `data/layout/view.html?n=<社區名>`（有 viewport，圖寬 100%；直接開 .svg 時手機用 980px 版面只看得到左半）。重跑：`python3 scripts/door_layout.py .`（Windows 用 `python`）；內容沒變不改檔（index.json 也不會因日期每天變）。
- 資料只用本站自己的：簡報內嵌 `window.SITE` 的本社區建物輪廓（me=1）與道路、`data/doors/<社區名>.json` 門牌定位（property-deck scope_check 的國土測繪中心門牌定位結果，格式 `{"doors":[{"no":"191","lat":..,"lon":..}]}`）。門牌落在本社區輪廓 8 公尺內才標上去。
- 門牌畫法（2026-11-04 修正）：每個門牌在國土測繪中心座標畫藍點（2026-11-10 前為紅點）＋獨立小標籤，標籤彼此不重疊（放不下往外推、拉引線），也不蓋住棟名、指北針、比例尺；全部門牌同一主號都有之N（健華新城 309之1～之38）時標籤只寫「之N」，副標註明主號。SVG 只給 viewBox（寬度自適應）。**不手改 SVG，改 door_layout.py。**
- `scripts/door_layout.py` 只由它自己的修改流程 commit：指揮艙發布的 `git add` 排除它（`PENDING_EXCLUDE`；2026-11-04 欣璞綻發布 26381ca 曾把改到一半的版本帶上線），發布時重產的 `data/layout/*.svg` 照常 commit。
- **不可以參考、描繪樂居或其他網站的配置圖或平面圖。** 只標門牌號，不標樓層、戶號、住戶資訊。

## 門牌座標與每戶實價資料（2026-11-04 第三階段）

兩種檔都由 property-deck `site_export.py` 產生，**不要手改**；要改資料請回工作資料夾修正後重跑（`python -X utf8 site_export.py --all --site <本 repo> --work-roots <工作根目錄…> [--units-to-site] [--layout]`，內容沒變不會改檔）。圖也不要手改 SVG，改產生器或資料。

- `data/doors/<社區名>.json`：來源是工作資料夾 `scope_check.json` 的**內政部國土測繪中心門牌定位**，只取落在本社區輪廓的點；沒查到座標的門牌不寫。格式 `{"source":"內政部國土測繪中心門牌定位（scope_check）","checked":"YYYY-MM-DD","origin":{"lat":..,"lon":..},"doors":[{"no":"191","lat":..,"lon":..}]}`。`checked` 是 scope_check 實際查詢日；`origin` 是簡報 `window.SITE` 的原點（建物輪廓座標的 0,0），`door_layout.py` 用它換算（地圖 `communities.json` 的點不一定是原點，綠如意差約 12 公尺）。**只放門牌號與座標，不放樓層、戶號、住戶資訊。** 社區版發布時指揮艙會一起寫入並重跑 `door_layout.py`，跟簡報同一個 commit。
- `data/units/<社區名>.json`（每戶成交實價格子圖，林津陞 2026-11-04 定案）：
  - **資料新舊**：不用簡報 deals 快照。直接從每晚更新的本機實價快取（realprice market_cache）取社區全部成交，依工作資料夾 `facts_verified.json` 的門牌範圍（address 列，含單雙號）、建築完成年月、總樓層數不超過地上層數篩選。
  - **口徑（照樂居均價口徑 leju.com.tw/faq/2：單價扣除車位坪數與價格；只借口徑，樣式不照抄）**：全部用途都列（住家、住商、辦公、商業、其他）；一樓、地下層照收，圖上用另一種底色標示（一樓／店面、地下層），不跟住宅樓層混比；排除特殊交易（property-deck `SPECIAL_KEYWORDS`）、單獨車位／土地、預售屋（交易日早於建築完成年月＝蓋好前簽約）；同一戶（門牌＋樓層＋之N）只留最新一筆，`n` 記該戶筆數。
  - **單價**（萬元/坪，小數一位）：原始資料有拆分車位價與車位面積的才扣，(總價−車位價)/(總面積−車位面積)；沒拆分的不估算，`parking:"included"`，圖上標「含車位」。
  - 格式 `{"source":"內政部不動產交易實價查詢服務網（已排除特殊交易）","period":"110S2～115S4","published_through":"115/11/01","cutoff":"截至 115/11/01 公布","scope":"…","floors":19,"door_floors":{"莊敬路191號":19},"units":[{"addr":"莊敬路203號","floor":11,"suffix":"之3","ym":"114/08","price":85.9,"parking":"none","use":"住家用","n":2}]}`。`floor` 地下層是負數；跨層（一層，夾層）畫在最低地上層並有 `span`。**成交只到年月，不放交易日、總價、車位價、住戶資訊。**
- **「網頁不寫金額」的例外只限這張格子圖**：每格寫「成交年月＋成交單價（萬/坪）」，不寫幾房；同一戶多筆只畫最新一筆並標「共N筆」。圖下註記必含：資料來源「內政部不動產交易實價查詢服務網（已排除特殊交易）」、資料期間、資料公布截止日（「截至 115/11/01 公布」）、「之後的新成交未納入，以內政部最新資料為準」、「單價已扣除有拆分的車位；標『含車位』者未拆分」、「不依實際比例重繪，實際以現場及權狀為準」。
- `scripts/unit_grid.py` 讀 `data/units`（門牌欄另外併入 `data/doors` 全部門牌，沒成交的留空欄、不跳號），產生（2026-11-04 重新設計、林津陞核可上線）：
  - `data/units/view.html?n=<社區名>`：手機優先看圖頁。最上面是單價中位數摘要（只算二樓以上、不含「含車位」、每戶最新一筆；近一年 ≥3 戶放近一年，否則放全部期間）、有成交戶數、近一年戶數、最新成交年月、資料公布截止日；下面一棟一張表（用 `data/doors` 座標對 SITE 本社區輪廓 me=1 分棟，有一戶歸不到棟就整個社區合成一張表），連續 2 層以上沒成交收成細列，表頭與樓層欄固定；成交格依單價（本社區分位數 5 階藍青色階，2026-11-10 前為總站紅）或年份（中性灰階）上色，一樓／地下層／含車位只加框不上色；點格子看細節。頁首細揭露列（小字中性色）、頁尾完整揭露、只放手機與 LINE。
  - `data/units/<社區名>.grid.json`（看圖頁讀的預算資料）、`<社區名>.svg`（同設計的靜態圖，給社群或列印）、`index.json`（有格子圖的社區清單，地圖資料卡據此顯示「看每戶成交實價」）。
  - 門牌在上、樓層在左是通用排法；**不可照抄樂居銷控表的配色、版面細節、特殊交易標示方式**；「夾層」是禁用詞，寫「跨層」；內容沒變不改檔。
- **每晚自動更新**：`C:\claude-work\nightly-9b-sync.ps1` 第 0b 步（實價快取 refresh 之後）跑 `site_export.py --all --units-only --units-to-site` 再跑 `scripts/unit_grid.py`，結果寫 `steps.units_refresh`，失敗只記 faults，不擋同步。腳本變數 `$unitsAutoPush`：
  - 林津陞 2026-11-04 核可上線，已改 `$true`：`data/units` 有變動才 commit＋push（只 add `data/units`）。
- 指揮艙發布只把 units 寫在工作資料夾 `site_units.json`，`git add` 一律排除 `data/units` 與 `scripts/unit_grid.py`（`PENDING_EXCLUDE`）：總站的 units 只由夜間同步更新，`unit_grid.py` 改版要另外 commit。改 `unit_grid.py` 的版面或收錄口徑要先給林津陞看截圖。

## 充電樁（2026-11-04 第四階段）

依據：本 repo `notes` 分支 `research/2026-11-04_充電樁與平面圖_法規研究.md`（A2 標籤與標準說法、C 節檢查規則）。**法規判斷只照報告，不自己推論；沒有證據就是「未查證」。**
- `data/communities.json` 每個社區可有 `ev`：`{"status":[標籤…],"basis":{"permit_no","permit_issued","commenced","use_permit_no","use_permit_issued","completed","rule","src":"參考政府公開資料"},"verified_at"}`。值**只能來自** property-deck 查證表 `facts_verified.json` 的 `ev` 列，由 `site_map.py` 寫入，**不要手改**；查證表沒有 ev 就整欄省略（不填 null）。
- 標籤只能用：`existing_needs_approval`（既有大樓：個別加裝需管委會同意與用電評估）、`law_space_108`（建照申請日 ≥ 108/7/1，依法預留裝設空間）、`ntpc_conduit_111`（新北集合住宅、建照核發日 ≥ 111/3/1，應全數預留管線）、`has_shared_charging`（社區設有公共充電設備）、`has_private_installed`（已有住戶在自有車位裝設）、`no_parking`（使照附表汽車位 0）、`unverified`（未查證）。法定基準最多一個；`unverified`、`no_parking` 只能單獨用；`has_*` 要有管委會書面公告、規約、本店照片、建商文件、竣工資料或補助名單等證據（記日期）與查證日 `verified_at`。
- 判斷用使照存根的原建照字號與日期：使照竣工／發照、建照核發或開工在 108/7/1 以前 → `existing_needs_approval`；建照在 108/7/1 以後核發但查不到申請（掛號）日 → `unverified`（不可標 law_space_108）。變更設計不改原建照申請日。
- 顯示：簡報「停車與充電」頁用報告的標準說法＋一般附註（「充電設備能否加裝，需依社區規約、管委會或區分所有權人會議決議，以及電機技師與台電的用電評估而定；本頁僅整理公開資料與查證紀錄，非施工或核准保證。」）；地圖資料卡「充電」一行用報告 C 節的短句，`unverified` 不顯示。`has_*` 查證日超過 12 個月，由瀏覽器當天日期即時顯示「待重新確認」，不寫死。
- **禁用**：「保證可裝」「一定可以」「管委會不能拒絕」「不得拒絕」「友善」（含「電動車友善社區」）。不寫充電費率、「隨時有位」、「很難裝」。標籤只寫類別，不寫「民國XX年建照」；字號只放在資料來源。
- 2026-11-04 現況：地圖 14 個社區標 `existing_needs_approval`（全部有原建照字號與 108/7/1 前的日期）；新濠一滙（興建中、沒有查證表）與鑽石名門（沒有查證表）沒有 ev。目前沒有任何社區有 has_* 證據。

## 戶型（2026-11-04 第五階段）

依據：本 repo `notes` 分支 `research/2026-11-04_戶型示意圖_二創法律分析與畫法.md` 與 `research/2026-11-04_充電樁與平面圖_法規研究.md`（B3、B4、C 節）。**法律判斷只照報告，不自己推論。**
- **分布表口徑**：`data/communities.json` 的 `layouts` 與社區簡報「戶型」頁，由 property-deck `site_export.layouts()` 產生，**不要手改**。取數跟每戶實價同一套（本機實價快取、查證表門牌範圍＋完工年月＋地上層數、排除特殊交易與預售屋），只算主要用途含「住」；同一戶只算一次；依「建物現況格局-房」分 0 房（開放格局或套房）／1／2／3／4 房以上，**少於 3 筆的組併入「其他」**；坪數是主建物面積（最小～最大，小數一位）。格式 `{"source","basis","period","published_through","cutoff","n","rows":[{"rooms","label","count","main_ping"}]}`。**不放金額、單價、完工年、交易日**；資料公布截止日一定要記。發布檢查會擋。
- 簡報戶型頁固定附註：資料來源內政部實價登錄（申報資料，可能與現況不同，不代表個別房屋）、已排除特殊交易與預售屋、資料公布截止日、坪數為主建物、僅供參考，實際以權狀與現場為準。錄影版不放這頁。`republish` 只更新地圖那筆的 `built`／`year`／`ev`／`layouts`；簡報暫不重發布的社區用 `site_map.py layouts-only` 只動 layouts。
- **嚴禁描圖**：不可拿建商（DM、官網、接待中心）、591、樂居、他店的格局圖、竣工圖、建物測量成果圖描圖、套底、掃描、向量化或丟給 AI 參考（換顏色、線寬仍是重製）；委託人提供的建商圖也不行。
- **示意圖核可**：只能用 property-deck `floorplan/gen_floorplan.py` 畫阿陞版示意圖，輸入只有房廳衛數、坪數、座向、本店現場勘查草圖；每張存佐證（輸入 JSON、草圖來源說明、產生時間）。**林津陞核可（`approved_by`、`approved_at`）才會出現在網頁**，沒核可的發布程式擋下。只標戶型代號，不標棟、樓層、戶號、門牌。圖上固定兩行附註「格局示意，非依比例繪製，僅供參考；實際以現場、權狀及使用執照為準」「本圖為本店依公開資料與現場勘查自行繪製之示意圖，非建商原始圖面」。2026-11-04 現況：沒有任何核可的示意圖。
- **樂居只放連結**：戶型頁「看樂居戶型圖 →」只連到樂居社區頁（`https://www.leju.com.tw/community/L…`，`rel="noopener nofollow"`），不複製圖、不嵌入、不截圖。網址記在查證表 `leju_url` 列，林津陞確認（status「已確認」）前按鈕不顯示。

## 屋齡（2026-11-04）

- 網頁上的屋齡**一律不寫死**：由瀏覽器在打開頁面時，依 `built`（完工年月）與當天日期（台灣時間）即時計算，例：地圖資料卡「屋齡 29 年（依完工年月自動計算）」。只有完工年、沒有月份時可能差一歲，**不顯示任何屋齡數字、不估算**，資料卡與清單顯示「屋齡：待查證完工月份」，地圖屋齡篩選歸到「完工月份待查」（林津陞 2026-11-04）；查到月份後把 `built` 補成「民國X年Y月」即可。地圖屋齡分組：3年內（新成屋）／3～5年／5～10年／10～20年／20～30年／30年以上／完工月份待查／興建中，同樣在瀏覽器即時計算。
- 靜態文字（title、meta description、og、JSON-LD、llms.txt、YouTube 說明、591 文案、影片字幕）仍然**不寫屋齡數字**，只寫完工年，因為這些不會自動更新。
- 簡報頁也即時計算（2026-11-04 第二階段）：社區簡報第 1 章事實欄「完工」旁邊多一格「屋齡」，由頁面 JS 依 `DECK.facts` 的完工年月與當天台灣時間計算，算法與本頁 `ageText()` 相同（property-deck `tests/test_age_live.cjs` 比對兩邊結果）。只有年份顯示「屋齡：待查證完工月份」；興建中不顯示；錄影版（影片）不顯示屋齡。noscript／靜態 HTML 不含屋齡數字。
- 完工月份一律用**使照發照日的月份**（不用竣工日）；查找順序：使照發照日 → 實價登錄「建築完成年月」（同社區多筆取最常出現的值）→ 建物登記謄本。來源月份不一致時列給林津陞決定（林津陞 2026-11-04）。
- 發布會擋：`data/communities.json` 的 `built` 不是「興建中」就必須是「民國X年Y月」，沒有月份 property-deck 發布直接停下（`site_map.py` validate／prepare）；靜態文字出現「屋齡＋數字」「N年屋」也會擋（`structured_data.py` 的 `AGE`，只掃 `<script>` 以外的文字）。`republish` 只更新地圖那筆的 `built`／`year`，其他人工校過的欄位不動。

## 用詞與每戶成交實價（2026-11-04 林津陞決定）

- 用詞：不說「街屋」，一律改「透天厝」；不說「塔樓」，一律改「大樓」（含簡報、地圖、配置圖、字幕、說明欄）。
- `data/units/view.html`「每戶成交實價」保留單價與成交年月（資料來源政府實價登錄、排除特殊交易、註明資料期間），林津陞確認保留。
