"""Records the scenes of a finished comparison again with the current recorder.

    python bench/rerecord.py docs/bench/2026-10-26-bread-and-butter

Each model folder holds scene.py and optionally helpers.diff. For every model: a fresh clone
of HEAD, its helper changes applied, its scene in place, then `demorec record` in the bench
image against the pinned Excalidraw, one model after another so they do not share the CPU.
The video and result.json replace the ones in the model folder.
"""
import argparse, os, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import IMAGE, NET, ROOT, read_json, sh, start_excalidraw, stop_excalidraw, use_local_excalidraw  # noqa: E402

SCRIPT = ("cd /work && python3 -m venv --system-site-packages .venv > /out/setup.log 2>&1"
          " && .venv/bin/pip install -q -e . >> /out/setup.log 2>&1"
          " && .venv/bin/demorec record projects/excalidraw %s --model \"%s\" > /out/record.out.log 2> /out/record.err.log")


def rerecord(src, work, demo, log):
    """Record the scene in model folder src again. Returns the demo's out folder in the clone."""
    name = os.path.basename(src)
    repo, out = os.path.join(work, "repo"), os.path.join(work, "out")
    os.makedirs(out)
    sh(["git", "clone", "-q", ROOT, repo], log)
    use_local_excalidraw(repo)
    diff = os.path.join(src, "helpers.diff")
    if os.path.exists(diff) and os.path.getsize(diff):
        sh(["git", "-C", repo, "apply", diff], log)
    shutil.copy(os.path.join(src, "scene.py"), os.path.join(repo, "projects", "excalidraw", "demos", demo))
    model = read_json(os.path.join(src, "result.json")).get("model", "")
    cname = "demorec-rerecord-" + name.replace(".", "-")
    sh(["docker", "rm", "-f", cname], log, check=False)
    sh(["docker", "run", "--rm", "--name", cname, "--network", NET, "--shm-size", "1g",
        "-v", repo + ":/work", "-v", out + ":/out", "--entrypoint", "bash", IMAGE, "-c", SCRIPT % (demo, model)], log,
       check=False)
    return os.path.join(repo, "projects", "excalidraw", "out", demo)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bench_dir")
    ap.add_argument("--demo", default="bread-and-butter")
    ap.add_argument("--runs", default="")
    a = ap.parse_args()
    bench = os.path.abspath(a.bench_dir)
    names = a.runs.split(",") if a.runs else sorted(n for n in os.listdir(bench)
                                                    if os.path.exists(os.path.join(bench, n, "scene.py")))
    base = tempfile.mkdtemp(prefix="demorec-rerecord-")
    log = os.path.join(base, "docker.log")
    start_excalidraw(log)
    try:
        for name in names:
            src = os.path.join(bench, name)
            res = rerecord(src, os.path.join(base, name), a.demo, log)
            if not os.path.exists(os.path.join(res, a.demo + ".mp4")):
                print("failed", name, res, flush=True)
                continue
            shutil.copy(os.path.join(res, a.demo + ".mp4"), src)
            shutil.copy(os.path.join(res, "result.json"), src)
            print("recorded", name, flush=True)
    finally:
        stop_excalidraw(log)
    print(base)


if __name__ == "__main__":
    main()
