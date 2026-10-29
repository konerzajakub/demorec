# BENCH_REPORT: bread-and-butter (projects/excalidraw)

Model: claude-haiku-5-5

## 1. Final status

**Not done as the brief asks.** `demorec record` finished with `status: ok`, `missing_moments: []` and `unplanned_chapters: []`, but:

- Keyframe 7 (Tip) does not match the brief: the brief asks for a sticky note, and this build has none.
- The video is 145.8 s long. The brief asks for about 90 s.
- The video is 2560x1440. The brief asks for 1280x720.

Per AGENTS.md, I did not call it done. The person needs to decide on the tip form and on the length and resolution.

- Video: `/work/projects/excalidraw/out/bread-and-butter/bread-and-butter.mp4`
- Duration: 145.76 s (`result.json`), 146.1 s (ffprobe).
- Resolution: 2560x1440 (ffprobe). The viewport is 1280x720, so the output looks rendered at 2x.

Chapters, start times from the final record run:

| Chapter | Start (s) |
|---|---|
| Blank canvas | 1.5 |
| Title | 5.2 |
| Ingredients | 12.2 |
| Steps | 43.4 |
| What goes where | 78.8 |
| Colors | 104.4 |
| Tip | 113.1 |
| Done | 126.4 |

## 2. Run counts

- `check`: 4 runs, all `status: ok`, `missing_moments` empty. Estimates: 128.4 s, 112.3 s, 103.7 s, 102.2 s.
- `record`: 2 runs.
  - Run 1: 139.8 s. Its contact sheet showed the tip box filled green while its label was typed, because it inherited the last Background. Fixed in run 2, which is the output.
  - Run 2: 145.8 s. Final.
- `inspect`: 3 runs (start page, plus two scratch probes of the properties panel and the More tools menu). The `_probe` scratch demo was deleted.
- `doctor`: 1 run, ok.

## 3. Key moments

| # | Key moment | Keyframe matches brief | Why |
|---|---|---|---|
| 1 | Blank canvas | Yes | Welcome screen with the toolbar at the top, nothing drawn. |
| 2 | Title | Yes | "Bread with butter and chives" at the top of the canvas. |
| 3 | Ingredients | Yes | Four boxes, "bread", "butter", "chives", "salt", in a column on the left. |
| 4 | Steps | Yes | Three boxes in a row, "1. Slice the bread", "2. Spread the butter", "3. Top with chives and salt". Arrows 1 to 2 and 2 to 3. |
| 5 | What goes where | Yes | Arrows bread to 1, butter to 2, chives to 3, salt to 3. No arrows cross a box. |
| 6 | Colors | Yes | Butter filled `#ffec99` (yellow), chives filled `#b2f2bb` (green). All other shapes have no fill. |
| 7 | Tip | **No (partly)** | The text "Chop the chives just before serving" is exact and sits above step 3. But the brief asks for a sticky note, and this build has no sticky-note tool. The tip is a no-fill rectangle, which is not a note. |
| 8 | Done | Yes | "Enjoy!" ellipse below step 3, arrow from step 3 to it, nothing selected, text readable. Shift+1 zoom to fit: the view recentred, and the zoom stayed at 100% because the content already fits. |

Do-not-show: I did not log in, sign up, share, open Live collaboration, the Excalidraw+ page, or export. I did not click the Excalidraw+ link or the share button. I did not check the cursor path against those buttons.

## 4. Problems

Tool:
- `estimated_duration_s` under-predicted the recording. The check estimate was 102 s and the record was 146 s, about 40% longer. I could not separate the cause from the outside. Real mouse moves, typing and waits all count in record mode.
- The output is 2560x1440 for a 1280x720 viewport. The brief format says 1280x720. I did not change `src/` for this, as the task forbids it.
- Check mode only saves end-of-chapter screenshots. The green flash of the tip box (run 1) showed only in the record contact sheet, not in any check screenshot.

Docs:
- `app.md` listed a Sticky note in the toolbar, but this local build has none. The More tools menu has Frame, Web Embed, Laser pointer, Lasso selection, Text to diagram AI, Mermaid to Excalidraw and Wireframe to code AI. The brief asks for a sticky note, so the brief and this build disagree.
- `app.md` did not say that a new shape takes the last Background used, or that the properties panel covers the left side (x 16 to 216) while a shape is selected. I added both, plus the radio-button toolbar and the panel colors, to `app.md`.
- `git status` fails in `/work` with "dubious ownership". I did not run git or change git config.

## 5. Changes made

- `projects/excalidraw/demos/bread-and-butter/scene.py`: new.
- `projects/excalidraw/helpers.py`: added `arrow`, `background` and `fill`. `box` and `arrow` take optional `delay`, `dur` and `after` parameters. Defaults are unchanged, so `first-diagram` behaves as before.
- `projects/excalidraw/app.md`: corrected the glossary line and added pitfalls.
- Deleted `projects/excalidraw/demos/_probe` and its probe output files.
- Generated output in `projects/excalidraw/out/bread-and-butter/` and `out/_inspect/`.
- Not changed: `src/`, `tests/`, `bench/`, `AGENTS.md`, `README.md`, the brief. No commits, pushes or remotes. `pytest` was not run, since no `src/` file changed.

## 6. Decisions for the person

1. Tip: accept a no-fill box as the stand-in for the sticky note, or change the brief.
2. Length: accept about 146 s, or ask for a shorter cut. Shortening needs fewer labels or keyboard tool shortcuts, not just smaller holds.
3. Resolution: the 2x output may be a tool setting. The brief's 1280x720 is not met.
