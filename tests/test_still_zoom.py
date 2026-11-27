"""Large zooms rendered frame by frame: the paused recording clock, the stills and the video."""
import shutil, subprocess

import pytest
from playwright.sync_api import sync_playwright

from demorec.actor import Actor
from demorec.cast import Cast
from demorec.config import Config

FF = shutil.which("ffmpeg")


def solid(path, color="white"):
    subprocess.run([FF, "-v", "error", "-y", "-f", "lavfi", "-i", "color=%s:s=320x180" % color,
                    "-frames:v", "1", str(path)], check=True)
    return str(path)


def test_pause_cuts_the_wall_clock_and_resume_skips_ahead(tmp_path):
    cast = Cast(None, "t", 320, 180, str(tmp_path / "work"))
    cast.t0, cast.offset = 100.0, 0.0
    cast.pauses = [[102.0, 107.0, 1.0]]  # 5 s rendering stills for a 1 s move
    assert cast.paused(101.0) == 0
    assert cast.paused(104.0) == 2.0  # inside the pause the clock stands
    assert cast.paused(108.0) == 4.0  # after it: 5 s paused, 1 s skipped ahead
    a, b, c, s0, s1 = (str(tmp_path / n) for n in ("a", "b", "c", "s0", "s1"))
    cast.frames = [(101.0, a), (103.0, b), (108.0, c)]
    cast.stills = [(2.5, s0), (3.0, s1)]
    cast._apply_pauses()
    # b was screencast during the pause: dropped. c moves back by 4 s, the stills fill 2 to 3 s.
    assert cast.frames == [(101.0, a), (102.5, s0), (103.0, s1), (104.0, c)]


def test_elapsed_stands_still_while_paused(tmp_path):
    cast = Cast(None, "t", 320, 180, str(tmp_path / "work"))
    cast.start()
    cast.pause()
    with pytest.raises(RuntimeError):
        cast.pause()
    t = cast.elapsed()
    cast.pauses[-1][0] -= 3.0  # as if the pause had lasted 3 s
    assert cast.elapsed() == pytest.approx(t - 3.0, abs=0.05)
    cast.resume(advance=0.5)
    assert cast.elapsed() == pytest.approx(t - 2.5, abs=0.05)


def test_encode_shows_the_stills_at_their_time(tmp_path):
    white, black = solid(tmp_path / "w.jpg"), solid(tmp_path / "b.jpg", "black")
    cast = Cast(None, "t", 320, 180, str(tmp_path / "work"))
    cast.t0, cast.offset, cast.end = 0.0, 0.0, 6.0  # end is on the recording clock
    cast.frames = [(0.0, white), (2.5, white), (8.0, white)]  # the 2.5 s frame was taken during the pause
    cast.pauses = [[2.0, 6.0, 1.0]]
    cast.stills = [(2.0 + i / 30, black) for i in range(1, 31)]  # 1 s of black stills from 2 s on
    cast._apply_pauses()
    dst = str(tmp_path / "v.mp4")
    assert cast.encode(dst, FF, fps=30, log_dir=str(tmp_path)) == pytest.approx(6.0)

    def mean(t):
        return subprocess.run([FF, "-v", "error", "-ss", str(t), "-i", dst, "-frames:v", "1", "-vf", "scale=1:1",
                               "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout[0]
    assert mean(1.5) > 230 and mean(2.5) < 30
    assert mean(4.5) < 30  # the last still holds until the next screencast frame, 8 - (4 - 1) = 5 s
    assert mean(5.5) > 230


PAGE = """<body style='margin:0;background:#fff'>
<div style='position:absolute;left:200px;top:100px;width:32px;height:36px;background:#000'></div>
<table style='position:absolute;left:0;top:200px;width:640px;font:12px sans-serif'>%s</table></body>""" % (
    "<tr><td>Row</td><td>Customer</td><td>Item with a longer text</td><td>open</td></tr>" * 30)


def record_zoom_out(tmp_path, still):
    profile = str(tmp_path / "profile")
    cfg = Config(project_dir=str(tmp_path), name="t", url="", width=640, height=360, scale=2, still_zoom=still)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            profile, headless=True, viewport={"width": 640, "height": 360}, device_scale_factor=2,
            args=["--force-device-scale-factor=2", "--remote-debugging-port=0"])
        pg = ctx.pages[0]
        pg.set_content(PAGE)
        cast = Cast(ctx, "t", 1280, 720, str(tmp_path / "work"), profile)
        a = Actor(ctx, pg, cast, cfg)
        a.zoom((200, 100, 64, 36), pad=0)  # in setup: the video opens 10x zoomed in
        cast.attach(pg)
        pg.wait_for_timeout(500)
        cast.start()
        a.hold(1.0)
        a.zoom_out(dur=1.0, easing="spring-soft")
        a.hold(1.0)
        cast.stop()
        ctx.close()
    return a, cast


def test_large_zoom_out_is_rendered_frame_by_frame(tmp_path):
    a, cast = record_zoom_out(tmp_path, still=True)
    fps = max(a.cfg.fps, a.cfg.transition_fps)
    assert fps - 1 <= len(cast.stills) <= fps + 1  # one still per video frame of the 1 s move
    assert cast.stills[-1][0] == pytest.approx(2.0, abs=0.1) and cast.end - cast.t0 == pytest.approx(3.0, abs=0.2)
    assert not a.camera.rendering() and a.camera.render == [[0.0, 0.0, pytest.approx(2.0, abs=0.1)]]
    dst = str(tmp_path / "v.mp4")
    assert cast.encode(dst, FF, fps=fps, crf=12, log_dir=str(tmp_path), camera=a.camera) == pytest.approx(3.0, abs=0.2)
    s, d = a.camera.moves[-1][:2]
    for t in (s + 0.2 * d, s + 0.5 * d):
        # The black box in the video is as wide as the camera path says at that time.
        x, y, w, h = a.camera.at(t)
        cy = (118 - y) * 720 / h  # the middle of the box in the frame
        row = subprocess.run([FF, "-v", "error", "-ss", "%.3f" % t, "-i", dst, "-frames:v", "1", "-vf",
                              "crop=1280:2:0:%d" % (round(cy) // 2 * 2), "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                             capture_output=True, check=True).stdout[:1280]
        dark = sum(1 for v in row if v < 100)
        widths = [32 * 1280 / a.camera.at(t + k / fps)[2] for k in (-2, 2)]
        assert min(widths) - 4 <= dark <= max(widths) + 4, (t, dark, widths)


def test_live_zoom_when_still_zoom_is_off(tmp_path):
    a, cast = record_zoom_out(tmp_path, still=False)
    assert cast.stills == [] and cast.pauses == []
    assert a.camera.render == [[0.0, 0.0, pytest.approx(2.0, abs=0.1)]]
