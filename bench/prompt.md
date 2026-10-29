You are a coding agent in a fresh clone of demorec, a tool that records demo videos of web
apps. This run is one entry of a model comparison. Every model gets this exact prompt.

Task: make the demo `{DEMO}` in `projects/excalidraw`. Its brief already exists at
`projects/excalidraw/demos/{DEMO}/brief.md` and is confirmed by the person. Do not change its
key moments. Write `scene.py` (and helpers if you need them), check it, record it.

How to work: read `AGENTS.md` and follow it. `projects/excalidraw` already has `app.md`,
`helpers.py` and a level 1 demo `first-diagram` you can learn from. The venv is in `.venv`
(`.venv/bin/demorec` on Linux, `.venv/Scripts/demorec` on Windows). Pass `--model {MODEL}`
to `demorec record`.

The app is a local copy of Excalidraw at {APP_URL}, and `project.toml` already points to it.
It can differ in details from excalidraw.com, which `app.md` describes. Trust what you see in
`inspect` over `app.md`.

Rules:
- Use only {APP_URL}. Never log in, sign up, share, open collaboration or upload.
- Do not edit anything under `src/`, `tests/`, `bench/`, `AGENTS.md`, `README.md` or the brief.
- Do not commit, push or add remotes.
- Every command sends stdout and stderr to a file, then you read the file.
- Stop after 60 minutes of work even if not done.

Done means: `demorec record` finished with status ok and no missing moments, and you looked at
every keyframe and they match the brief.

At the end write `BENCH_REPORT.md` in the repo root:
1. Final status, video path, duration, chapters.
2. Number of check runs and record runs.
3. For each key moment: does the keyframe match the brief, yes or no, and why.
4. Problems you hit with the tool or the docs.
