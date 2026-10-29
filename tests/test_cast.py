"""Capture keeps the frame rate and the device resolution while the scene's Python is busy."""
import time

from playwright.sync_api import sync_playwright

from demorec.cast import Cast

PAGE = ("<div id=n style='font:40px sans-serif'></div>"
        "<script>let i = 0; (function f() { n.textContent = i++; requestAnimationFrame(f) })()</script>")


def test_frames_while_python_is_busy(tmp_path):
    profile = str(tmp_path / "profile")
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            profile, headless=True, viewport={"width": 640, "height": 360}, device_scale_factor=2,
            args=["--force-device-scale-factor=2", "--remote-debugging-port=0"])
        pg = ctx.pages[0]
        pg.set_content(PAGE)
        cast = Cast(ctx, "t", 1280, 720, str(tmp_path / "work"), profile)
        cast.attach(pg)
        pg.wait_for_timeout(2000)  # past Chrome's one pause about 1.7 s after the screencast starts
        cast.start()
        t = time.time()
        while time.time() - t < 2:  # no Playwright call, the old in-process capture stalled here
            sum(range(10000))
        cast.stop()
        ctx.close()
    t0, end = cast._clock()
    ts = [f[0] for f in cast.frames if t0 <= f[0] <= end]
    assert len(ts) / (end - t0) > 40
    assert max(b - a for a, b in zip(ts, ts[1:])) < 0.1
    assert set(cast.sizes) == {(1280, 720)}
