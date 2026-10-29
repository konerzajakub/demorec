# bread-and-butter, 2026-10-26

Level 2 of the Excalidraw ladder: a recipe diagram with 8 key moments, about 90 s, English labels.
Brief: [`projects/excalidraw/demos/bread-and-butter/brief.md`](../../../projects/excalidraw/demos/bread-and-butter/brief.md).

## Setup

- `python bench/run.py --demo bread-and-butter`, one pair of models per run, each pair started
  within one second:
  - Opus 5.5 and GPT-6.1 sol on 2026-10-26.
  - Sonnet 5.5 and GPT-6.1 Terra on 2026-10-27. Their clone also held the first pair's results
    under `docs/`.
  - Haiku 5.5 and GPT-6 Luna on 2026-10-28. Their clone had no `docs/bench`.
- One Docker container per agent (`bench/Dockerfile`), a fresh clone each, the same prompt
  (`bench/prompt.md`), 60 minute limit.
- Local Excalidraw pinned by image digest, so all saw the same UI.
- Claude Code 2.1.310 with `claude-opus-5-5`, `claude-sonnet-5-5` and `claude-haiku-5-5`, effort
  `xhigh`. Codex CLI 0.163.0 with `gpt-6.1-sol`, `gpt-6.1-terra` and `gpt-6-luna`, reasoning
  `xhigh`. Codex has no GPT-6.1 Luna. None got any personal instructions or skills.

## Re-recorded on 2026-10-28

- The first four ran with Czech labels and an older recorder. That recorder slowed every mouse
  event on the canvas, so videos ran longer than their scenes asked for.
- On 2026-10-28 the labels and chapter titles in their scenes were translated to English, and
  all six scenes were recorded again with the current recorder (`python bench/rerecord.py`),
  one after another on an idle machine.
- Layout and timing are what each model wrote. The first four tuned their timing against the
  old recorder, so their videos are now shorter than when the agent finished. Haiku and Luna
  ran with the current recorder and the English brief from the start.
- Video length below is from that re-recording. Agent time, runs and tokens are from the
  original runs.

## Results

| | Claude Opus 5.5 | GPT-6.1 sol | Claude Sonnet 5.5 | GPT-6.1 Terra | Claude Haiku 5.5 | GPT-6 Luna |
|---|---|---|---|---|---|---|
| Result | 8 of 8 key moments | 8 of 8 key moments | 8 of 8 key moments | 8 of 8 key moments | 8 of 8 key moments | 8 of 8 key moments |
| Video length (target about 90 s) | 51.8 s | 64.4 s | 93.8 s | 112.9 s | 129.8 s | 140.9 s |
| Agent time | 39 min | 26 min | 25 min | 16 min | 19 min | 24 min |
| check / record runs | 5 / 3, plus 3 timing probes | 4 / 3 | 7 / 3, plus 2 on other demos | 4 / 2 | 4 / 2 | 4 / 1 |
| Input tokens (cached) | 8.41 M (8.20 M) | 5.05 M (4.96 M) | 4.67 M (4.49 M) | 4.14 M (4.06 M) | 4.23 M (4.02 M) | 7.99 M (7.82 M) |
| Output tokens (reasoning) | 101.5 k (65.6 k) | 36.5 k (22.3 k) | 75.8 k (49.4 k) | 12.7 k (2.5 k) | 82.9 k (63.1 k) | 65.0 k (51.5 k) |
| Cost | $5.17 | not reported (ChatGPT plan) | $1.92 | not reported (ChatGPT plan) | $0.45 | not reported (ChatGPT plan) |
| Peak RAM of the agent CLI | not measured | not measured | 331 MB | about 300 MB | not measured | not measured |

Side by side at full speed: [`comparison.mp4`](comparison.mp4). Each row pairs a Claude and a
GPT model of the same tier: Opus and Sol, Sonnet and Terra, Haiku and Luna. Shorter videos hold
their last frame.

Each folder holds the video, `result.json`, the scene the model wrote, its changes to the
shared helpers (Terra changed none) and its own report.

Peak RAM was sampled every 5 s inside the container for the second pair only. It counts the
agent CLI processes (Codex: the Node launcher, `codex` and `codex-code-mode`). Chromium and
ffmpeg peaked at about 255 MB and 350 MB in both runs and are demorec's share, the same for
every model.

## Caveats

- One run per model. Single runs vary, so this shows what each model can do, not an average.
- Key moments were checked against the keyframes by Claude Opus 5.5, which is not a neutral
  judge. All videos are here to judge for yourself.
- The local Excalidraw has no sticky note tool. Five models drew a yellow rectangle instead,
  Claude Haiku 5.5 a plain white one. Haiku's own report calls the tip a mismatch for that reason.
- GPT-6.1 Terra placed the tip note above step 3 with a wide gap, and its ingredient arrows
  cross each other. GPT-6 Luna set the three steps on a diagonal, not in a straight row. The
  brief does not forbid either.
- Video length depends on free CPU while recording. The same scenes on a machine busy with
  other containers ran up to twice as long.
