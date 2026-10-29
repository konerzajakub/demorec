# BENCH_REPORT: bread-and-butter (projects/excalidraw)

Model: claude-sonnet-5-5. Work time about 30 minutes (07:49 to 08:17 UTC).

## 1. Final status

- Status: `ok`, `missing_moments` is empty, `unplanned_chapters` is empty.
- Video: `projects/excalidraw/out/bread-and-butter/bread-and-butter.mp4`, 1280x720, 30 fps, **94.9 s**
  (brief: about 90 s). No audio.
- Chapters (start in s, same titles and order as the brief):

| # | Chapter | Start |
|---|---|---|
| 1 | Blank canvas | 1.5 |
| 2 | Title | 3.4 |
| 3 | Ingredients | 9.5 |
| 4 | Steps | 25.6 |
| 5 | What goes where | 45.8 |
| 6 | Colors | 61.2 |
| 7 | Tip | 69.3 |
| 8 | Done | 78.2 |

Files changed: `projects/excalidraw/demos/bread-and-butter/scene.py` (new), `projects/excalidraw/helpers.py`
(extended, defaults unchanged), `projects/excalidraw/app.md` (notes on the local build). Nothing under `src/`,
`tests/`, `bench/`, `AGENTS.md`, `README.md` or the brief was touched. `project.toml` shows as modified in git,
but the change (URL set to `http://excalidraw/`) was there before I started.

## 2. Runs

- `check` on bread-and-butter: **7**, all `status: ok`. Estimated length per run: 155.9, 110.2, 101.4, 99.3,
  82.5, 75.6, 75.7 s. Runs 2 to 6 only changed pacing, the layout of the note and the fill handling.
- Other `check` runs: 1 on a scratch demo `_probe` (Escape deselects, set the background before drawing),
  deleted afterwards, and 1 on `first-diagram` to confirm the helper change did not break it (ok, 37.5 s).
- `record`: **3**. Run 1: 134.5 s. Run 2: 95.0 s. Run 3 (final): 94.9 s.
  - Run 1 was too long, and its contact sheet showed two defects `check` did not show (see section 4).
  - Run 2 fixed both. Its keyframes 4 and 5 had the cursor on top of an arrowhead.
  - Run 3 parks the cursor on empty canvas at the end of "Steps" and "What goes where".
- `inspect`: 3 (blank page, "More tools" menu, a selected shape) plus 2 wrong calls (see section 4).

## 3. Key moments against the keyframes of the final recording

I looked at all 8 keyframes and at `contact.jpg` of run 3.

1. **Blank canvas: yes.** Blank canvas, toolbar at the top, welcome screen, cursor on the Rectangle button.
2. **Title: yes.** "Bread with butter and chives" at the top of the canvas, spelled correctly, nothing selected.
3. **Ingredients: yes.** Four rectangles in a column on the left: "bread", "butter", "chives", "salt", all
   without fill.
4. **Steps: yes.** Three rectangles in a row: "1. Slice the bread", "2. Spread the butter",
   "3. Top with chives and salt" (3 lines, fits). Arrows 1 to 2 and 2 to 3, arrowheads visible (cursor parked
   away).
5. **What goes where: yes.** bread to 1, butter to 2, chives to 3, salt to 3. The two arrows to step 3 end at
   different points on its bottom edge, so both are visible. They do not cross each other or a shape.
6. **Colors: yes.** "butter" yellow (`#ffec99`), "chives" green (`#b2f2bb`). "bread", "salt", the steps and
   the title have no fill. Nothing selected, panel closed.
7. **Tip: yes, with a deviation.** This build has no Sticky note tool (the toolbar has no such button, "More
   tools" does not list it). The note is a rectangle with a yellow fill and the text "Chop the chives just
   before serving", directly below step 3 (about 45 px). It looks like a sticky note, but it is a
   rectangle. Its yellow is the same as "butter". Moment 6 ("all other shapes keep no fill") is checked
   before the note exists, but a reviewer who applies it to the last frame will see a second filled shape.
8. **Done: yes, with a caveat.** Ellipse "Enjoy!" right of step 3, no fill, with an arrow from step 3.
   Shift+1 (zoom to fit) was pressed, the whole diagram is centered, all text readable, nothing selected,
   cursor at the bottom on empty canvas. The zoom stays at 100 % (Excalidraw does not zoom in above 100 %
   and the diagram already fit), so the viewer sees the drawing slide to the middle, not a change of scale.

The keyframes show no error message, empty table or cut-off dialog. The scene never touches "Excalidraw+",
the share button, Live collaboration or Sign up: toolbar clicks are at x 520 to 760, y 38, and no mouse path
goes near the top right corner. The cursor is visible in every keyframe.

## 4. Problems with the tool and the docs

- **`<project>` in AGENTS.md is a path.** The command table writes `demorec inspect <project>`,
  `new-demo <project> <id>`, `check <project> <id>`, but `demorec inspect excalidraw` fails with
  "no project.toml in /work/excalidraw". It needs `projects/excalidraw`. Only the last line of AGENTS.md
  shows a path (`demorec record projects/example add-task`). I lost two calls to this.
- **`check` underestimates the recording by about 35 %.** Estimate 99.3 s, real video 134.5 s. Probably the mouse
  moves: `Actor.move` paces its steps by the clock, and I did not measure why they take longer while the screen
  is captured. AGENTS.md says to adjust holds
  if the estimate is far from the target, but the estimate is only right when the scene has few moves. I
  needed an estimate of about 75 s to get 95 s, and had to record once to learn this. A note in AGENTS.md or
  an `estimated_duration_s` that includes the overhead would save a record run.
- **`check` hides problems that only show during the run.** Excalidraw gives every new shape the last
  Background color picked. In record run 1 the note was drawn green (from "chives") before I made it
  yellow, and the final ellipse came out yellow. `check` only saves the end state of each chapter, so the
  green flash was visible only in the contact sheet (the yellow ellipse was already in the end screenshot
  of the first checks, I did not notice it there). The fix is to pick the Background in the panel while the drawing tool
  is active, before drawing (`helpers.background`), and `transparent` for the ellipse.
- **The brief asks for a sticky note, the local build has none**, and neither `app.md` nor AGENTS.md says
  what to do when a tool is missing. `app.md` lists "Sticky note" in the toolbar (true for excalidraw.com).
  I emulated it and noted it above and in `app.md`.
- **The shared `box` helper had a fixed, slow pace** (about 5 s per shape recorded). With 9 shapes and 7
  arrows the demo was over 130 s. I added optional pacing parameters (`delay`, `dur`, `after`, `key`, `before`,
  `shape`) with the old values as defaults, so `first-diagram` is unchanged (its check is still ok).
- **`check` takes 50 to 105 s** on this scene, because only `hold` and mouse moves are scaled down, the
  waits after clicks and key presses are not.
- Small things: `git status` in `/work` fails with "dubious ownership" (I used
  `git -c safe.directory=/work`, no config change). There is no Actor method for a keyboard shortcut chord
  like zoom to fit, `a.key("Shift+1")` works. The title stayed at the default font size: I expected that a larger size
  would carry over to all later labels (as the Background color does), and did not test it.
