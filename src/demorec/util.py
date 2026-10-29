"""Helpers shared by the modules: the run log, file name slugs, subprocess flags."""
import contextlib, re, shutil, sys, time, traceback, unicodedata

NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0  # creationflags: no console window on Windows

_sink = None  # open file while a run is active, so the terminal only gets the final summary


def set_sink(f):
    global _sink
    _sink = f


@contextlib.contextmanager
def log_to(path):
    """Send log() and log_exc() to a new file at path while the block runs."""
    with open(path, "w", encoding="utf-8") as f:
        set_sink(f)
        try:
            yield f
        finally:
            set_sink(None)


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, file=_sink or sys.stdout, flush=True)


def log_exc():
    traceback.print_exc(file=_sink or sys.stderr)
    (_sink or sys.stderr).flush()


def slug(s):
    """ASCII file name part of a title: `Ünits & prices` gives `units-prices`."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:50] or "x"


def ffmpeg_path(name="ffmpeg"):
    p = shutil.which(name)
    if not p:
        raise SystemExit("%s not found on PATH" % name)
    return p
