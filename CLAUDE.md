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

- 各頁 `<head>` 的 `<!-- LD:START -->…<!-- LD:END -->`、簡報頁 `<main>` 前的 `<!-- LD-SUMMARY -->` noscript 摘要、`/llms.txt` 都由 `scripts/structured_data.py` 產生，**不要手改**；GitHub Actions 每次 push 會重跑。
- 這支程式的唯一來源是 9b-houseflow-tools `tools/property-deck/structured_data.py`，指揮艙發布時會複製過來；要改請改那邊。
- 資料來源：頁面內嵌的 DECK／SITE、`data/communities.json`、`data/videos.json`（YouTube 影片）、`data/narration.json`（影片字卡與口播稿，發布時寫入）、`decks.json`。
- 影片上傳 YouTube 後執行 `python scripts/structured_data.py add-video . community/<社區名> https://youtu.be/<編號>` 再 commit／push（Shorts 一樣）。
- 法遵：金額、屋齡、禁用詞整句不寫；有一頁沒過，程式整批不寫檔。

## 生活圈分類

`data/communities.json` 的 `areas`，名稱與範圍參考樂居板橋區生活圈（林津陞 2026-11-02 提供樂居地圖截圖）。`lat/lon` 是生活圈名稱在地圖上的標籤位置（依樂居地圖判讀，約略）。新社區歸到最近的生活圈；跨界的照樂居社區頁標示。不放樂居的單價數字。

## 法遵

頁首揭露列（精簡版，SOP 3.1）與頁尾完整版揭露三行都不可刪；主色紅（#C8161D），LOGO 用 assets/logo-nra.png（全國不動產官網 nra.com.tw 原檔）與 assets/logo-nra-icon.png（圓形標誌）；地圖橫幅白底、黑字、紅框；社區圓點與名稱照 SOP 4.9 用紅色、加大；只放手機＋LINE；禁用詞照 realtor-ad-compliance 技能。例外：`about/` 關於我頁的聯絡區與頁尾可以放店址（新北市板橋區文化路二段37號），林津陞 2026-11-03 確認「這個沒關係」；店電話仍不放。

## 網域

- 主網域 **banqiaoasheng.com**，2026-11-02 在 Cloudflare 註冊。DNS 也在 Cloudflare，所有紀錄一律設成 **DNS only（灰色雲）**，不開 Cloudflare 代理，由 GitHub、Netlify 自己簽 HTTPS 憑證。
- `www.banqiaoasheng.com`：CNAME 指到 `f743182002.github.io`。
- `tax.banqiaoasheng.com`：對應 Netlify 專案 `house116money`（稅務小幫手）。
- `loan.banqiaoasheng.com`：對應 Netlify 專案 `zesty-cocada-c738c2`（青安 3.0）。
- 以後新的互動簡報網址一律寫 `https://banqiaoasheng.com/community/<社區名>/`。舊的 `f743182002.github.io` 網址 GitHub 會自動轉址，不用改舊影片說明欄。
- 「關於我」頁在 `about/`（2026-11-02 由 Netlify lin-realtor 搬入），舊網址 lin-realtor.netlify.app 會轉到 https://banqiaoasheng.com/about/ 。

## 棟別門牌配置圖（2026-11-04）

- `scripts/door_layout.py` 產生 `data/layout/<社區名>.svg` 與 `data/layout/index.json`；地圖資料卡有檔案才顯示「看棟別配置圖」。重跑：`python3 scripts/door_layout.py .`（Windows 用 `python`）
- 資料只用本站自己的：簡報內嵌 `window.SITE` 的本社區建物輪廓（me=1）與道路、`data/doors/<社區名>.json` 門牌定位（property-deck scope_check 的國土測繪中心門牌定位結果，格式 `{"doors":[{"no":"191","lat":..,"lon":..}]}`）。門牌落在本社區輪廓 8 公尺內才標上去。
- **不可以參考、描繪樂居或其他網站的配置圖或平面圖。** 只標門牌號，不標樓層、戶號、住戶資訊。

## 門牌座標與每戶實價資料（2026-11-04 第三階段）

兩種檔都由 property-deck `site_export.py` 產生，**不要手改**；要改資料請回工作資料夾修正後重跑（`python -X utf8 site_export.py --all --site <本 repo> --work-roots <工作根目錄…> [--units-to-site] [--layout]`，內容沒變不會改檔）。圖也不要手改 SVG，改產生器或資料。

- `data/doors/<社區名>.json`：來源是工作資料夾 `scope_check.json` 的**內政部國土測繪中心門牌定位**，只取落在本社區輪廓的點；沒查到座標的門牌不寫。格式 `{"source":"內政部國土測繪中心門牌定位（scope_check）","checked":"YYYY-MM-DD","origin":{"lat":..,"lon":..},"doors":[{"no":"191","lat":..,"lon":..}]}`。`checked` 是 scope_check 實際查詢日；`origin` 是簡報 `window.SITE` 的原點（建物輪廓座標的 0,0），`door_layout.py` 用它換算（地圖 `communities.json` 的點不一定是原點，綠如意差約 12 公尺）。**只放門牌號與座標，不放樓層、戶號、住戶資訊。** 社區版發布時指揮艙會一起寫入並重跑 `door_layout.py`，跟簡報同一個 commit。
- `data/units/<社區名>.json`：來源是**內政部實價登錄買賣**，跟社區簡報「實價登錄 N 筆」同一批（排除特殊交易、不含預售屋 B 檔），逐筆對回實價原始資料，只留主要用途「住家用」、單一樓層的成交；同一戶（門牌＋樓層＋之N）只留最新一筆。格式 `{"source":"內政部實價登錄 買賣（排除特殊交易）","period":"110S2～115S4","checked":"YYYY-MM-DD","units":[{"addr":"莊敬路203號","floor":11,"suffix":"之3","rooms":2,"main_ping":10.2,"area_ping":14.7,"parking":false}]}`（坪＝平方公尺×0.3025，小數一位；查不到的欄位不寫）。**不放金額、單價、交易日期、車位價、住戶資訊。**
- `scripts/unit_grid.py` 讀 `data/units` 產生 `data/units/<社區名>.svg`（樓層×門牌格子圖，「309之5號」這種之N門牌各自一欄）。
- **`data/units`（JSON 與格子圖）上線要林津陞核可**：核可前不 commit、不 push。指揮艙發布只把 units 寫在工作資料夾 `site_units.json`，`git add` 一律排除 `data/units`（`':(exclude)data/units'`）；核可後由人明確 `git add data/units/<檔名>` 再 commit。

## 充電樁（2026-11-04 第四階段）

依據：本 repo `notes` 分支 `research/2026-11-04_充電樁與平面圖_法規研究.md`（A2 標籤與標準說法、C 節檢查規則）。**法規判斷只照報告，不自己推論；沒有證據就是「未查證」。**
- `data/communities.json` 每個社區可有 `ev`：`{"status":[標籤…],"basis":{"permit_no","permit_issued","commenced","use_permit_no","use_permit_issued","completed","rule","src":"參考政府公開資料"},"verified_at"}`。值**只能來自** property-deck 查證表 `facts_verified.json` 的 `ev` 列，由 `site_map.py` 寫入，**不要手改**；查證表沒有 ev 就整欄省略（不填 null）。
- 標籤只能用：`existing_needs_approval`（既有大樓：個別加裝需管委會同意與用電評估）、`law_space_108`（建照申請日 ≥ 108/7/1，依法預留裝設空間）、`ntpc_conduit_111`（新北集合住宅、建照核發日 ≥ 111/3/1，應全數預留管線）、`has_shared_charging`（社區設有公共充電設備）、`has_private_installed`（已有住戶在自有車位裝設）、`no_parking`（使照附表汽車位 0）、`unverified`（未查證）。法定基準最多一個；`unverified`、`no_parking` 只能單獨用；`has_*` 要有管委會書面公告、規約、本店照片、建商文件、竣工資料或補助名單等證據（記日期）與查證日 `verified_at`。
- 判斷用使照存根的原建照字號與日期：使照竣工／發照、建照核發或開工在 108/7/1 以前 → `existing_needs_approval`；建照在 108/7/1 以後核發但查不到申請（掛號）日 → `unverified`（不可標 law_space_108）。變更設計不改原建照申請日。
- 顯示：簡報「停車與充電」頁用報告的標準說法＋一般附註（「充電設備能否加裝，需依社區規約、管委會或區分所有權人會議決議，以及電機技師與台電的用電評估而定；本頁僅整理公開資料與查證紀錄，非施工或核准保證。」）；地圖資料卡「充電」一行用報告 C 節的短句，`unverified` 不顯示。`has_*` 查證日超過 12 個月，由瀏覽器當天日期即時顯示「待重新確認」，不寫死。
- **禁用**：「保證可裝」「一定可以」「管委會不能拒絕」「不得拒絕」「友善」（含「電動車友善社區」）。不寫充電費率、「隨時有位」、「很難裝」。標籤只寫類別，不寫「民國XX年建照」；字號只放在資料來源。
- 2026-11-04 現況：地圖 14 個社區標 `existing_needs_approval`（全部有原建照字號與 108/7/1 前的日期）；新濠一滙（興建中、沒有查證表）與鑽石名門（沒有查證表）沒有 ev。目前沒有任何社區有 has_* 證據。

## 屋齡（2026-11-04）

- 網頁上的屋齡**一律不寫死**：由瀏覽器在打開頁面時，依 `built`（完工年月）與當天日期（台灣時間）即時計算，例：地圖資料卡「屋齡 29 年（依完工年月自動計算）」。只有完工年、沒有月份時可能差一歲，**不顯示任何屋齡數字、不估算**，資料卡與清單顯示「屋齡：待查證完工月份」，地圖屋齡篩選歸到「完工月份待查」（林津陞 2026-11-04）；查到月份後把 `built` 補成「民國X年Y月」即可。地圖屋齡分組：3年內（新成屋）／3～5年／5～10年／10～20年／20～30年／30年以上／完工月份待查／興建中，同樣在瀏覽器即時計算。
- 靜態文字（title、meta description、og、JSON-LD、llms.txt、YouTube 說明、591 文案、影片字幕）仍然**不寫屋齡數字**，只寫完工年，因為這些不會自動更新。
- 簡報頁也即時計算（2026-11-04 第二階段）：社區簡報第 1 章事實欄「完工」旁邊多一格「屋齡」，由頁面 JS 依 `DECK.facts` 的完工年月與當天台灣時間計算，算法與本頁 `ageText()` 相同（property-deck `tests/test_age_live.cjs` 比對兩邊結果）。只有年份顯示「屋齡：待查證完工月份」；興建中不顯示；錄影版（影片）不顯示屋齡。noscript／靜態 HTML 不含屋齡數字。
- 完工月份一律用**使照發照日的月份**（不用竣工日）；查找順序：使照發照日 → 實價登錄「建築完成年月」（同社區多筆取最常出現的值）→ 建物登記謄本。來源月份不一致時列給林津陞決定（林津陞 2026-11-04）。
- 發布會擋：`data/communities.json` 的 `built` 不是「興建中」就必須是「民國X年Y月」，沒有月份 property-deck 發布直接停下（`site_map.py` validate／prepare）；靜態文字出現「屋齡＋數字」「N年屋」也會擋（`structured_data.py` 的 `AGE`，只掃 `<script>` 以外的文字）。`republish` 只更新地圖那筆的 `built`／`year`，其他人工校過的欄位不動。
