// Drawn cursor. Headless Chrome has no visible pointer, so the page draws one that follows
// the mouse events Playwright sends, and shrinks it while the button is down.
(() => {
  if (window.top !== window) return;
  const SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="32" viewBox="0 0 24 32"><path d="M3 2 L3 25 L8.6 19.6 L12.6 29 L16.2 27.5 L12.3 18.3 L19.8 18.3 Z" fill="#111" stroke="#fff" stroke-width="1.8" stroke-linejoin="round"/></svg>';
  function el() {
    let c = document.getElementById('__rec_cursor');
    if (!c && (document.body || document.documentElement)) {
      c = document.createElement('div'); c.id = '__rec_cursor';
      c.style.cssText = 'position:fixed;left:-50px;top:-50px;width:24px;height:32px;z-index:2147483647;pointer-events:none;transform-origin:3px 2px;transition:transform 90ms ease-out;';
      c.innerHTML = SVG;
      (document.body || document.documentElement).appendChild(c);
    }
    return c;
  }
  window.__recCursor = (x, y) => { const c = el(); if (c) { c.style.left = (x - 3) + 'px'; c.style.top = (y - 2) + 'px'; } };
  addEventListener('mousemove', e => window.__recCursor(e.clientX, e.clientY), true);
  addEventListener('mousedown', () => { const c = el(); if (c) c.style.transform = 'scale(0.82)'; }, true);
  addEventListener('mouseup', () => { const c = el(); if (c) c.style.transform = 'scale(1)'; }, true);
  // Keep the cursor above elements that the app appends later (dialogs, menus).
  new MutationObserver(() => { const c = document.getElementById('__rec_cursor'); if (c && c.parentNode === document.body && document.body.lastElementChild !== c) document.body.appendChild(c); })
    .observe(document.documentElement, { childList: true, subtree: false });
})();
