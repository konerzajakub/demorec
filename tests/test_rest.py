"""The cursor at rest: next to a result, never on its text."""
import pytest
from playwright.sync_api import sync_playwright

from demorec.actor import CURSOR_H, CURSOR_W, Actor
from demorec.browser import CURSOR_JS
from demorec.config import Config

PAGE = """<body style='margin:0;font:16px sans-serif'>
<div id=total style='position:absolute;left:100px;top:100px;width:220px;height:40px'>Total 1 250.00 EUR</div>
<div id=wide style='position:absolute;left:0;top:200px;width:640px;height:60px;font-size:40px'>
  A line of text that runs from edge to edge of the page</div>
<div style='position:absolute;left:0;top:260px;width:640px;height:100px;font-size:40px;overflow:hidden'>
  More text right under it, all the way down to the bottom</div>
</body>"""


def text_boxes(pg):
    return pg.evaluate("""() => { const out = [], w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      const r = document.createRange();
      for (let n = w.nextNode(); n; n = w.nextNode()) { if (!n.textContent.trim()) continue; r.selectNodeContents(n);
        for (const b of r.getClientRects()) out.push([b.left, b.top, b.right, b.bottom]); } return out; }""")


@pytest.fixture
def actor(tmp_path):
    cfg = Config(project_dir=str(tmp_path), name="t", url="", width=640, height=360, scroll=False)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 640, "height": 360})
        pg.add_init_script(CURSOR_JS)
        page = tmp_path / "page.html"
        page.write_text(PAGE, encoding="utf-8")
        pg.goto(page.as_uri())  # init scripts run on navigation, not on set_content
        pg.mouse.move(600, 20)  # the drawn cursor appears with the first mouse event
        a = Actor(None, pg, None, cfg)
        a.speed = 0.05
        yield a
        b.close()


def test_rest_beside_the_text(actor):
    a = actor
    x, y = a.rest(a.pg.locator("#total"))
    assert (a.mx, a.my) == (x, y)
    left, top, right, bottom = x, y, x + CURSOR_W, y + CURSOR_H
    for l, t, r, b in text_boxes(a.pg):
        assert right < l or left > r or bottom < t or top > b  # the arrow covers no text
    total = a.pg.locator("#total").bounding_box()
    assert abs(y - (total["y"] + total["height"] / 2)) < 60 and x < total["x"] + total["width"] + 60  # still at the result
    assert a.pg.evaluate("!!document.querySelector('#__rec_cursor svg')")
    assert a.rest(a.pg.locator("#total")) == (x, y)  # the drawn cursor itself is no obstacle


def test_rest_without_a_free_spot_goes_to_the_corner(actor):
    a = actor
    wide = a.pg.locator("#wide")
    x, y = a.rest(wide)
    bb = wide.bounding_box()
    assert (x, y) == pytest.approx((bb["x"] + bb["width"] * 0.95, bb["y"] + bb["height"] * 0.9))
