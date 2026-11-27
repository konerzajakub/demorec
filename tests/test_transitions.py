"""Scene transitions: the marks, the cut, the slide in the encoded video and the chapter times."""
import json, re, shutil, subprocess

import pytest

from demorec.actor import Actor
from demorec.artifacts import write_vtt
from demorec.cast import Cast
from demorec.config import Config
from demorec.motion import ease
from demorec.transitions import _tree, check, cut_total, fractions, graph, remap, shown

FF = shutil.which("ffmpeg")
TRS = [{"name": "a", "out": 2.0, "in": 5.0, "back": False}, {"name": "b", "out": 8.0, "in": 9.0, "back": True}]


def test_remap_takes_the_cuts_out():
    assert remap(1.0, TRS) == 1.0
    assert remap(2.0, TRS) == 2.0
    assert remap(3.5, TRS) == 2.0  # inside a cut: the start of its slide
    assert remap(6.0, TRS) == 3.0
    assert remap(8.5, TRS) == 5.0
    assert remap(10.0, TRS) == 6.0
    assert cut_total(TRS) == 4.0
    assert shown(3.5, TRS) == 2.0 and shown(6.0, TRS) == 6.0  # keyframes: the last frame shown before


def test_slides_must_not_overlap():
    check(TRS, 1.3)
    with pytest.raises(ValueError, match="'b'"):
        check(TRS, 3.5)  # a's slide runs 5.0 to 8.5, b starts at 8.0


def test_slide_expression_follows_the_easing():
    values = fractions(1.0, 60, "cubic")
    assert len(values) == 60 and values[0] == 0 and values[30] == pytest.approx(0.5, abs=1e-4)
    expr = _tree(values, "n")
    for n in range(60):
        py = expr.replace("if(", "iff(").replace("lt(n,", "lt(N,")
        got = eval(py, {"iff": lambda c, a, b: a if c else b, "lt": lambda a, b: a < b, "N": n})
        assert got == pytest.approx(ease("cubic", n / 60), abs=1e-4)


def test_graph_keeps_slides_and_the_rest():
    f, length = graph(TRS, 12.0, 60, 320, 180, duration=1.0)
    assert length == pytest.approx(8.0)
    assert f.count("overlay=") == 4 and "concat=n=5" in f  # keep, slide, keep, slide, keep
    assert "x='1*W*(1-(" in f and "x='-1*W*(1-(" in f  # forward from the right, back from the left


def test_marks_on_the_actor(tmp_path):
    a = Actor(None, None, None, Config(project_dir=str(tmp_path), name="t", url=""))
    now = [1.0]
    a.cast = type("C", (), {"elapsed": lambda self: now[0]})()
    a.transition_out("open")
    now[0] = 2.5
    a.transition_in("open", hold=False)
    with pytest.raises(ValueError, match="during the slide"):
        a.transition_out("close")  # the new scene must stand still while it slides in
    now[0] = 6.0
    with pytest.raises(ValueError, match="twice"):
        a.transition_out("open")
    a.transition_out("close", back=True)
    with pytest.raises(ValueError, match="before transition_in"):
        a.transition_out("other")
    with pytest.raises(ValueError, match="no transition_in"):
        a.transitions_end()
    a.transition_in("close", hold=False)
    a.transitions_end()
    assert a.transitions == [{"name": "open", "out": 1.0, "in": 2.5, "back": False},
                             {"name": "close", "out": 6.0, "in": 6.0, "back": True}]
    with pytest.raises(ValueError, match="without transition_out"):
        a.transition_in("close")


def solid(path, color):
    subprocess.run([FF, "-v", "error", "-y", "-f", "lavfi", "-i", "color=%s:s=320x180" % color,
                    "-frames:v", "1", str(path)], check=True)
    return str(path)


def column_means(video, t):
    """Mean grey of the left and the right half of the frame at t."""
    r = subprocess.run([FF, "-v", "error", "-ss", str(t), "-i", video, "-frames:v", "1", "-vf", "scale=2:1",
                        "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True)
    return r.stdout[0], r.stdout[1]


def test_encoded_video_cuts_and_slides(tmp_path):
    """White until 2 s, a grey load from 2 to 4 s that the video cuts, then black. The black scene
    slides in from the right over 1 s, the video is 2 s shorter and runs at 60 fps."""
    white, grey, black = solid(tmp_path / "w.jpg", "white"), solid(tmp_path / "g.jpg", "gray"), solid(tmp_path / "b.jpg", "black")
    cast = Cast(None, "t", 320, 180, str(tmp_path / "work"))
    cast.frames = [(0.0, white), (2.0, grey), (4.0, black)]
    cast.t0, cast.end, cast.offset = 0.0, 8.0, 0.0
    trs = [{"name": "load", "out": 2.0, "in": 4.0, "back": False}]
    dst = str(tmp_path / "v.mp4")
    length = cast.encode(dst, FF, fps=60, log_dir=str(tmp_path), transitions=trs, slide=(1.0, "cubic"))
    assert length == pytest.approx(6.0)
    probe = json.loads(subprocess.run([shutil.which("ffprobe"), "-v", "error", "-show_entries",
                                       "stream=r_frame_rate:format=duration", "-of", "json", dst],
                                      capture_output=True, text=True, check=True).stdout)
    assert abs(float(probe["format"]["duration"]) - 6.0) < 0.1 and probe["streams"][0]["r_frame_rate"] == "60/1"
    assert min(column_means(dst, 1.0)) > 240  # the old scene
    left, right = column_means(dst, 2.5)  # mid slide: white leaves to the left, black comes from the right
    assert left > 200 and right < 50
    assert max(column_means(dst, 3.5)) < 15  # the new scene, no grey frame of the load anywhere
    for t in [2.0 + k / 10 for k in range(10)]:  # only the two scenes during the slide, no grey
        row = subprocess.run([FF, "-v", "error", "-ss", str(t), "-i", dst, "-frames:v", "1", "-vf", "crop=320:2:0:90",
                              "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout[:320]
        assert sum(1 for v in row if 60 < v < 200) <= 4


def test_back_slides_the_other_way(tmp_path):
    white, black = solid(tmp_path / "w.jpg", "white"), solid(tmp_path / "b.jpg", "black")
    cast = Cast(None, "t", 320, 180, str(tmp_path / "work"))
    cast.frames = [(0.0, white), (2.5, black)]
    cast.t0, cast.end, cast.offset = 0.0, 5.0, 0.0
    dst = str(tmp_path / "v.mp4")
    cast.encode(dst, FF, fps=60, log_dir=str(tmp_path), transitions=[{"name": "x", "out": 2.0, "in": 2.5, "back": True}],
                slide=(1.0, "cubic"))
    left, right = column_means(dst, 2.5)
    assert left < 50 and right > 200  # the new scene comes from the left


def test_chapters_after_the_cut(tmp_path):
    chapters = [{"title": "One", "start": 0.5}, {"title": "Two", "start": 3.0}, {"title": "Three", "start": 6.0}]
    for c in chapters:
        c["start"] = remap(c["start"], TRS)
    write_vtt(str(tmp_path / "c.vtt"), chapters, 12.0 - cut_total(TRS))
    vtt = (tmp_path / "c.vtt").read_text(encoding="utf-8")
    assert re.findall(r"(\S+) --> (\S+)", vtt) == [("00:00:00.000", "00:00:02.000"), ("00:00:02.000", "00:00:03.000"),
                                                   ("00:00:03.000", "00:00:08.000")]


def test_transition_settings_in_project_toml(tmp_path):
    from demorec import config
    toml = tmp_path / "project.toml"
    toml.write_text('[app]\nurl = "http://x/"\n', encoding="utf-8")
    cfg = config.load(tmp_path)
    assert (cfg.transition_easing, cfg.transition_duration, cfg.transition_fps) == ("cubic", 1.3, 60)
    toml.write_text('[app]\nurl = "http://x/"\n[recording]\ntransition_fps = 50\n[motion]\ntransition_easing = "quint"\n'
                    'transition_duration = 0.8\n', encoding="utf-8")
    cfg = config.load(tmp_path)
    assert (cfg.transition_easing, cfg.transition_duration, cfg.transition_fps) == ("quint", 0.8, 50)
    for bad in ('transition_easing = "wobbly"', "transition_duration = 0"):
        toml.write_text('[app]\nurl = "http://x/"\n[motion]\n%s\n' % bad, encoding="utf-8")
        with pytest.raises(SystemExit, match=bad.split()[0]):
            config.load(tmp_path)


SITE = """<!doctype html><body style='margin:0;font:24px sans-serif;background:#fff'>
<a id=go href='#two' style='position:absolute;left:80px;top:80px'>Open the report</a>
<script>onhashchange = () => setTimeout(() => { document.body.style.background = '#000'; go.remove(); }, 700)</script></body>"""

SCENE = '''
def scene(a):
    a.chapter("List")
    a.hold(1.0)
    a.click(a.pg.get_by_text("Open the report"), after=400)
    a.transition_out("report")
    a.chapter("Report")
    a.wait(1500)  # a slow page load, cut from the video
    a.transition_in("report")
    a.hold(1.0)
'''


def test_record_with_a_transition(tmp_path):
    """End to end: the load between the marks is cut, the chapter starts with the slide."""
    from demorec import config, runner
    proj = tmp_path / "proj"
    (proj / "demos" / "slide").mkdir(parents=True)
    (proj / "site.html").write_text(SITE, encoding="utf-8")
    (proj / "project.toml").write_text('[app]\nurl = "./site.html"\n[browser]\nwidth = 640\nheight = 360\n', encoding="utf-8")
    (proj / "demos" / "slide" / "scene.py").write_text(SCENE, encoding="utf-8")
    cfg = config.load(str(proj), out_root=str(tmp_path / "out"))
    result, out = runner.run_demo(cfg, "slide")
    assert result["status"] == "ok", result
    (tr,) = result["transitions"]
    assert tr["name"] == "report" and 1.4 < tr["cut_s"] < 2.0
    report = result["chapters"][1]
    assert report["start"] == pytest.approx(tr["at"], abs=0.05)  # started inside the cut: starts with the slide
    video = out + "/slide.mp4"
    probe = json.loads(subprocess.run([shutil.which("ffprobe"), "-v", "error", "-show_entries",
                                       "stream=r_frame_rate:format=duration", "-of", "json", video],
                                      capture_output=True, text=True, check=True).stdout)
    assert abs(float(probe["format"]["duration"]) - result["duration_s"]) < 0.2
    assert probe["streams"][0]["r_frame_rate"] == "60/1"
    t = tr["at"]
    assert min(column_means(video, t - 0.2)) > 200  # the white list up to the slide
    left, right = column_means(video, t + 0.65)  # half way: white leaves left, black comes from the right
    assert left > 150 and right < 60
    assert max(column_means(video, t + 1.6)) < 30
