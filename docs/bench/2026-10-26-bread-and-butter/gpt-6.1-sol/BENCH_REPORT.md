# BENCH_REPORT

1. **Final status, video, duration and chapters**

`demorec record` completed with **status: ok**, `missing_moments: []`, and
`unplanned_chapters: []`. Model: `gpt-6.1-sol`.

Video: [bread-and-butter.mp4](projects/excalidraw/out/bread-and-butter/bread-and-butter.mp4).
Encoded duration: **141.034 seconds (2:21)**. The runner reports
`duration_s: 139.77`. Verified with ffprobe: 1280×720, H.264, 30 fps,
no audio stream.

**Timing deviation:** the video is longer than the brief’s approximately 90-second
target. All eight required visual states match; the duration target was not met.

Chapter titles and order are unchanged from the confirmed brief. Start times below
come from demorec’s chapter metadata; the opening hold belongs to chapter 1.

2. **Run counts**

**4 check runs; 3 record runs.** Doctor also passed. Inspections were used for tool,
font, fill and empty-canvas states; the temporary `_probe` demo was removed.

| Run | Result | Duration / finding |
| --- | --- | --- |
| Check 1 | ok, no missing moments | Estimated 100.1 s; visual review found the unwanted opening welcome panel. |
| Check 2 | failed | Helper rename typo caused `NameError` at Title; corrected. |
| Check 3 | ok, no missing moments | Estimated 98.5 s; all chapter screenshots reviewed. |
| Check 4 | ok, no missing moments | Estimated 86.8 s after keyboard shortcuts; all screenshots reviewed. |
| Record 1 | ok, no missing moments | 137.30 s in runner metadata; all keyframes and contact sheet reviewed. |
| Record 2 | ok, no missing moments | 160.53 s in runner metadata; all keyframes and contact sheet reviewed. |
| Record 3, final | ok, no missing moments | 139.77 s in runner metadata; 141.034 s encoded. |

The last adjustment changed only recording cursor speed. Check mode retains the
same runner-controlled speed and behavior that passed check 4.

3. **Keyframe review**

I opened every final keyframe at full viewport size and the final contact sheet.
The cursor is visible, labels are spelled correctly, and no error dialog or
selection obscures a chapter’s final state.

| Start | Key moment / chapter | Matches? | Why |
| --- | --- | --- | --- |
| 00:00 | Blank canvas | Yes | Empty drawing area and toolbar; the welcome panel is absent. |
| 00:04 | Title | Yes | The exact title “Bread with butter and chives” is readable at the top. |
| 00:12 | Ingredients | Yes | Four unfilled shapes form a left column, labelled bread, butter, chives and salt. |
| 00:28 | Steps | Yes | Three recipe rectangles form a row with the exact step labels and arrows 1 → 2 → 3. |
| 00:56 | What goes where | Yes | Four arrows connect bread → 1, butter → 2, chives → 3 and salt → 3. |
| 01:19 | Colors | Yes | Butter is yellow and chives is green; the other existing shapes remain unfilled. |
| 01:30 | Tip | Yes | A yellow sticky-note-style card near step 3 contains the exact text “Chop the chives just before serving”. |
| 01:47 | Done | Yes | An unfilled ellipse says “Enjoy!”, an arrow leads from step 3, and the fitted overview is readable with nothing selected. |

Keyframes: [keyframes/](projects/excalidraw/out/bread-and-butter/keyframes/).
Contact sheet: [contact.jpg](projects/excalidraw/out/bread-and-butter/contact.jpg).
Result metadata: [result.json](projects/excalidraw/out/bread-and-butter/result.json).
Chapters: [chapters.vtt](projects/excalidraw/out/bread-and-butter/chapters.vtt).

4. **Problems with the tool or documentation**

- The local build differs from app.md’s public-site description: tools are radios,
  and no Sticky note tool exists, even under More tools. The tip is therefore a
  square-corner, solid yellow rectangle with bound text, visually serving as a
  sticky note. The local selectors and coordinates are documented in app.md.
- Selection on an empty drawing restores the welcome panel. Escape and a blank
  click did not dismiss it. Starting capture with Hand selected gives a blank
  drawing area with the toolbar and no welcome panel.
- Font size, Edges and Stroke width radios lack accessible names. Their named
  groups and inspected visual order provide stable locators.
- Check success validates chapter coverage, not the promised visual state. The
  first check passed despite the welcome panel; screenshot review caught it.
- Recording took substantially longer than check estimated, and timings varied
  between runs. Number shortcuts and reduced cursor animation did not bring the
  final video near 90 seconds. Reading pauses were kept at their requested real
  duration. No tool source was changed to work around this.
- The encoded file is about 1.26 seconds longer than the runner’s duration field;
  both values are reported above.
- One check failure was my scene helper rename error, not a tool defect. It was
  fixed before the successful checks and recordings.

The confirmed brief and protected source/test/benchmark files were not edited.
All browser work used http://excalidraw/; no account, sharing, collaboration,
upload or cloud-export feature was opened. Artifacts remain local.
