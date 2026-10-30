"""Camera path: framing, clamping, easing, render mode, the ffmpeg expressions and the zoomed video."""
import json, os, re, shutil, subprocess, sys, time

import pytest
from playwright.sync_api import sync_playwright

from demorec.actor import Actor
from demorec.camera import SWITCH_HOLD, Camera, fit, follow
from demorec.cast import Cast, run_watched
from demorec.config import Config
from demorec.motion import pan_duration

W, H = 1280, 720
FF = shutil.which("ffmpeg")


def test_fit_frames_target_with_padding_and_aspect():
    x, y, w, h = fit((600, 300, 200, 60), W, H, pad=24, max_zoom=10)
    assert w / h == pytest.approx(W / H)
    assert w == pytest.approx(248) and h == pytest.approx(139.5)  # 200 + 2 * 24 wide fills the width
    assert (x + w / 2, y + h / 2) == pytest.approx((700, 330))  # centered on the target


def test_fit_clamps_zoom_and_stays_in_viewport():
    assert fit((10, 10, 20, 10), W, H)[2] == pytest.approx(W / 12)  # tiny target: max zoom
    assert fit((10, 10, 20, 10), W, H, max_zoom=2.5)[2] == pytest.approx(W / 2.5)
    assert fit((0, 0, 2000, 900), W, H) == (0, 0, W, H)  # larger than the screen: never below 1
    assert fit((100, 100, 50, 50), W, H, scale=0.5) == (0, 0, W, H)
    x, y, w, h = fit((0, 0, 40, 20), W, H)  # top left corner: the view does not leave the page
    assert (x, y) == (0, 0)
    x, y, w, h = fit((1250, 700, 30, 20), W, H, scale=2)
    assert (x + w, y + h) == pytest.approx((W, H)) and w == W / 2


def test_fit_a_logo_fills_the_frame():
    """A 100 x 40 px logo with the default padding: about 8x, inside max_zoom."""
    x, y, w, h = fit((24, 8, 100, 40), W, H)
    assert W / w == pytest.approx(H / (40 + 48))  # the height with padding fills the frame


@pytest.mark.parametrize("easing", ["spring", "human", "ease-in-out", "cubic", "quint", "smoothstep"])
def test_path_eases_and_holds(easing):
    cam = Camera(W, H)
    to = fit((100, 100, 200, 100), W, H)
    cam.move(1.0, to, 0.8, easing)
    assert cam.at(0.5) == cam.full and cam.at(1.0) == cam.full
    assert cam.at(1.8) == to and cam.at(10) == to
    widths = [cam.at(1 + 0.8 * i / 20)[2] for i in range(21)]
    assert all(a > b for a, b in zip(widths, widths[1:]))  # zooms in all the way, never back
    assert widths[1] - widths[2] > widths[0] - widths[1]  # eases in
    assert widths[-3] - widths[-2] > widths[-2] - widths[-1]  # eases out
    for t in (1.2, 1.4, 1.6):
        assert cam.at(t)[2] / cam.at(t)[3] == pytest.approx(W / H)


def test_overshooting_spring_stays_inside_the_page():
    cam = Camera(W, H)
    cam.move(0, fit((0, 0, 100, 50), W, H), 0)
    cam.move(0, cam.full, 1.0, "bouncy")  # overshoots past the full frame: clamped
    for i in range(41):
        x, y, w, h = cam.at(i / 40)
        assert w <= W and x >= 0 and y >= 0 and x + w <= W + 1e-9 and y + h <= H + 1e-9


def test_zoom_keeps_a_point_in_place():
    """Linear rect edges with a log-paced width: one screen point stays where it is."""
    cam = Camera(W, H)
    to = fit((900, 500, 100, 50), W, H)
    cam.move(0, to, 1)
    px = to[0] / (1 - to[2] / W)  # the point at the same relative place in both views
    for t in (0.25, 0.5, 0.75):
        x, _, w, _ = cam.at(t)
        assert (px - x) / w == pytest.approx(px / W)


def test_next_move_starts_where_the_camera_is():
    cam = Camera(W, H)
    a, b = fit((0, 0, 100, 50), W, H), fit((800, 400, 300, 150), W, H)
    cam.move(0, a, 1)
    cam.move(0.5, b, 1)  # before the first one ends
    mid = cam.at(0.5)
    assert cam.moves[-1][2] == mid and cam.at(1.5) == b
    cam.move(2, cam.full, 0.8)
    assert cam.at(3) == cam.full and cam.busy_until() == pytest.approx(2.8)


def test_follow_pans_to_keep_the_cursor_inside():
    view = (100, 100, 512, 288)
    assert follow(view, 300, 200, W, H) == view
    x, y, w, h = follow(view, 1000, 200, W, H)
    assert (w, h, y) == (512, 288, 100) and x + w * 0.9 == pytest.approx(1000)
    assert follow(view, 1279, 719, W, H) == (W - 512, H - 288, 512, 288)


def test_render_mode_leaves_the_frames_uncropped():
    cam = Camera(W, H)
    crop = fit((300, 200, 600, 300), W, H)  # about 1.9x: cropped
    deep = fit((300, 200, 60, 30), W, H)
    cam.move(1.0, crop, 0.5)
    cam.render_on(2.0, SWITCH_HOLD)
    cam.move(2.0 + SWITCH_HOLD, deep, 1.0)
    cam.move(4.0, cam.full, 1.0)
    cam.render_off(5.0)
    assert cam.crop_at(1.8) == crop
    assert cam.crop_at(2.05) == crop  # the camera stands still while the browser takes over
    assert cam.crop_at(2.5) == cam.full and cam.crop_at(4.5) == cam.full  # the browser renders
    assert cam.at(2.5) != cam.full  # the path itself goes on
    assert cam.holds() == [(2.0, 2.0 + SWITCH_HOLD)]
    assert not cam.rendering()
    only = Camera(W, H)
    only.render_on(0)
    only.move(0, deep, 0)
    assert only.filter(2, 30, 5) is None  # nothing to crop


def ffmpeg_eval(expr, n):
    """Evaluate a camera expression the way ffmpeg would, at frame number n (from 1)."""
    py = expr.replace("if(", "iff(").replace("lt(in,", "lt(IN,")
    env = {"iff": lambda c, a, b: a if c else b, "lt": lambda a, b: a < b, "IN": n}
    return eval(py, env)


def test_filter_expressions_match_the_path():
    cam = Camera(W, H)
    cam.move(0.5, fit((300, 200, 120, 40), W, H, max_zoom=2.5), 0.8, "spring")
    cam.move(2.0, fit((900, 500, 120, 40), W, H, scale=1.5), 0.6, "quint")
    cam.move(3.5, cam.full, 0.8, "bouncy")
    f = cam.filter(2, 30, 5.0)
    opts = dict(re.findall(r"([xy][0-3])='([^']*)'", f))
    assert len(opts) == 8
    for n in range(1, 151):
        x, y, w, h = cam.at((n - 1) / 30)
        assert ffmpeg_eval(opts["x0"], n) == pytest.approx(2 * x, abs=0.01)
        assert ffmpeg_eval(opts["y3"], n) == pytest.approx(2 * (y + h), abs=0.01)
    assert "enable='between(t," in f
    assert max(len(v) for v in opts.values()) < 20000  # a balanced tree, not one branch per frame in a chain


def solid(path, size, color="white", box=None):
    vf = "drawbox=%s:black:fill" % box if box else "null"
    subprocess.run([FF, "-v", "error", "-y", "-f", "lavfi", "-i", "color=%s:s=%s" % (color, size), "-vf", vf,
                    "-frames:v", "1", str(path)], check=True)
    return str(path)


def mean(video, t):
    r = subprocess.run([FF, "-v", "error", "-ss", str(t), "-i", video, "-frames:v", "1", "-vf", "scale=1:1",
                        "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True)
    return r.stdout[0]


def duration(video):
    probe = subprocess.run([shutil.which("ffprobe"), "-v", "error", "-show_entries", "format=duration",
                            "-of", "json", video], capture_output=True, text=True, check=True)
    return float(json.loads(probe.stdout)["format"]["duration"])


def test_encoded_video_is_zoomed(tmp_path):
    """A white frame with a black top left quadrant: zoomed on that quadrant the video is black."""
    src = solid(tmp_path / "f.jpg", "320x180", box="0:0:160:90")
    cast = Cast(None, "t", 320, 180, str(tmp_path / "work"))
    cast.frames, cast.t0, cast.end, cast.offset = [(0.0, src)], 0.0, 3.0, 0.0
    cam = Camera(160, 90)  # 2 device px per CSS px
    cam.move(1.0, fit((0, 0, 80, 45), 160, 90, pad=0), 0.5)
    dst = str(tmp_path / "v.mp4")
    cast.encode(dst, FF, fps=30, log_dir=str(tmp_path), camera=cam)
    assert 170 < mean(dst, 0.5) < 210  # a quarter black
    assert mean(dst, 2.5) < 30  # all black
    assert abs(duration(dst) - 3.0) < 0.1
    key = str(tmp_path / "k.jpg")
    assert cast.still(2.5, key, FF, cam)
    r = subprocess.run([FF, "-v", "error", "-i", key, "-vf", "scale=1:1", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                       capture_output=True, check=True)
    assert r.stdout[0] < 30


def test_zoom_lands_in_time_after_frames_of_another_size(tmp_path):
    """A frame of another size used to restart ffmpeg's filter graph and with it the camera's
    frame count, so every later zoom came late. Now such frames are fitted before the encode."""
    big = solid(tmp_path / "big.jpg", "320x180", box="0:0:160:90")
    small = solid(tmp_path / "small.jpg", "200x180", box="0:0:100:90")  # another size and aspect
    cast = Cast(None, "t", 320, 180, str(tmp_path / "work"))
    cast.frames = [(0.0, big), (1.0, small), (2.0, big)]
    cast.frame_size = {small: (200, 180)}
    cast.t0, cast.end, cast.offset = 0.0, 6.0, 0.0
    cam = Camera(160, 90)
    cam.move(3.0, fit((0, 0, 80, 45), 160, 90, pad=0), 0)  # jump to the black quadrant at 3 s
    dst = str(tmp_path / "v.mp4")
    cast.encode(dst, FF, fps=30, log_dir=str(tmp_path), camera=cam)
    assert mean(dst, 2.5) > 150  # not zoomed yet
    assert mean(dst, 3.3) < 30  # zoomed at 3 s, not 1 or 2 s later
    assert "Reconfiguring" not in open(tmp_path / "encode-t.err.log", encoding="utf-8", errors="replace").read()


def test_transient_frame_of_another_size_is_dropped(tmp_path):
    white = solid(tmp_path / "w.jpg", "320x180")
    odd = solid(tmp_path / "o.jpg", "320x150", color="black")
    cast = Cast(None, "t", 320, 180, str(tmp_path / "work"))
    cast.frames = [(0.0, white), (1.0, odd), (1.2, white), (2.0, odd)]  # the last one stays on screen
    cast.frame_size = {odd: (320, 150)}
    cast.t0, cast.end, cast.offset = 0.0, 3.0, 0.0
    kept = cast._usable_frames(cast.frames)
    assert kept == [(0.0, white), (1.2, white), (2.0, odd)]


def test_long_held_frame_finishes(tmp_path):
    a, b = solid(tmp_path / "a.jpg", "320x180"), solid(tmp_path / "b.jpg", "320x180", color="black")
    cast = Cast(None, "t", 320, 180, str(tmp_path / "work"))
    cast.frames, cast.t0, cast.end, cast.offset = [(0.0, a), (40.0, b)], 0.0, 41.0, 0.0
    cam = Camera(160, 90)
    cam.move(1.0, fit((0, 0, 80, 45), 160, 90, pad=0), 1.0)
    dst = str(tmp_path / "v.mp4")
    t = time.time()
    cast.encode(dst, FF, fps=30, log_dir=str(tmp_path), camera=cam)
    assert time.time() - t < 60
    assert abs(duration(dst) - 41.0) < 0.1
    lst = open(os.path.join(cast.dir, "list.txt"), encoding="utf-8").read()
    assert max(float(d) for d in re.findall(r"duration ([\d.]+)", lst)) <= 2.0


@pytest.mark.skipif(sys.platform == "win32", reason="needs a shell script as a stand-in for ffmpeg")
def test_stuck_encoder_is_stopped(tmp_path):
    fake = tmp_path / "ffmpeg"
    fake.write_text("#!/bin/sh\nsleep 30\n")
    fake.chmod(0o755)
    t = time.time()
    with pytest.raises(RuntimeError, match="no progress"):
        run_watched([str(fake), "-i", "x"], str(tmp_path / "enc"), stall=1)
    assert time.time() - t < 10


def test_actor_zoom_takes_rect_from_locator(tmp_path):
    cfg = Config(project_dir=str(tmp_path), name="t", url="", width=640, height=360, max_zoom=2.5)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 640, "height": 360})
        pg.set_content("<div id=t style='position:absolute;left:100px;top:50px;width:200px;height:40px'>x</div>")
        a = Actor(None, pg, None, cfg)
        a.render = False
        a.zoom(pg.locator("#t"), pad=10)
        a.zoom_out(easing="quint")
        b.close()
    (s, d, _, view, easing), out = a.camera.moves
    assert (s, d, easing) == (0, 0, "spring")  # not recording yet: the camera jumps, the video opens zoomed in
    assert view == pytest.approx(fit((100, 50, 200, 40), 640, 360, pad=10, max_zoom=2.5))
    assert out[3] == a.camera.full and out[4] == "quint"



def test_zoom_at_the_same_scale_is_a_pan_with_its_own_defaults(tmp_path):
    cfg = Config(project_dir=str(tmp_path), name="t", url="", width=640, height=360)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 640, "height": 360})
        a = Actor(None, pg, None, cfg)
        a.render = False
        a.speed = 0.01  # the holds that show each move, not their recorded length
        a._rolling = lambda: True
        a._now = lambda: 0.0
        a.zoom((100, 100, 10, 10), scale=1.4)
        a.zoom((500, 100, 10, 10), scale=1.4)                  # pan, pan defaults
        a.zoom((100, 100, 10, 10), scale=1.4, dur=0.5, easing="linear")  # pan, per call
        a.zoom((100, 100, 10, 10), scale=1.2)                  # another zoom: zoom defaults
        b.close()
    zoom_in, pan, pan_call, zoom = a.camera.moves
    assert (zoom_in[1], zoom_in[4]) == (1.0, "spring")
    assert pan[4] == "ease-in-out-soft"
    assert pan[1] == pytest.approx(pan_duration(pan[3][0] - zoom_in[3][0], zoom_in[3][2])) and pan[1] > 1.0
    assert (pan_call[1], pan_call[4]) == (0.5, "linear")
    assert (zoom[1], zoom[4]) == (1.0, "spring")


PAGE = """<body style='margin:0;background:#fff'>
<div style='position:absolute;left:200px;top:100px;width:32px;height:36px;background:#000'></div></body>"""


def test_large_zoom_is_rendered_sharp(tmp_path):
    """The video opens 10x zoomed on a 64 x 36 px area whose left half is black, then zooms out.
    The browser renders the zoom, so the black edge in the 1280 px wide video is sharp (a crop of
    the 2x frames would blur it over about 5 px), and the zoom out ends at the full page."""
    profile = str(tmp_path / "profile")
    cfg = Config(project_dir=str(tmp_path), name="t", url="", width=640, height=360, scale=2)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            profile, headless=True, viewport={"width": 640, "height": 360}, device_scale_factor=2,
            args=["--force-device-scale-factor=2", "--remote-debugging-port=0"])
        pg = ctx.pages[0]
        pg.set_content(PAGE)
        cast = Cast(ctx, "t", 1280, 720, str(tmp_path / "work"), profile)
        a = Actor(ctx, pg, cast, cfg)
        a.zoom((200, 100, 64, 36), pad=0)  # in setup: the video opens zoomed in
        assert a.camera.rendering()
        cast.attach(pg)
        pg.wait_for_timeout(500)
        cast.start()
        a.hold(1.0)
        a.zoom_out(dur=1.0)
        a.hold(1.0)
        cast.stop()
        ctx.close()
    assert not a.camera.rendering() and a.camera.render == [[0.0, 0.0, pytest.approx(2.0, abs=0.1)]]
    dst = str(tmp_path / "v.mp4")
    cast.encode(dst, FF, fps=30, crf=12, log_dir=str(tmp_path), camera=a.camera)
    row = subprocess.run([FF, "-v", "error", "-ss", "0.5", "-i", dst, "-frames:v", "1", "-vf", "crop=1280:2:0:360",
                          "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout[:1280]
    assert max(row[:600]) < 40 and min(row[680:]) > 215  # black left half, white right half
    assert sum(1 for v in row if 40 <= v <= 215) <= 4  # a sharp edge
    assert mean(dst, 2.8) > 245  # zoomed out: the white page with one small black box ...
    box = subprocess.run([FF, "-v", "error", "-ss", "2.8", "-i", dst, "-frames:v", "1", "-vf",
                          "crop=60:68:402:202,scale=1:1", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         capture_output=True, check=True).stdout
    assert box[0] < 30  # ... where the page has it


def test_switch_to_render_keeps_its_last_frame(tmp_path):
    """Frames while the browser takes over the zoom can show either state. The last one shows the
    rendered view, it starts when the encoder stops cropping, so no frame is shown uncropped."""
    raw, mid, rendered, moving = (solid(tmp_path / ("%s.jpg" % n), "320x180") for n in ("r", "m", "z", "v"))
    cast = Cast(None, "t", 320, 180, str(tmp_path / "work"))
    cast.t0, cast.end, cast.offset = 0.0, 3.0, 0.0
    cam = Camera(160, 90)
    cam.render_on(1.0, SWITCH_HOLD)
    frames = [(0.0, raw), (1.01, mid), (1.03, rendered), (1.2, moving)]
    assert cast._usable_frames(frames, cam) == [(0.0, raw), (1.0 + SWITCH_HOLD, rendered), (1.2, moving)]
