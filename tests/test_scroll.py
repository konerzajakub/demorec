"""Scrolling: the eased wheel steps, their timing in the browser, center() and visible()."""
import time

import pytest
from playwright.sync_api import sync_playwright

from demorec import config
from demorec.actor import Actor
from demorec.config import Config
from demorec.motion import SCROLL_MIN_DUR, SCROLL_RATE, SCROLL_SPEED, scroll_duration, scroll_steps

# Every wheel event with its time and delta, and every scroll position of the page or the panel.
PAGE = """<style>body { margin: 0 } .row { height: 40px; border-bottom: 1px solid #ccc }</style>
<div id=rows></div>
<div id=panel style='position:fixed;right:0;top:0;width:200px;height:300px;overflow:auto'>
  <div style='height:1500px'></div><div id=deep style='height:30px'>deep</div><div style='height:600px'></div>
</div>
<script>
  for (let i = 0; i < 100; i++) rows.insertAdjacentHTML('beforeend', `<div class=row id=r${i}>row ${i}</div>`);
  window.wheels = []; window.scrolls = [];
  addEventListener('wheel', e => wheels.push([performance.now(), e.deltaY, e.isTrusted]), {passive: true});
  addEventListener('scroll', () => scrolls.push([performance.now(), scrollY]));
  panel.addEventListener('scroll', () => scrolls.push([performance.now(), panel.scrollTop]));
</script>"""


def test_steps_add_up_and_ease_in_and_out():
    for dist in (600, -600, 37, 2000):
        steps = scroll_steps(dist, 1.0, "ease-in-out")
        assert sum(s for _, s in steps) == dist
        assert all(s * dist > 0 for _, s in steps)  # never back
        assert all(a < b for (a, _), (b, _) in zip(steps, steps[1:]))
        assert 0.9 <= steps[-1][0] <= 1.0  # the last ticks of a short scroll may have nothing left
    steps = [abs(s) for _, s in scroll_steps(600, 1.0, "ease-in-out")]
    assert SCROLL_RATE - 4 <= len(steps) <= SCROLL_RATE  # one per tick, bar ticks under 1 px at the ends
    assert max(steps[:3]) < max(steps) / 4 and max(steps[-3:]) < max(steps) / 4  # slow ends
    assert max(steps) == pytest.approx(600 / SCROLL_RATE * 1.72, rel=0.1)  # CSS ease-in-out peaks at 1.7x
    linear = [s for _, s in scroll_steps(600, 1.0, "linear")]
    assert set(linear) == {10}


def test_duration_follows_the_distance():
    assert scroll_duration(SCROLL_SPEED) == pytest.approx(1.0)
    assert scroll_duration(-2 * SCROLL_SPEED, SCROLL_SPEED) == pytest.approx(2.0)
    assert scroll_duration(10) == SCROLL_MIN_DUR  # a short scroll is still seen to move
    assert scroll_duration(600, 1200) == pytest.approx(0.5)


def test_scroll_settings_in_project_toml(tmp_path):
    toml = tmp_path / "project.toml"
    toml.write_text('[app]\nurl = "http://x/"\n', encoding="utf-8")
    cfg = config.load(tmp_path)
    assert (cfg.scroll_easing, cfg.scroll_speed) == ("ease-in-out", SCROLL_SPEED)
    toml.write_text('[app]\nurl = "http://x/"\n[motion]\nscroll_easing = "quint"\nscroll_speed = 300\n', encoding="utf-8")
    cfg = config.load(tmp_path)
    assert (cfg.scroll_easing, cfg.scroll_speed) == ("quint", 300)
    for bad in ('scroll_easing = "wobbly"', "scroll_speed = 0"):
        toml.write_text('[app]\nurl = "http://x/"\n[motion]\n%s\n' % bad, encoding="utf-8")
        with pytest.raises(SystemExit, match=bad.split()[0]):
            config.load(tmp_path)


@pytest.fixture
def actor(tmp_path):
    cfg = Config(project_dir=str(tmp_path), name="t", url="", width=640, height=360, scroll_speed=1000,
                 safe_top=0, safe_bottom=0)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 640, "height": 360})
        pg.set_content(PAGE)
        a = Actor(None, pg, None, cfg)
        pg.mouse.move(300, 200)
        yield a
        b.close()


def test_wheel_glides_with_real_wheel_events(actor):
    a = actor
    t0 = time.time()
    a.wheel(600)  # 0.6 s at 1000 px/s
    took = time.time() - t0
    a.pg.wait_for_timeout(100)
    assert a.pg.evaluate("scrollY") == 600
    wheels = a.pg.evaluate("wheels")
    assert sum(d for _, d, _ in wheels) == 600 and all(trusted for _, _, trusted in wheels)
    assert 0.55 < took < 0.9
    span = (wheels[-1][0] - wheels[0][0]) / 1000
    assert 0.45 < span < 0.8 and len(wheels) >= 30  # spread over the duration, not a burst
    deltas = [d for _, d, _ in wheels]
    assert max(deltas[:3]) < max(deltas) / 3 and max(deltas[-3:]) < max(deltas) / 3


def test_wheel_takes_dur_and_easing_per_call(actor):
    a = actor
    t0 = time.time()
    a.wheel(-0)
    a.wheel(300, dur=0.3, easing="linear")
    assert time.time() - t0 < 0.5
    a.pg.wait_for_timeout(100)
    assert a.pg.evaluate("scrollY") == 300
    deltas = [d for _, d, _ in a.pg.evaluate("wheels")]
    assert max(deltas) - min(deltas) <= 1  # linear: equal steps, but whole px
    a.speed = 0.01  # check mode skips most of the time, and counts it
    t0 = time.time()
    a.wheel(-300)
    assert time.time() - t0 < 0.2 and a.saved == pytest.approx(0.3 * 0.99)


def test_center_glides_the_panel(actor):
    a = actor
    deep = a.pg.locator("#deep")
    t0 = time.time()
    a.center(deep)
    assert time.time() - t0 > 1.0  # about 1385 px at 1000 px/s, plus the settle
    panel = a.pg.evaluate("[panel.scrollTop, scrolls.length]")
    assert panel[0] == pytest.approx(1500 + 15 - 150, abs=1)  # the row sits in the panel's middle
    assert panel[1] > 20  # many positions on the way, no jump
    assert a.pg.evaluate("scrollY") == 0  # the page stays where it was


def test_visible_lands_the_target(actor):
    a = actor
    row = a.pg.locator("#r60")
    a.visible(row, land=0.35)
    y = row.bounding_box()["y"]
    assert 360 * 0.2 <= y <= 360 * 0.5
    assert len(a.pg.evaluate("wheels")) > 30  # a glide, not a jump
