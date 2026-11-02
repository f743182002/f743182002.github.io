# f743182002.github.io（板橋阿陞聊房 總站）

給接手的 AI 和發布程式看的規則。

## 網站結構

- `index.html`：總站首頁（2026-11-02 起）。社區分析、物件清單是**執行時讀 `decks.json` 產生的**。
- `map/index.html`：阿陞的商圈地圖（Leaflet＋OpenStreetMap），資料來自 `data/communities.json`。
- `assets/site.css`：首頁與地圖共用的樣式。
- `community/<社區名>/`、`S<編號>/`：各社區／物件的互動簡報（由 property-deck 指揮艙發布）。

## 發布新簡報時

1. **不要再用清單覆寫 `index.html`。** 舊的發布流程會把 index.html 重寫成純清單，總站會整個不見。現在只要更新 `decks.json`（加一筆 `"community/<社區名>": {name, subtitle, area, updated}`），首頁就會自動列出。
2. 社區版另外在 `data/communities.json` 的 `communities` 加一筆，地圖才會出現。欄位照現有格式填，`deck` 填 `community/<社區名>/`；只能用查證表（facts_verified.json）裡已查證的值。座標用簡報 data.js 的 `SITE.lat/lon`（建物輪廓中心），不用 591 座標。
3. 簡報還沒發布的社區，`deck` 填 `null`，清單會顯示「簡報製作中」。

## 生活圈分類

`data/communities.json` 的 `areas`。目前以最近的捷運站分生活圈，之後要改成樂居的分區，改 `areas` 名稱和每個社區的 `area` 就好。

## 法遵

頁尾完整版揭露三行不可刪；只放手機＋LINE；禁用詞照 realtor-ad-compliance 技能。
