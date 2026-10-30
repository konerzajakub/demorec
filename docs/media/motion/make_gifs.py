"""Rebuild the motion GIFs in this folder from scratch demos of projects/example.

    .venv/bin/python docs/media/motion/make_gifs.py            # record and build
    .venv/bin/python docs/media/motion/make_gifs.py --no-record  # build from the last recordings

Each GIF shows one kind of motion with several easings side by side, the default first.
The scratch demos (projects/example/demos/_motion-*) are recorded at full resolution
(2560x1440), cut from their first chapter, scaled down with lanczos, labelled like the tiles of
bench/compare.py, stacked in a grid and turned into a 30 fps GIF with its own palette. The scratch demos and their out folders are deleted afterwards, --keep
leaves them for another --no-record run.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PROJECT = os.path.join(ROOT, "projects", "example")
DST = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(ROOT, ".venv", "Scripts" if sys.platform == "win32" else "bin")
FPS = 30
TW, TH, COLS = 640, 360, 2   # tile size, tiles per row: 1280 px wide
TAIL = 2.5  # s the recorder holds after the scene

ZOOMS = ["spring", "spring-soft", "snappy", "bouncy", "ease-in-out", "linear"]
CURSORS = ["human", "ease-in-out", "cubic", "smoothstep", "spring", "linear"]

HEAD = '"""Scratch demo for docs/media/motion/make_gifs.py."""\nfrom helpers import *\n\nOUTPUT = "{demo}.mp4"\nE = "{easing}"\n'
SCENES = {
    # Zoom in on a table cell and back out.
    "zoom": """
def setup(a):
    a.mx, a.my = 1000, 600


def scene(a):
    a.chapter("Zoom")
    a.hold(0.6)
    a.zoom(task_table(a).get_by_role("cell", name="Operator Two"), scale=3, easing=E)
    a.hold(0.9)
    a.zoom_out(easing=E)
    a.hold(0.9)
""",
    # Zoomed in 2.5x, the camera pans along the table header and back.
    "pan": """
def setup(a):
    a.mx, a.my = 640, 700
    a.zoom((320, 190, 20, 20), scale=2.5)


def scene(a):
    a.chapter("Pan")
    a.hold(0.6)
    a.zoom((940, 190, 20, 20), scale=2.5, easing=E)
    a.hold(0.9)
    a.zoom((320, 190, 20, 20), scale=2.5, easing=E)
    a.hold(0.9)
""",
    # The cursor, drawn twice its size so it can be seen in a small tile, moves between three points.
    "cursor": """
def setup(a):
    a.pg.add_style_tag(content="#__rec_cursor{width:48px!important;height:64px!important;margin:-2px 0 0 -3px}"
                               "#__rec_cursor svg{width:48px;height:64px}")
    a.move(200, 520, dur=0.3)


def scene(a):
    a.chapter("Cursor")
    a.hold(0.6)
    a.move(1080, 520, dur=1.0, easing=E)
    a.hold(0.5)
    a.move(640, 280, dur=1.0, easing=E)
    a.hold(0.5)
    a.move(200, 520, dur=1.0, easing=E)
    a.hold(0.8)
""",
    # The video opens on the app title about 10x and zooms out to the whole app.
    "opening": """
def setup(a):
    a.zoom(a.pg.get_by_role("heading", name="Tasks"))
    a.mx, a.my = 700, 500


def scene(a):
    a.chapter("Opening")
    a.hold(1.5)
    a.zoom_out(dur=2.5)
    a.hold(1.5)
""",
}
# name: scene, easings, the default easing for this kind of motion
GIFS = {"zoom-easing": ("zoom", ZOOMS, "spring"), "pan-easing": ("pan", ZOOMS, "spring"),
        "cursor-easing": ("cursor", CURSORS, "human")}


def demo_id(kind, easing):
    return "_motion-%s-%s" % (kind, easing)


def takes():
    yield demo_id("opening", "spring"), "opening", "spring"
    for kind, easings, _ in GIFS.values():
        for e in easings:
            yield demo_id(kind, e), kind, e


def record(log):
    for demo, kind, easing in takes():
        d = os.path.join(PROJECT, "demos", demo)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "scene.py"), "w", encoding="utf-8") as f:
            f.write(HEAD.format(demo=demo, easing=easing) + SCENES[kind])
        r = subprocess.run([os.path.join(BIN, "demorec"), "record", PROJECT, demo], cwd=ROOT,
                           capture_output=True, text=True)
        log.write(r.stdout + r.stderr)
        out = json.loads(r.stdout[r.stdout.find("{"):]) if "{" in r.stdout else {}
        if r.returncode or out.get("status") != "ok":
            sys.exit("record %s failed: %s" % (demo, out.get("error") or r.stderr[-500:]))
        print("recorded", demo, out.get("duration_s"))


def take(demo):
    """Video path, start of the first chapter and the length of the scene from there (the
    recorder adds TAIL s after the scene)."""
    with open(os.path.join(PROJECT, "out", demo, "result.json"), encoding="utf-8") as f:
        res = json.load(f)
    t0 = res["chapters"][0]["start"]
    return os.path.join(PROJECT, "out", demo, res["video"]), t0, res["duration_s"] - t0 - TAIL


def labels(tmp):
    """Label per tile, styled like the model names in bench/compare.py: Arial Bold at 1/16 of the
    tile height, white on #333a40 at 95 %, flush left at the bottom of the tile."""
    from playwright.sync_api import sync_playwright
    size = TH / 16
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": TW, "height": TH}, device_scale_factor=1)
        for name, (_, easings, default) in GIFS.items():
            for n in easings:
                pg.set_content(
                    "<body style='margin:0;background:transparent'><span id=l style='display:inline-block;"
                    "padding:%.2fpx;background:rgba(51,58,64,.95);color:#fff;font:bold %.2fpx/%.2fpx Arial,"
                    "Helvetica,sans-serif'>%s</span></body>"
                    % (size / 3, size, size, n + (" (default)" if n == default else "")))
                pg.locator("#l").screenshot(path=os.path.join(tmp, "label-%s-%s.png" % (name, n)),
                                            omit_background=True)
        b.close()
    return round(TH - size / 2 + size / 3 - (size + 2 * size / 3))  # y of the label's top


def gif(inputs, graph, dst):
    """Palette from the whole clip (only the changing parts count), no dithering: flat UI colours
    stay flat and the text edges keep the palette's own greys."""
    graph += (";[g]split[a][b];[a]palettegen=max_colors=256:stats_mode=diff[p];"
              "[b][p]paletteuse=dither=none:diff_mode=rectangle")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", graph, "-loop", "0", dst],
                   check=True)
    print(os.path.relpath(dst, ROOT), os.path.getsize(dst) // 1024, "KB")


def grid(name, kind, easings, tmp, label_y):
    clips = [take(demo_id(kind, e)) for e in easings]
    dur = min(c[2] for c in clips)
    inputs, parts = [], []
    for path, t0, _ in clips:
        inputs += ["-ss", "%.3f" % t0, "-t", "%.3f" % dur, "-i", path]
    for e in easings:
        inputs += ["-i", os.path.join(tmp, "label-%s-%s.png" % (name, e))]
    n = len(easings)
    for i in range(n):
        parts.append("[%d:v]fps=%d,scale=%d:%d:flags=lanczos[v%d];[v%d][%d:v]overlay=0:%d[t%d]"
                     % (i, FPS, TW, TH, i, i, n + i, label_y, i))
    layout = "|".join("%d_%d" % (i % COLS * TW, i // COLS * TH) for i in range(n))
    parts.append("%sxstack=inputs=%d:layout=%s:fill=white[g]" % ("".join("[t%d]" % i for i in range(n)), n, layout))
    gif(inputs, ";".join(parts), os.path.join(DST, name + ".gif"))


def opening():
    path, t0, dur = take(demo_id("opening", "spring"))
    gif(["-ss", "%.3f" % t0, "-t", "%.3f" % dur, "-i", path],
        "[0:v]fps=%d,scale=1280:720:flags=lanczos[g]" % FPS, os.path.join(DST, "opening-zoom-out.gif"))


def clean():
    for demo, _, _ in takes():
        for d in (os.path.join(PROJECT, "demos", demo), os.path.join(PROJECT, "out", demo)):
            shutil.rmtree(d, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-record", action="store_true", help="build from the recordings of the last --keep run")
    ap.add_argument("--keep", action="store_true", help="keep the scratch demos and their recordings")
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        if not a.no_record:
            with open(os.path.join(tmp, "record.log"), "w", encoding="utf-8") as log:
                record(log)
        label_y = labels(tmp)
        opening()
        for name, (kind, easings, _) in GIFS.items():
            grid(name, kind, easings, tmp, label_y)
    if not a.keep:
        clean()


if __name__ == "__main__":
    main()
