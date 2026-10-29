# BENCH_REPORT: excalidraw / bread-and-butter

Model: claude-opus-5-5

## 1. Final status

- `demorec record`: **status ok**, `missing_moments: []`, `unplanned_chapters: []`
- Video: `projects/excalidraw/out/bread-and-butter/bread-and-butter.mp4`
- Duration: **94.4 s** (brief: about 90 s), 1280x720, no audio
- Chapters (start in the video):

| # | Chapter | Start |
|---|---|---|
| 1 | Blank canvas | 0:00 |
| 2 | Title | 0:03.3 |
| 3 | Ingredients | 0:12.7 |
| 4 | Steps | 0:32.7 |
| 5 | What goes where | 0:47.8 |
| 6 | Colors | 1:01.8 |
| 7 | Tip | 1:10.1 |
| 8 | Done | 1:21.0 |

Files changed: `projects/excalidraw/demos/bread-and-butter/scene.py` (new),
`projects/excalidraw/helpers.py` (added few-step mouse helpers; `tool` and `box` are unchanged,
so `first-diagram` behaves as before), `projects/excalidraw/app.md` (section on the local copy:
selectors, coordinates, pitfalls). The scratch demo `_probe` was deleted.

## 2. Runs

- `check` runs: **5**, all status ok with no missing moments. Runs 2-5 tuned the pacing; the
  estimates were 133.9, 102.6, 94.6, 87.0 and 70.6 s.
- `record` runs of `bread-and-butter`: **3**, all status ok. Durations: 205.5 s, 143.1 s, **94.4 s** (final).
- Other runs: 5 `inspect` runs and 3 `record` runs of a scratch demo `_probe`, used to time
  actions during capture (see section 4).

## 3. Key moments vs. keyframes

| # | Key moment | Match | Why |
|---|---|---|---|
| 1 | Blank canvas | yes | Empty white canvas with the toolbar at the top and the cursor on it. No welcome screen, so "Live collaboration" and "Sign up" from it are not shown. |
| 2 | Title | yes | "Bread with butter and chives" in Very large hand-drawn text at the top centre, spelled correctly, nothing selected. |
| 3 | Ingredients | yes | Four rectangles in a column on the left: "bread", "butter", "chives", "salt". |
| 4 | Steps | yes | Three rectangles in a row: "1. Slice the bread", "2. Spread the butter", "3. Top with chives and salt", with arrows 1→2 and 2→3. |
| 5 | What goes where | yes | Arrows bread→1 (into its left side), butter→2, chives→3 and salt→3 (into the bottom edges). No arrow crosses a shape. |
| 6 | Colors | yes | "butter" filled yellow (#ffec99), "chives" filled green (#b2f2bb). All other shapes have no fill. Nothing selected. |
| 7 | Tip | yes | A sticky note under step 3, to its right: a rectangle with sharp corners and an orange paper fill, reading "Chop the chives just before serving". This local build has no Sticky note tool, so the note is a styled rectangle (see section 4). |
| 8 | Done | yes | An ellipse "Enjoy!" right of step 3 with an arrow from step 3. Then Shift+1 (zoom to fit) centred the whole diagram. Every label is readable and nothing is selected. Zoom stays at 100 %, because Excalidraw's zoom to fit never zooms past 100 % and the diagram already fit. |

The contact sheet shows nothing the brief forbids. The Excalidraw+ link and the share button
stay in the top right corner as part of the UI, but the cursor never goes near them. There are
no error messages or cut-off dialogs, and the cursor is visible throughout.

## 4. Problems with the tool or the docs

1. **`check` badly underestimates the video length for canvas apps.** The `estimated_duration_s`
   values of 94.6 s and 87.0 s gave 205 s and 143 s videos. During recording, each mouse event
   renders a frame and captures it through the screencast. Timed with a probe, a cursor step took
   60-100 ms and a step while drawing about 350 ms; even `wait(200)` took up to 0.5 s.
   `Actor.move` sends about 50 steps per second, and `click`/`drag` send at least 12 per move, so
   a demo with 16 drawn shapes doubles in length. Capture ran at only 4-9 fps. Check mode cannot
   see any of this, because it plays without the screencast. The host was also shared (load
   average 1-4 with nothing else running in the container), so record times varied 2-3×
   between runs of the same scene. The fix stayed inside the project: `helpers.py` gained
   `glide`/`tap`/`press`/`pull` (2-3 mouse steps each, still a visible cursor), and labels are
   typed with `delay=0`. A general fix would need the tool: for example a configurable step rate
   in `Actor.move`, or a record-mode duration estimate. Per the rules I did not touch `src/`.
2. **app.md does not match the local copy.** It lists a "Sticky note" tool, but the local build
   has none, neither in the toolbar nor under "More tools". The brief's moment 7 asks for a
   sticky note, so I drew a rectangle with sharp corners and an orange palette fill. Tools are
   radios, not buttons; `tool_button()` already handles that.
3. **The welcome screen conflicts with the brief.** It shows "Live collaboration..." and
   "Sign up", which this brief forbids. Nothing in the docs says how to hide it. Drawing and
   deleting a shape in `setup()` removes it.
4. **Sticky style settings.** In Excalidraw, a property changed on a selected shape becomes the
   default for the next shape. A Very large title made the next labels Very large, and a fill
   carried over to the next shape. app.md did not mention this; I added it.
5. **Unnamed radios.** The panel's radios (font size, edges, stroke width) have no accessible
   name, so `get_by_role` cannot reach them. `get_by_title("Very large")` / `get_by_title("Sharp")`
   works. Now noted in app.md.
6. Minor: `brief.md` asks for "zoomed to fit", but Excalidraw caps zoom to fit at 100 %. For a
   diagram that already fits, it only re-centres the view, which a viewer can easily miss.
