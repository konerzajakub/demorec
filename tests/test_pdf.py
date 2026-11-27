"""A downloaded PDF shown over the app in the same tab, with transitions to it and back."""
import base64, json, shutil, subprocess

import pytest
from playwright.sync_api import sync_playwright

from demorec import config, runner

FF = shutil.which("ffmpeg")

SITE = """<!doctype html><body style='margin:0;font:24px sans-serif;background:#fff'>
<h1 style='margin:40px'>Quote Q-0001</h1>
<a id=dl style='position:absolute;left:40px;top:140px'>Download PDF</a>
<script>
  const bytes = Uint8Array.from(atob('%s'), c => c.charCodeAt(0));
  dl.href = URL.createObjectURL(new Blob([bytes], {type: 'application/pdf'}));
  dl.download = 'quote.pdf';
</script></body>"""

SCENE = '''
def scene(a):
    a.chapter("Quote")
    a.zoom(a.pg.get_by_text("Download PDF"), scale=1.4)
    a.hold(0.8)
    pdf = a.download(a.pg.get_by_text("Download PDF"), "quote.pdf", transition="pdf")
    a.chapter("Quote PDF")
    a.pdf_show(pdf, wait=1.5)
    a.transition_in("pdf")
    a.pdf_scroll(300)
    a.hold(0.6)
    a.transition_out("back", back=True)
    a.chapter("Back")
    a.pdf_hide()
    a.transition_in("back")
    a.hold(0.5)
'''


def pdf_viewer():
    """True if Playwright's full Chromium (channel "chromium") runs and has a PDF viewer."""
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chromium")
            ok = b.new_page().evaluate("navigator.pdfViewerEnabled")
            b.close()
            return ok
    except Exception:
        return False


def make_pdf():
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.set_content("<h1 style='font:60px sans-serif'>Quote Q-0001</h1>" + "<p>Line of the quote</p>" * 60)
        pdf = pg.pdf()
        b.close()
    return pdf


def top_strip(image):
    """Mean grey of the top 40 px of an image."""
    r = subprocess.run([FF, "-v", "error", "-i", str(image), "-vf", "crop=iw:40:0:0,scale=1:1", "-f", "rawvideo",
                        "-pix_fmt", "gray", "-"], capture_output=True, check=True)
    return r.stdout[0]


def test_headless_shell_says_it_has_no_viewer(tmp_path):
    from demorec.actor import Actor
    from demorec.config import Config
    with sync_playwright() as p:
        b = p.chromium.launch()
        a = Actor(None, b.new_page(), None, Config(project_dir=str(tmp_path), name="t", url=""))
        with pytest.raises(RuntimeError, match="channel"):
            a.pdf_show(str(tmp_path / "x.pdf"))
        b.close()


@pytest.mark.skipif(not pdf_viewer(), reason='needs Playwright Chromium with its PDF viewer (channel "chromium")')
def test_record_pdf_in_the_same_tab(tmp_path):
    proj = tmp_path / "proj"
    (proj / "demos" / "quote").mkdir(parents=True)
    (proj / "site.html").write_text(SITE % base64.b64encode(make_pdf()).decode(), encoding="utf-8")
    (proj / "project.toml").write_text('[app]\nurl = "./site.html"\n[browser]\nwidth = 640\nheight = 360\n'
                                       'channel = "chromium"\n', encoding="utf-8")
    (proj / "demos" / "quote" / "scene.py").write_text(SCENE, encoding="utf-8")
    cfg = config.load(str(proj), out_root=str(tmp_path / "out"))
    result, out = runner.run_demo(cfg, "quote")
    assert result["status"] == "ok", result
    assert [t["name"] for t in result["transitions"]] == ["pdf", "back"] and result["transitions"][1]["back"]
    app, pdf, back = (out + "/" + c["keyframe"] for c in result["chapters"])
    assert top_strip(app) > 200  # the white app
    assert top_strip(pdf) < 100  # the viewer's dark toolbar: the keyframe of the PDF chapter shows the PDF
    assert top_strip(back) > 200  # back in the app
    video = out + "/quote.mp4"
    probe = json.loads(subprocess.run([shutil.which("ffprobe"), "-v", "error", "-show_entries", "format=duration",
                                       "-of", "json", video], capture_output=True, text=True, check=True).stdout)
    assert abs(float(probe["format"]["duration"]) - result["duration_s"]) < 0.2
    shot = tmp_path / "mid.png"  # in the video, the PDF right after its slide, at the full frame
    subprocess.run([FF, "-v", "error", "-y", "-ss", str(result["transitions"][0]["at"] + 1.5), "-i", video,
                    "-frames:v", "1", str(shot)], check=True)
    assert top_strip(shot) < 100


FILE_SCENE = '''
import os

def scene(a):
    a.chapter("File")
    a.zoom((200, 100, 240, 135), scale=1.4)  # a zoom the encoder crops
    a.hold(0.5)
    a.show_file(os.path.join(os.path.dirname(__file__), "file.html"), hold=2.0)
'''


def test_show_file_is_never_cropped(tmp_path):
    """The camera used to crop the file's window as well, cutting off its top: now it zooms out first."""
    proj = tmp_path / "proj"
    demo = proj / "demos" / "file"
    demo.mkdir(parents=True)
    (proj / "site.html").write_text("<body style='background:#fff'>app</body>", encoding="utf-8")
    (proj / "project.toml").write_text('[app]\nurl = "./site.html"\n[browser]\nwidth = 640\nheight = 360\n', encoding="utf-8")
    (demo / "scene.py").write_text(FILE_SCENE, encoding="utf-8")
    (demo / "file.html").write_text("<body style='margin:0'><div style='height:30px;background:#000'></div>"
                                    "<script>setInterval(() => document.title = Date.now(), 50)</script></body>", encoding="utf-8")
    cfg = config.load(str(proj), out_root=str(tmp_path / "out"))
    result, out = runner.run_demo(cfg, "file")
    assert result["status"] == "ok", result
    shot = tmp_path / "file.png"
    subprocess.run([FF, "-v", "error", "-y", "-ss", str(result["duration_s"] - 4.0), "-i", out + "/file.mp4",
                    "-frames:v", "1", str(shot)], check=True)
    assert top_strip(shot) < 60  # the black bar at the top of the file's window is in the picture
