"""Model comparison: every agent makes the same demo in its own Docker container.

    python bench/run.py --demo bread-and-butter --out ../demorec-bench

Each run gets a fresh clone of this repo's HEAD, a copy of the agent's login (deleted after
the run), the same prompt and a pinned local Excalidraw. Results land in <out>/<stamp>/:
one folder per run with the clone, the agent log, timings and the demo output, plus
summary.json for all runs.
"""
import argparse, json, os, shutil, subprocess, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE = "demorec-bench:1"
EXCALIDRAW = "excalidraw/excalidraw@sha256:f7ee194addd607bf831d2af0f0a34463dd4225e426cf35199ef0b12a803398e9"
NET = "demorec-bench"
APP_URL = "http://excalidraw/"
HOME = os.path.expanduser("~")

# Login files on this machine, copied into each container. Same lookup as the agent CLIs.
CLAUDE_LOGIN = os.path.join(os.environ.get("CLAUDE_CONFIG_DIR", os.path.join(HOME, ".claude")), ".credentials.json")
CODEX_LOGIN = os.path.join(os.environ.get("CODEX_HOME", os.path.join(HOME, ".codex")), "auth.json")
CLAUDE_CONF, CODEX_CONF = "/home/bench/.claude", "/home/bench/.codex"  # config dirs inside the container

# name: (agent, model, effort, login files to copy, config dir inside the container)
RUNS = {
    "opus-5.5": ("claude", "claude-opus-5-5", "xhigh", [CLAUDE_LOGIN], CLAUDE_CONF),
    "sonnet-5.5": ("claude", "claude-sonnet-5-5", "xhigh", [CLAUDE_LOGIN], CLAUDE_CONF),
    "haiku-5.5": ("claude", "claude-haiku-5-5", "xhigh", [CLAUDE_LOGIN], CLAUDE_CONF),
    "gpt-6.1-sol": ("codex", "gpt-6.1-sol", "xhigh", [CODEX_LOGIN], CODEX_CONF),
    "gpt-6.1-terra": ("codex", "gpt-6.1-terra", "xhigh", [CODEX_LOGIN], CODEX_CONF),
    "gpt-6-luna": ("codex", "gpt-6-luna", "xhigh", [CODEX_LOGIN], CODEX_CONF),
}


def sh(args, log=None, check=True):
    """Run a command with its output appended to log."""
    with open(log or os.devnull, "ab") as f:
        r = subprocess.run(args, stdout=f, stderr=f)
    if check and r.returncode != 0:
        raise SystemExit("failed: %s (see %s)" % (" ".join(args[:4]), log))
    return r.returncode


def read_text(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def use_local_excalidraw(repo):
    """Point the clone's Excalidraw project at the pinned container instead of excalidraw.com."""
    toml = os.path.join(repo, "projects", "excalidraw", "project.toml")
    with open(toml, encoding="utf-8") as f:
        s = f.read().replace('url = "https://excalidraw.com/"', 'url = "%s"' % APP_URL)
    with open(toml, "w", encoding="utf-8") as f:
        f.write(s)


def start_excalidraw(log):
    sh(["docker", "network", "create", NET], log, check=False)
    sh(["docker", "rm", "-f", "excalidraw"], log, check=False)
    sh(["docker", "run", "-d", "--name", "excalidraw", "--network", NET, EXCALIDRAW], log)


def stop_excalidraw(log):
    sh(["docker", "rm", "-f", "excalidraw"], log, check=False)


def prepare(run_dir, name, demo):
    """Clone, prompt and login copy for one run."""
    agent, model, effort, logins, conf = RUNS[name]
    repo = os.path.join(run_dir, "repo")
    sh(["git", "clone", "-q", ROOT, repo])
    sh(["git", "-C", repo, "remote", "remove", "origin"])
    shutil.rmtree(os.path.join(repo, "docs", "bench"), ignore_errors=True)  # no earlier model's scene to copy
    use_local_excalidraw(repo)
    with open(os.path.join(repo, "bench", "prompt.md"), encoding="utf-8") as f:
        prompt = f.read()
    for k, v in {"{DEMO}": demo, "{MODEL}": model, "{APP_URL}": APP_URL}.items():
        prompt = prompt.replace(k, v)
    with open(os.path.join(repo, "bench", "prompt.txt"), "w", encoding="utf-8") as f:
        f.write(prompt)
    auth = os.path.join(run_dir, "login")
    os.makedirs(auth)
    for f in logins:
        shutil.copy(f, auth)
    os.makedirs(os.path.join(run_dir, "agent"))
    return repo, auth, agent, model, effort, conf


def start_run(base, name, demo, log):
    """Start one agent's container. Returns the container name."""
    run_dir = os.path.join(base, name)
    repo, auth, agent, model, effort, conf = prepare(run_dir, name, demo)
    cname = "demorec-bench-" + name.replace(".", "-")
    sh(["docker", "rm", "-f", cname], log, check=False)
    env = {"AGENT": agent, "MODEL": model, "EFFORT": effort,
           "CLAUDE_CONFIG_DIR": conf if agent == "claude" else "", "CODEX_HOME": conf if agent == "codex" else ""}
    args = ["docker", "run", "-d", "--name", cname, "--network", NET, "--shm-size", "1g",
            "-v", repo + ":/work", "-v", os.path.join(run_dir, "agent") + ":/out", "-v", auth + ":" + conf]
    for k, v in env.items():
        args += ["-e", "%s=%s" % (k, v)]
    sh(args + [IMAGE], log)
    return cname


def finish_run(base, name, cname, log):
    """Wait for the container, keep its log, then delete it and the login copy."""
    sh(["docker", "wait", cname], log)
    run_dir = os.path.join(base, name)
    sh(["docker", "logs", cname], os.path.join(run_dir, "agent", "container.log"), check=False)
    sh(["docker", "rm", cname], log, check=False)
    shutil.rmtree(os.path.join(run_dir, "login"), ignore_errors=True)  # never keep login copies


def summarize(base, names, demo):
    summary = {}
    for name in names:
        d = os.path.join(base, name)
        res = os.path.join(d, "repo", "projects", "excalidraw", "out", demo, "result.json")
        summary[name] = {"model": RUNS[name][1], "effort": RUNS[name][2],
                         "start": read_text(os.path.join(d, "agent", "start.txt")),
                         "end": read_text(os.path.join(d, "agent", "end.txt")),
                         "agent_exit": read_text(os.path.join(d, "agent", "exit.txt")),
                         "result": read_json(res) if os.path.exists(res) else None}
    with open(os.path.join(base, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", default="bread-and-butter")
    ap.add_argument("--runs", default=",".join(RUNS))
    ap.add_argument("--out", default=os.path.join(os.path.dirname(ROOT), "demorec-bench"))
    a = ap.parse_args()
    stamp = time.strftime("%Y%m%d-%H%M%S")
    base = os.path.abspath(os.path.join(a.out, stamp))
    os.makedirs(base)
    log = os.path.join(base, "docker.log")

    start_excalidraw(log)
    started = {}
    for name in a.runs.split(","):
        started[name] = start_run(base, name, a.demo, log)
        print("started", name, flush=True)
    for name, cname in started.items():
        finish_run(base, name, cname, log)
        print("finished", name, flush=True)
    stop_excalidraw(log)
    summarize(base, started, a.demo)
    print(base)


if __name__ == "__main__":
    main()
