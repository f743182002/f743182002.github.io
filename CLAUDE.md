# f743182002.github.io（板橋阿陞聊房 總站）

給接手的 AI 和發布程式看的規則。

## 網站結構

- `index.html`：總站首頁（2026-11-02 起）。社區分析、物件清單是**執行時讀 `decks.json` 產生的**。
- `map/index.html`：阿陞的商圈地圖（Leaflet＋OpenStreetMap），資料來自 `data/communities.json`。
- `assets/site.css`：首頁與地圖共用的樣式。
- `community/<社區名>/`、`S<編號>/`：各社區／物件的互動簡報（由 property-deck 指揮艙發布）。

## 發布新簡報時

1. **不要再用清單覆寫 `index.html`。** 舊的發布流程會把 index.html 重寫成純清單，總站會整個不見。現在只要更新 `decks.json`（加一筆 `"community/<社區名>": {name, subtitle, area, updated}`），首頁就會自動列出。
2. 社區版另外在 `data/communities.json` 的 `communities` 加一筆，地圖才會出現。欄位照現有格式填，`deck` 填 `community/<社區名>/`；只能用查證表（facts_verified.json）裡已查證的值。座標用簡報 data.js 的 `SITE.lat/lon`（建物輪廓中心），不用 591 座標。指揮艙發布時會自動寫入，不用手動加（property-deck `site_map.py`：同名社區只更新那一筆、新社區加在最後；檢查不過整個發布不 push）。
3. 簡報還沒發布的社區，`deck` 填 `null`，清單會顯示「簡報製作中」。

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

- `scripts/door_layout.py` 產生 `data/layout/<社區名>.svg` 與 `data/layout/index.json`；地圖資料卡有檔案才顯示「看棟別配置圖」。重跑：`python3 scripts/door_layout.py .`
- 資料只用本站自己的：簡報內嵌 `window.SITE` 的本社區建物輪廓（me=1）與道路、`data/doors/<社區名>.json` 門牌定位（property-deck scope_check 的國土測繪中心門牌定位結果，格式 `{"doors":[{"no":"191","lat":..,"lon":..}]}`）。門牌落在本社區輪廓 8 公尺內才標上去。
- **不可以參考、描繪樂居或其他網站的配置圖或平面圖。** 只標門牌號，不標樓層、戶號、住戶資訊。

## 屋齡（2026-11-04）

- 網頁上的屋齡**一律不寫死**：由瀏覽器在打開頁面時，依 `built`（完工年月）與當天日期（台灣時間）即時計算，例：地圖資料卡「屋齡 29 年（依完工年月自動計算）」。只有完工年沒有月份時顯示「約 N 年（依完工年自動推算）」。
- 靜態文字（title、meta description、og、JSON-LD、llms.txt、YouTube 說明、591 文案、影片字幕）仍然**不寫屋齡數字**，只寫完工年，因為這些不會自動更新。
