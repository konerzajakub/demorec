"""Runs a demo: reset data, open the browser, log in, play the scene, encode, write artifacts.

Artifacts of `demos/<id>` go to `<project>/out/<id>/`:
  <output>.mp4      the video (record mode only)
  result.json       status, duration, chapters, key moments without a chapter, error, artifact paths
  chapters.vtt      WebVTT chapter list
  keyframes/        one frame at the end of each chapter, named NN-<chapter>.jpg
  contact.jpg       grid of frames every few seconds
  check/            check mode only: a screenshot at the end of each chapter
  failure.png       screenshot at the failure point
  failure.aria.yml  accessibility tree at the failure point, for fixing selectors
  run.log           everything the run printed
"""
import dataclasses, importlib.util, json, os, shutil, subprocess, sys, time

from playwright.sync_api import sync_playwright

from .actor import Actor
from .artifacts import clear_failure, save_failure, write_contact, write_keyframes, write_vtt
from .brief import key_moments
from .browser import new_profile, open_context, save_aria_tree, sign_in
from .cast import Cast
from .util import ffmpeg_path, log, log_exc, slug

CHECK_SPEED = 0.05  # check mode and inspect play every pause and move at this fraction


# ------------------------------------------------------------ loading
def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_helpers(cfg):
    if cfg.project_dir not in sys.path:
        sys.path.insert(0, cfg.project_dir)  # scenes can `from helpers import *`
    p = os.path.join(cfg.project_dir, "helpers.py")
    return load_module(p, "helpers") if os.path.exists(p) else None


def demo_dir(cfg, demo):
    d = os.path.join(cfg.project_dir, "demos", demo)
    if not os.path.isdir(d):
        raise SystemExit("no demo folder %s (create one with: demorec new-demo)" % d)
    return d


def load_scene(ddir, module_name):
    return load_module(os.path.join(ddir, "scene.py"), module_name)


# ------------------------------------------------------------ record / check
def run_before(cfg, log_dir):
    """The project's [recording] before command, which resets the demo data."""
    if not cfg.before:
        return
    log("before:", cfg.before)
    with open(os.path.join(log_dir, "before.out.log"), "wb") as o, open(os.path.join(log_dir, "before.err.log"), "wb") as e:
        r = subprocess.run(cfg.before, shell=True, cwd=cfg.project_dir, stdout=o, stderr=e)
    if r.returncode != 0:
        raise RuntimeError("before command failed (exit %d), see before.*.log" % r.returncode)


def play(a, scene, cfg, helpers, check, out):
    """Login and setup off the record, then the scene between an opening and a closing hold."""
    if getattr(scene, "LOGIN", True):
        sign_in(a, cfg, helpers)  # LOGIN = False: the scene shows the login itself
    if hasattr(scene, "setup"):
        scene.setup(a)  # not filmed: navigation, data the scene needs
    if check:
        a.speed = CHECK_SPEED
        a.shot_dir = os.path.join(out, "check")
        shutil.rmtree(a.shot_dir, ignore_errors=True)
        os.makedirs(a.shot_dir)
    else:
        a.cast.attach(a.pg)
    a.park(); a.wait(300)
    a.cast.start()
    a.hold(1.5)
    scene.scene(a)
    a.hold(2.5)
    a.chapter_end()


def short_error(ex):
    """`Type: message` from the first lines. Playwright errors go on with a long call log."""
    lines = [l.strip() for l in str(ex).splitlines()[:3] if l.strip()]
    return "%s: %s" % (type(ex).__name__, " | ".join(lines))


def add_video(result, cast, chapters, total, out, output, cfg):
    """Encode the frames and write everything that is cut from the video."""
    dst = os.path.join(out, output)
    cast.encode(dst, ffmpeg_path(), cfg.fps, cfg.crf, log_dir=out)
    result["video"] = output
    result["duration_s"] = total
    write_vtt(os.path.join(out, "chapters.vtt"), chapters, total)
    result["chapters_vtt"] = "chapters.vtt"
    write_keyframes(cast, chapters, total, out)
    result["contact_sheet"] = write_contact(dst, out, total)


def run_demo(cfg, demo, check=False, keep_frames=False):
    """check=True plays the scene fast without capture. Use it to fix selectors before recording."""
    ddir = demo_dir(cfg, demo)
    helpers = load_helpers(cfg)
    scene = load_scene(ddir, "scene_" + slug(demo).replace("-", "_"))
    if not hasattr(scene, "scene"):
        raise SystemExit("%s/scene.py must define scene(a)" % ddir)
    out = os.path.join(cfg.out_dir, demo)
    os.makedirs(out, exist_ok=True)
    os.makedirs(cfg.work_dir, exist_ok=True)
    clear_failure(out)
    output = getattr(scene, "OUTPUT", demo + ".mp4")
    if hasattr(scene, "SIZE"):  # per-demo viewport, e.g. a wide overview screen
        cfg = dataclasses.replace(cfg, width=scene.SIZE[0], height=scene.SIZE[1])
    moments = key_moments(os.path.join(ddir, "brief.md"))
    result = {"project": cfg.name, "demo": demo, "mode": "check" if check else "record",
              "status": "failed", "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
    profile = new_profile(cfg)
    cast = None
    t_run = time.time()
    try:
        run_before(cfg, out)
        with sync_playwright() as p:
            ctx, pg = open_context(p, cfg, profile)
            cast = Cast(ctx, slug(demo), cfg.width * cfg.scale, cfg.height * cfg.scale, cfg.work_dir, profile)
            a = Actor(ctx, pg, cast, cfg)
            try:
                play(a, scene, cfg, helpers, check, out)
                result["status"] = "ok"
            except Exception as ex:
                log_exc()
                result["error"] = short_error(ex)
                result["error_at_chapter"] = a.chapters[-1]["title"] if a.chapters else None
                result.update(save_failure(a.pg, out))
            finally:
                cast.stop()
                try: ctx.close()
                except Exception: pass
        total = round(cast.end - cast.t0, 2) if cast.t0 else 0
        titles = [c["title"] for c in a.chapters]
        result["chapters"] = a.chapters
        result["missing_moments"] = [m for m in moments if m not in titles]
        result["unplanned_chapters"] = [t for t in titles if moments and t not in moments]
        if not check and result["status"] == "ok":
            add_video(result, cast, a.chapters, total, out, output, cfg)
        elif check:
            result["estimated_duration_s"] = round(total + a.saved, 1)
            result["note"] = ("check mode: nothing was captured, chapter starts are not real. "
                              "chapters[].screenshot shows each chapter's end state. "
                              "estimated_duration_s is the expected video length")
    except Exception as ex:
        log_exc()
        result["error"] = result.get("error") or "%s: %s" % (type(ex).__name__, ex)
        result["status"] = "failed"
    finally:
        if cast and not keep_frames: cast.cleanup()
        shutil.rmtree(profile, ignore_errors=True)
    result["run_s"] = round(time.time() - t_run, 1)
    with open(os.path.join(out, "result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result, out


# ------------------------------------------------------------ inspect
def page_url(cfg, path):
    """path as given if it is a URL, else relative to [app] url."""
    return path if "://" in path else cfg.url.rstrip("/") + "/" + path.lstrip("/")


def inspect(cfg, path="", demo=None, name="inspect"):
    """Log in, open a page (or play a demo's setup), save screenshot and accessibility tree.
    The tree shows the roles and names that get_by_role() and get_by_label() match."""
    helpers = load_helpers(cfg)
    out = os.path.join(cfg.out_dir, "_inspect")
    os.makedirs(out, exist_ok=True); os.makedirs(cfg.work_dir, exist_ok=True)
    profile = new_profile(cfg)
    try:
        with sync_playwright() as p:
            ctx, pg = open_context(p, cfg, profile)
            a = Actor(ctx, pg, Cast(ctx, "inspect", cfg.width, cfg.height, cfg.work_dir), cfg)
            a.speed = CHECK_SPEED
            sign_in(a, cfg, helpers)
            if demo:
                scene = load_scene(demo_dir(cfg, demo), "scene_inspect")
                if hasattr(scene, "setup"): scene.setup(a)
            if path:
                a.pg.goto(page_url(cfg, path))
                a.settle(800)
            png, yml = os.path.join(out, name + ".png"), os.path.join(out, name + ".aria.yml")
            a.pg.screenshot(path=png)
            save_aria_tree(a.pg, yml)
            a.cast.cleanup()
            ctx.close()
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    return png, yml
