// 售價只由 PROPERTY.price 提供，供首頁、簡報售價欄位與頁面標題共用。
(() => {
  'use strict';
  const render = (config, doc) => {
    doc.title = `${config.title}｜3房2廳2衛｜總價${config.price}萬`;
    doc.querySelectorAll('[data-price]').forEach(element => {
      element.textContent = `總價 ${config.price} 萬`;
    });
    doc.getElementById('hero-photo').src = 'assets/photos/' + config.heroPhoto;
    doc.querySelector('meta[property="og:image"]').setAttribute('content', new URL('assets/photos/' + config.heroPhoto, location.href).href);
  };
  window.ListingView = {render};
  render(window.PROPERTY, document);
})();
