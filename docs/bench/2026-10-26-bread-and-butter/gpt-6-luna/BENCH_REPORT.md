# bread-and-butter benchmark report

## Final result

- Status: `ok`; `missing_moments` is empty.
- Video: `projects/excalidraw/out/bread-and-butter/bread-and-butter.mp4`
- Duration: 165.71 seconds (about 2:46), versus the brief's target of about 90 seconds.
- Recorded chapter starts:
  - Blank canvas — 1.53 s
  - Title — 4.99 s
  - Ingredients — 15.72 s
  - Steps — 52.89 s
  - What goes where — 89.52 s
  - Colors — 114.70 s
  - Tip — 125.19 s
  - Done — 141.34 s
- Reviewed all eight recorded keyframes and `contact.jpg`.

## Runs

- Check runs: 4 total (2 failed during scene development, followed by 2 passing checks).
- Record runs: 1, completed successfully with model `gpt-6-luna`.

## Key moment review

| Key moment | Match? | Review |
|---|---|---|
| Blank canvas | Yes | Empty canvas and Shapes toolbar are visible; the welcome screen is gone. |
| Title | Yes | “Bread with butter and chives” is readable at the top. |
| Ingredients | Yes | Bread, butter, chives and salt appear in a labeled column on the left. |
| Steps | Yes | The three labeled step rectangles appear in left-to-right order, connected by arrows. They are staggered vertically to keep the ingredient arrows clear. |
| What goes where | Yes | Arrows connect bread to step 1, butter to step 2, and chives and salt to step 3. |
| Colors | Yes | Butter is yellow, chives are green, and the other existing shapes have no fill. |
| Tip | Yes, visually | The exact tip text appears in a yellow note-style rectangle beside step 3. This build has no Sticky note tool. |
| Done | Yes | The step 3 arrow leads to an unfilled “Enjoy!” ellipse. At 90% zoom, all text is readable and nothing is selected. |

## Problems encountered

- The local Excalidraw build differs from `app.md`: its toolbar has no Sticky note tool, so the tip is represented by a yellow filled rectangle. The current toolbar and palette details are now recorded in `projects/excalidraw/app.md`.
- The drawing properties panel covers the leftmost canvas area while a tool is active. The first ingredient coordinates landed beneath it; moving the column right fixed the issue.
- The first-run welcome screen includes collaboration and account controls. A temporary rectangle followed by Undo in `setup` dismissed it without opening those controls. The app's Excalidraw+, share and Live collaboration controls remain visible in the site chrome and were never clicked or hovered.
- The passing check estimated 119.2 seconds, but the recorded video is 165.71 seconds. Repeated visible cursor paths make the actual recording longer than the check estimate and the target.
