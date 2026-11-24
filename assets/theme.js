/* 深色模式開關（林津陞 2026-11-24：「這個能不能跟上架中心一樣 有個深色模式開關阿 晚上看了很刺眼」）
   - 預設淺色：11/11 林津陞「大部分都深色 可是文字很淺 辨識度很差」，所以不跟手機／電腦的深色設定，按了才變深色。
   - 選擇記在這台瀏覽器（localStorage sa-theme），下次打開同一頁、其他頁都一樣。
   - 做法同查詢台：整頁反轉亮度＋色相轉回；照片、影片、地圖、3D 畫面、深色主視覺再轉回原色。
   - 按鈕在右下角（11/24 林津陞：「這個深色擋住了 移動到右下去」，原本左下擋到頁尾文字）。
   - 錄影版（html.rec）、列印一律淺色、不顯示按鈕。
   每頁 <head> 由 scripts/structured_data.py 自動帶入（THEME 標記），不要手動刪。 */
(function () {
  var K = 'sa-theme', R = document.documentElement;
  function saved() { try { return localStorage.getItem(K) === 'dark'; } catch (e) { return false; } }
  function save(dark) { try { localStorage.setItem(K, dark ? 'dark' : 'light'); } catch (e) {} }
  var D = 'html.sa-dark:not(.rec)';
  var keep = ['img', 'video', 'canvas', 'iframe', 'svg#map', '.leaflet-container', '.sa-keep'];
  var css =
    D + '{filter:invert(.9) hue-rotate(180deg);background:#fff}' +
    keep.map(function (s) { return D + ' ' + s; }).join(',') + '{filter:invert(1) hue-rotate(180deg)!important}' +
    ['svg#map', '.leaflet-container', '.sa-keep'].map(function (p) {
      return ['img', 'video', 'canvas', 'iframe'].map(function (s) { return D + ' ' + p + ' ' + s; }).join(',');
    }).join(',') + '{filter:none!important}' +
    D + ' img[src*="logo"]:not(.sa-keep img),' + D + ' img[src*="brand/icon"]:not(.sa-keep img){filter:none!important}' +  // 近黑 LOGO 在深色頁首跟著反轉成淺色才看得到

    '#sa-theme-btn{position:fixed;right:12px;bottom:12px;z-index:2147483000;display:flex;align-items:center;gap:6px;' +
    'font:600 14px/1 system-ui,"PingFang TC","Microsoft JhengHei",sans-serif;padding:9px 13px;border-radius:999px;' +
    'border:1px solid #B9D0DE;background:#FFFFFF;color:#0F2233;box-shadow:0 2px 10px rgba(15,34,51,.18);cursor:pointer}' +
    '#sa-theme-btn:hover{background:#F2F8FB}' +
    'html.rec #sa-theme-btn{display:none}@media print{#sa-theme-btn{display:none}html.sa-dark{filter:none}}';
  var st = document.createElement('style');
  st.id = 'sa-theme-css';
  st.textContent = css;
  (document.head || R).appendChild(st);
  if (saved()) R.classList.add('sa-dark');

  function dark() { return R.classList.contains('sa-dark'); }
  function label(b) {
    b.innerHTML = dark() ? '<span class="sa-keep">☀️</span>淺色' : '<span class="sa-keep">🌙</span>深色';
    b.setAttribute('aria-label', dark() ? '切換成淺色' : '切換成深色');
    b.title = b.getAttribute('aria-label');
  }
  function isDark(cs) {  // 底色（或漸層第一個顏色）本來就是深色、不透明
    var bi = cs.backgroundImage, m;
    if (bi && bi !== 'none' && bi.indexOf('gradient') >= 0) m = bi.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?/);
    if (!m) m = cs.backgroundColor.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?/);
    if (!m || (m[4] !== undefined && +m[4] < 0.6)) return false;
    return (+m[1] + +m[2] + +m[3]) / 3 < 90;
  }
  function markDark() {  // 深藍主視覺、深色卡片、深色按鈕本來就是深色：維持原色不反轉（外層已保留的就不再重複）
    var els = document.body.getElementsByTagName('*');
    for (var i = 0; i < els.length; i++) {
      var el = els[i], tag = el.tagName;
      if (tag === 'SCRIPT' || tag === 'STYLE' || el.id === 'sa-theme-btn' || el.closest('#sa-theme-btn')) continue;
      if (el.parentElement && el.parentElement.closest('.sa-keep')) continue;
      if (el.classList.contains('sa-keep')) continue;
      var pb = getComputedStyle(el, '::before');  // 首頁主視覺的深藍是畫在 ::before 這層
      var big = parseFloat(pb.height) >= el.offsetHeight * 0.6 && parseFloat(pb.width) >= el.offsetWidth * 0.6;  // 上緣細線不算
      var cs = getComputedStyle(el);
      if (isDark(cs) || cs.backgroundImage.indexOf('url(') >= 0 || (pb.content !== 'none' && pb.position === 'absolute' && big && isDark(pb)))
        el.classList.add('sa-keep', 'sa-auto');
    }
  }
  function place(b) {  // 手機底部有固定列（LINE、電話）時，開關移到它上面，不擋按鈕
    var off = 0, vh = window.innerHeight, els = document.body.getElementsByTagName('*');
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      if (el === b || b.contains(el)) continue;
      var cs = getComputedStyle(el);
      if (cs.position !== 'fixed' || cs.display === 'none' || cs.visibility === 'hidden') continue;
      var r = el.getBoundingClientRect();
      if (r.height > 0 && r.height < vh * 0.4 && r.bottom >= vh - 4 && r.right > window.innerWidth - 120) off = Math.max(off, vh - r.top);
    }
    b.style.bottom = (off + 12) + 'px';
  }
  function init() {
    if (document.getElementById('sa-theme-btn')) return;
    markDark();
    var b = document.createElement('button');
    b.id = 'sa-theme-btn';
    b.type = 'button';
    label(b);
    b.onclick = function () {
      R.classList.toggle('sa-dark');
      save(dark());
      label(b);
    };
    document.body.appendChild(b);
    place(b);
    var tm;
    window.addEventListener('resize', function () { clearTimeout(tm); tm = setTimeout(function () { place(b); }, 300); });
    window.addEventListener('load', function () { markDark(); place(b); });  // 簡報頁有些區塊是載入後才畫出來的，再找一次
    setTimeout(function () { markDark(); place(b); }, 2500);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
