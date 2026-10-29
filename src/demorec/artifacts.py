"""Files a run writes next to the video for review: chapters, keyframes, contact sheet, failure
state. The full list of the out folder is in runner.py."""
import os, shutil, subprocess

from .browser import save_aria_tree
from .util import NO_WINDOW, ffmpeg_path, slug

FAILURE_FILES = ("failure.png", "failure.aria.yml")


def _chapter_ends(chapters, total):
    """A chapter ends where the next one starts, the last one at the end of the video."""
    return [c["start"] for c in chapters[1:]] + [total]


def write_vtt(path, chapters, total):
    def ts(t):
        return "%02d:%02d:%06.3f" % (t // 3600, t % 3600 // 60, t % 60)
    with open(path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for i, (c, end) in enumerate(zip(chapters, _chapter_ends(chapters, total))):
            start = 0 if i == 0 else c["start"]  # the opening hold belongs to the first chapter
            f.write("%d\n%s --> %s\n%s\n\n" % (i + 1, ts(start), ts(end), c["title"]))


def write_keyframes(cast, chapters, total, out):
    """The frame just before each chapter's end, as keyframes/NN-<chapter>.jpg. Sets
    chapter["keyframe"] for the chapters that got one."""
    kd = os.path.join(out, "keyframes")
    shutil.rmtree(kd, ignore_errors=True)
    os.makedirs(kd)
    for i, (c, end) in enumerate(zip(chapters, _chapter_ends(chapters, total))):
        src = cast.frame_at(max(c["start"], end - 0.3))
        if src:
            name = "%02d-%s.jpg" % (i + 1, slug(c["title"]))
            shutil.copy(src, os.path.join(kd, name))
            c["keyframe"] = "keyframes/" + name


def write_contact(video, out, total):
    """contact.jpg: a 4x4 grid of frames spread over the video. Returns its description."""
    every = max(2, round(total / 16))
    with open(os.path.join(out, "contact.log"), "wb") as e:
        subprocess.run([ffmpeg_path(), "-y", "-i", video, "-vf",
                        "fps=1/%d,scale=480:-2,tile=4x4:padding=4:color=white" % every,
                        "-frames:v", "1", "-q:v", "3", os.path.join(out, "contact.jpg")],
                       stdout=e, stderr=e, creationflags=NO_WINDOW)
    return "contact.jpg (one frame every %d s, left to right, top to bottom)" % every


def clear_failure(out):
    """Remove the failure files of an earlier run, so they never describe this one."""
    for name in FAILURE_FILES:
        if os.path.exists(os.path.join(out, name)):
            os.remove(os.path.join(out, name))


def save_failure(pg, out):
    """Screenshot and accessibility tree at the failure point. Returns the result.json entries
    of the files that could be written."""
    png, aria = FAILURE_FILES
    saved = {}
    try:
        pg.screenshot(path=os.path.join(out, png))
        saved["failure_screenshot"] = png
    except Exception: pass
    try:
        save_aria_tree(pg, os.path.join(out, aria))
        saved["failure_aria"] = aria
    except Exception: pass
    return saved
