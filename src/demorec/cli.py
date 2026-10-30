"""Command line. Every command prints one JSON object on stdout and nothing else. The full log of a
run goes to <project>/out/<demo>/run.log. Exit code 0 means success."""
import argparse, json, os, shutil, sys

from . import config, runner, util
from .brief import key_moments

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATE = os.path.join(ROOT, "projects", "_template")
LAST_RUN_KEYS = ("mode", "status", "started", "video", "duration_s", "error")


def emit(obj, code=0):
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    sys.exit(code)


# ------------------------------------------------------------ record, check, inspect
def cmd_run(args, check):
    cfg = config.load(args.project)
    if args.no_before:
        cfg.before = ""
    out = os.path.join(cfg.out_dir, args.demo)
    os.makedirs(out, exist_ok=True)
    with util.log_to(os.path.join(out, "run.log")):
        result, out = runner.run_demo(cfg, args.demo, check=check, keep_frames=args.keep_frames)
    if args.model:
        result["model"] = args.model
        with open(os.path.join(out, "result.json"), "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    result["out_dir"] = out
    result["log"] = "run.log"
    emit(result, 0 if result["status"] == "ok" and not result.get("missing_moments") else 1)


def cmd_record(args):
    cmd_run(args, check=False)


def cmd_check(args):
    cmd_run(args, check=True)


def cmd_inspect(args):
    cfg = config.load(args.project)
    os.makedirs(os.path.join(cfg.out_dir, "_inspect"), exist_ok=True)
    error = None
    with util.log_to(os.path.join(cfg.out_dir, "_inspect", args.name + ".log")) as f:
        try:
            png, yml = runner.inspect(cfg, args.path, args.demo, args.name)
        except Exception as ex:
            util.log_exc()
            error = "%s: %s" % (type(ex).__name__, ex)
    if error:
        emit({"status": "failed", "error": error, "log": f.name,
              "hint": "check [app] url and [login] in project.toml and that the app is running"}, 1)
    emit({"status": "ok", "screenshot": png, "aria_tree": yml})


# ------------------------------------------------------------ templates
def render(src, dst, repl):
    """Copy a template file, replacing each placeholder in repl with its value."""
    with open(src, encoding="utf-8") as f:
        s = f.read()
    for k, v in repl.items():
        s = s.replace(k, v)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(s)


def copy_template(src, dst, repl):
    """The project template without its demos, new-demo copies those one at a time."""
    for base, _, files in os.walk(src):
        rel = os.path.relpath(base, src)
        if rel.startswith("demos") or "__pycache__" in rel:
            continue
        os.makedirs(os.path.join(dst, rel), exist_ok=True)
        for fn in files:
            if not fn.endswith(".pyc"):
                render(os.path.join(base, fn), os.path.join(dst, rel, fn), repl)


def cmd_new_project(args):
    dst = os.path.abspath(args.dir or os.path.join(ROOT, "projects", args.name))
    if os.path.exists(dst):
        emit({"status": "failed", "error": "already exists: " + dst}, 1)
    copy_template(TEMPLATE, dst, {"{{project}}": args.name})
    os.makedirs(os.path.join(dst, "demos"), exist_ok=True)
    emit({"status": "ok", "project": dst, "next": ["fill app.md", "set [app] url and ready in project.toml, delete [login] if the app has no login",
                                                   "demorec inspect " + dst]})


def cmd_new_demo(args):
    cfg = config.load(args.project)
    dst = os.path.join(cfg.project_dir, "demos", args.demo)
    if os.path.exists(dst):
        emit({"status": "failed", "error": "already exists: " + dst}, 1)
    os.makedirs(dst)
    src = os.path.join(TEMPLATE, "demos", "_demo")
    for fn in os.listdir(src):
        if os.path.isfile(os.path.join(src, fn)) and not fn.endswith(".pyc"):  # not __pycache__
            render(os.path.join(src, fn), os.path.join(dst, fn), {"{{demo}}": args.demo})
    emit({"status": "ok", "demo": dst, "next": ["fill brief.md with the person", "write scene.py",
                                                "demorec check %s %s" % (args.project, args.demo)]})


# ------------------------------------------------------------ list, doctor
def last_run(cfg, demo):
    """The main fields of the demo's result.json, None if it never ran."""
    path = os.path.join(cfg.out_dir, demo, "result.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        last = json.load(f)
    return last and {k: last.get(k) for k in LAST_RUN_KEYS}


def cmd_list(args):
    cfg = config.load(args.project)
    dd = os.path.join(cfg.project_dir, "demos")
    demos = []
    for d in sorted(os.listdir(dd)) if os.path.isdir(dd) else []:
        if d.startswith("_") or not os.path.isdir(os.path.join(dd, d)):
            continue  # scratch demos and stray files
        demos.append({"demo": d, "key_moments": key_moments(os.path.join(dd, d, "brief.md")),
                      "last_run": last_run(cfg, d)})
    emit({"project": cfg.name, "demos": demos})


def chromium_version():
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            version = b.version
            b.close()
            return version
    except Exception:
        return None


def cmd_doctor(args):
    import importlib.metadata as md
    checks = {"python": sys.version.split()[0], "ffmpeg": shutil.which("ffmpeg"), "ffprobe": shutil.which("ffprobe")}
    try: checks["playwright"] = md.version("playwright")
    except Exception: checks["playwright"] = None
    checks["chromium"] = chromium_version()
    ok = all(checks.values()) and sys.version_info >= (3, 11)
    if not ok:
        checks["fix"] = "Python 3.11+, `pip install -e .`, `playwright install chromium`, ffmpeg on PATH"
    emit({"status": "ok" if ok else "failed", **checks}, 0 if ok else 1)


# ------------------------------------------------------------ arguments
COMMANDS = {"record": cmd_record, "check": cmd_check, "inspect": cmd_inspect, "new-project": cmd_new_project,
            "new-demo": cmd_new_demo, "list": cmd_list, "doctor": cmd_doctor}


def build_parser():
    ap = argparse.ArgumentParser(prog="demorec", description=__doc__)
    sp = ap.add_subparsers(dest="cmd", required=True)
    for name, h in (("record", "record a demo to MP4"), ("check", "play a demo fast without capture")):
        p = sp.add_parser(name, help=h)
        p.add_argument("project"); p.add_argument("demo")
        p.add_argument("--keep-frames", action="store_true", help="keep raw frames in out/.work")
        p.add_argument("--no-before", action="store_true", help="skip the [recording] before command")
        p.add_argument("--model", default=os.environ.get("DEMOREC_MODEL", ""),
                       help="model that wrote the scene, stored in result.json (env DEMOREC_MODEL)")
    p = sp.add_parser("inspect", help="screenshot and accessibility tree of a page, after login")
    p.add_argument("project")
    p.add_argument("--path", default="", help="URL or path relative to app.url")
    p.add_argument("--demo", help="run this demo's setup() first")
    p.add_argument("--name", default="inspect", help="base name of the output files")
    p = sp.add_parser("new-project", help="create a project from the template")
    p.add_argument("name"); p.add_argument("--dir", help="where to create it (default projects/<name>)")
    p = sp.add_parser("new-demo", help="create demos/<demo> with brief.md and scene.py")
    p.add_argument("project"); p.add_argument("demo")
    p = sp.add_parser("list", help="demos of a project, their key moments and last run")
    p.add_argument("project")
    sp.add_parser("doctor", help="check Python, Playwright and ffmpeg")
    return ap


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # JSON stays UTF-8 when redirected on Windows
    args = build_parser().parse_args()
    COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
