# Benchmark report: bread-and-butter

- Final status: **ok**, with no missing moments or unplanned chapters. All eight final keyframes and the contact sheet were reviewed.
- Video: `projects/excalidraw/out/bread-and-butter/bread-and-butter.mp4`
- Duration: **128.57 seconds** (2:08.57), longer than the brief's approximately 90-second target.
- Model: `gpt-6.1-terra`.
- Runs: **4 checks**, **2 recordings**. The second check repeated the first scene because an editing command failed before it ran.

## Chapters and keyframe review

| Chapter | Start | Matches? | Evidence |
| --- | ---: | --- | --- |
| Blank canvas | 0:01.52 | Yes | Empty canvas and toolbar; the welcome screen has been dismissed. |
| Title | 0:04.30 | Yes | “Bread with butter and chives” is visible at the top. |
| Ingredients | 0:12.62 | Yes | Four labelled shapes form a column: bread, butter, chives and salt. |
| Steps | 0:32.90 | Yes | Three labelled step rectangles appear in a row with arrows from 1 to 2 to 3. |
| What goes where | 0:58.23 | Yes | Four arrows go from bread to 1, butter to 2, and chives and salt to 3. |
| Colors | 1:24.31 | Yes | Butter is yellow and chives green; the other existing shapes are unfilled. |
| Tip | 1:33.55 | Yes | A yellow square note near step 3 contains the full requested text. It is a rectangle styled as a sticky note because this local build has no sticky-note tool. |
| Done | 1:46.85 | Yes | The unfilled “Enjoy!” ellipse follows step 3 with an arrow; the fitted overview is readable and nothing is selected. |

## Tool and documentation observations

- The local build differs from `app.md`'s public-site description: shape tools are radios, and no sticky-note tool appears in the main toolbar or More tools. A square yellow rectangle provides the note visually.
- The default welcome screen includes a Sign up link. Drawing and deleting a temporary rectangle in `setup` dismisses it while leaving a blank canvas for the first chapter.
- The duration estimate substantially underpredicted the recording on this run: the final check estimated 90.0 seconds, while the recording lasted 128.57 seconds. The first recording was 143.5 seconds against a 103.6-second estimate. Keyboard shortcuts for repeated tool selection shortened the final recording, but it remains above target.
- The `python` command was unavailable in the shell; `python3` worked. The failed edit led to one redundant check run.
