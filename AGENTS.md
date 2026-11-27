# AGENTS.md

demorec records demo videos of web applications. You, the agent, write and run the demos. The
person tells you what to show and approves the result. They do not write scene code.

## Layout

- `src/demorec/`: the tool. `actor.py` has every action a scene can use, read it before writing a scene.
- `projects/<app>/`: one folder per application.
  - `app.md`: what the app is. Read it before any work on that app.
  - `project.toml`: URL, browser size, locale, login, reset command.
  - `helpers.py`: actions shared by the app's demos.
  - `demos/<id>/brief.md`: what the person wants to show. `demos/<id>/scene.py`: the script.
  - `out/<id>/`: results, never edited by hand.
- `projects/_template/`: what `new-project` and `new-demo` copy.
- `projects/example/`: a working project with no server, the reference for style.
- `projects/excalidraw/`: a demo of a public website with a canvas, the reference for
  third-party sites and drawing apps.

## Commands

Run from the repo root with the venv active (`.venv/Scripts/demorec` on Windows,
`.venv/bin/demorec` elsewhere). Each command prints one JSON object and exits 0 on success.
Run logs go to files, never stream them.

| Command | Use |
|---|---|
| `demorec doctor` | Check Python, Playwright, its Chromium and ffmpeg. Run first on a new machine. |
| `demorec new-project <name>` | Create `projects/<name>` from the template. |
| `demorec new-demo <project> <id>` | Create `demos/<id>/brief.md` and `scene.py`. |
| `demorec inspect <project> [--path P] [--demo ID] [--name N]` | Log in, open a page (or run a demo's `setup`), save a screenshot and the accessibility tree. |
| `demorec check <project> <id> [--no-before]` | Play the scene fast, no capture. Saves a screenshot of each chapter's end state in `out/<id>/check/` and estimates the video length (`estimated_duration_s`). `--no-before` skips the data reset, only for scenes that change no data. |
| `demorec record <project> <id> --model <id>` | Record the video and write all artifacts. Pass your own model id (for example `claude-opus-5-5`), it is stored in `result.json`. |
| `demorec list <project>` | Demos, their key moments and their last run. |

## Workflow

1. App context. If `app.md` is missing or a template, fill it before anything else. Read the
   app's repository (README, routes, UI text, test ids, seed data) and a running instance with
   `inspect`. Ask the person only what those cannot answer: the audience, which features are
   unfinished, how to reset demo data. Then set `[app] url` and `ready` in `project.toml`, and
   uncomment `[login]` only if the app has a login form.
2. Demo intent. Write `brief.md` with the person. Audience, goal, story, key moments, what not
   to show, format. Key moments are the contract: each one is a state that must be visible on
   screen. Show the person the brief and wait for their confirmation before step 3.
3. Scene. Write `scene.py`: one `a.chapter("<title>")` per key moment, the same title as in
   the brief, in the same order. Put repeated steps into `helpers.py`. Find selectors in the
   `inspect` output, not by guessing.
4. Check. Run `check` until `status` is `ok` and `missing_moments` is empty. On failure read
   `error`, `error_at_chapter`, `failure.png` and `failure.aria.yml` in the out folder. A passing
   check can still show the wrong thing: look at the screenshots in `check/` before recording.
   If `estimated_duration_s` is far from the brief's target length, adjust holds or the brief.
5. Record. Run `record`. Then look at every image in `keyframes/` (one per chapter, the frame at
   the chapter's end) and at `contact.jpg`. Each keyframe must show what its key moment in
   the brief promises. Also look for things the brief forbids, error messages, empty tables,
   cut-off dialogs and a missing cursor.
6. Hand over. Give the person the video path, the duration and one line per chapter. Do not
   call it done while a keyframe disagrees with the brief.

## Writing scenes

- Use `Actor` methods (`click`, `type`, `hover`, `choose`, `drag`, `write`, `hold`) for everything
  the viewer should see. Plain Playwright calls (`a.pg...`) jump without a visible cursor, use
  them only for waits and reads.
- Locators: `get_by_role` with the accessible name first, then `get_by_label`,
  `get_by_test_id`, `get_by_text`. No CSS classes from component libraries unless nothing else
  exists. Scope locators to the dialog or panel they live in.
- Pace: `hold(1.5)` to `hold(2.5)` after each result the viewer should read, `hold(1.0)` after
  small steps. The viewer needs time to read: a 10-word message needs about 2 s.
- After a result appears, `a.rest(loc)` leaves the cursor next to it without covering any text:
  beside it, under it or in an empty part of it. `a.hover(loc)` puts the arrow on the text the
  viewer wants to read.
- A chapter ends where the next one starts. Wait for its result (`a.see(...)`) and hold before
  the next `chapter()` call, so the keyframe shows the outcome.
- Things that disappear on their own (notifications, toasts) must be visible at the chapter's end.
- Put preparation the viewer must not see (navigation, creating data) into `setup(a)`.
- To inspect a state that only exists after some steps (an open panel, a selected item), create
  a scratch demo whose name starts with `_` (`new-demo <project> _probe`), put the steps into its
  `setup(a)` and run `inspect <project> --demo _probe`. `list` and the tests skip `_` demos.
  Delete it when done.
- Selects, dropdowns, comboboxes and menus: `a.choose(control, "Label")` opens the control and
  picks the option or menu item with that label. The cursor runs down the 3 entries above it
  (`glide=3`, 0 goes straight), each just right of its text, then clicks it, and finally steps
  off beside the control so the chosen value is readable (`rest=False` stays). A long list's own
  scroll area glides to the option first.
  - Submenus: `a.choose(menu_button, ["Export", "PDF"])`.
  - A combobox that filters as you type: `a.choose(field, "Gamma Labs", search="gam")`.
  - `exact=False` matches a part of the label.
  - A native `<select>` is drawn by the OS and never captured: `choose` shows the click and sets
    the value (its label or value).
  - Plain navigation links are no menu: `a.click(nav.get_by_role("link", name="Reports"))`.
- File pickers are drawn by the OS and are not captured. Set the files with Playwright.
- The browser print dialog is not captured. Use `a.print_preview()`.
- Downloads: `a.download(locator, name)` returns the path, `a.show_file(path)` shows it in a
  window of its own and returns to the app in one call.
- A downloaded PDF that a chapter's keyframe should show: `a.pdf_show(path)` puts it in the
  browser's PDF viewer over the whole app, in the same tab, `a.pdf_scroll(600)` glides down it,
  `a.pdf_hide()` returns to the app, also in the next chapter. A zoomed camera cuts to the full
  frame, the drawn cursor hides over the PDF. It needs a browser with a PDF viewer:
  `channel = "chromium"` (or `"chrome"`) in `[browser]`. With a transition:

  ```python
  pdf = a.download(dlg.get_by_role("button", name="PDF"), "quote.pdf", transition="pdf")
  a.chapter("Quote PDF")
  a.pdf_show(pdf)
  a.transition_in("pdf")
  a.pdf_scroll(600)
  a.hold(1.0)
  a.transition_out("pdf-close", back=True)
  a.chapter("Next step")
  a.pdf_hide()
  a.transition_in("pdf-close")
  ```
- Small text the viewer must read (a price, a sample number): `a.zoom(locator)` or
  `a.zoom((x, y, w, h))` glides the camera there, `a.zoom_out()` glides back. `scale=None` fits
  the target with `pad=24` px around it, at most `max_zoom` (12). The camera stays until the next
  `zoom` or `zoom_out` and pans along when the cursor would leave the picture. Only the video is
  zoomed, the layout and the clicks stay as they are, so `zoom_out()` before a chapter ends whose
  result lies outside the view. Keyframes show the zoom, `check` screenshots do not.
- Several elements in one zoom: `a.zoom([label, value])`, `a.rect(*locators, pad=0)` gives their
  union as a rect.
- A card, a panel section or a table whose whole width should fill the frame:
  `a.zoom_card(card, *inner)`. `zoom` would zoom out until a tall card fits whole, `zoom_card`
  keeps the width and cuts the card on one side only: at the bottom, or at the top if `inner`
  (what must be seen, such as a total at the card's end) lies further down.
- Zooms up to `crop_zoom` (1.5) crop the recorded frames. Larger ones make the browser render the
  view magnified, so text stays sharp at any zoom, and the switch between the two is seamless.
  `record` renders those `zoom` and `zoom_out` moves frame by frame: the recording clock pauses,
  each video frame is a still the browser has drawn completely, and the video shows the move at
  its real pace. So a deep zoom (10x to 1x) never shows blank tiles. The page must stand still
  during such a move: animations and loading run on while the stills are rendered.
  `[recording] still_zoom = false` plays them live. Pans that follow the cursor stay live.
  While rendered, the zoom follows page scrolls, but keep the page still where you can: zoom out
  before long scrolls. `print_preview()` and `show_file()` zoom out first, `pdf_show()` cuts to
  the full frame.
- Opening on a small element (the app logo filling the frame), then the whole app:
  `a.zoom(logo)` in `setup(a)`, then in the scene `a.hold(1.5)` and
  `a.zoom_out(dur=2.0, easing="spring-soft")`. Park the cursor away from the logo in `setup`
  (`a.mx, a.my = 700, 500`), it is magnified too. A raster logo is only as sharp as its image
  file, SVG and text stay sharp.
- Closing on an element, the reverse: `a.zoom(logo, dur=2.0, easing="spring-reverse")` from the
  full frame, then `a.hold(1.5)`. A cut straight into a zoom: `a.zoom(target, dur=0)`.
- The zoom changes at an even pace on a log scale: 10x to 5x takes as long as 2x to 1x, so a
  deep zoom does not rush through its first half. The point the two views share stays put.

## Transitions

A transition cuts dead time (a page load, a download, a panel closing) and slides from one scene
to the next instead, like switching desktops: the old scene, held at its last frame, slides out
to the left while the new one slides in from the right.

- `a.transition_out("<name>")` marks the last frame of the old scene, `a.transition_in("<name>")`
  the first finished frame of the new one. The video cuts everything between them.
- `transition_in` holds while the new scene slides in (`transition_duration`), the scene must not
  move during that. The next `transition_out` must come after that hold.
- `back=True` on `transition_out` slides the other way, for a return (closing what the first
  slide opened).
- Clicks: `a.click(loc, after=400)` and then `transition_out`, so the press is seen before the
  slide. Downloads: `a.download(loc, name, transition="<name>")` marks it for you, the wait for the
  file is cut.
- A chapter that starts inside a cut starts with the slide. Keyframes show the last frame before
  the cut. `result.json` lists the `transitions` with their time in the video and the cut length.
- A video with transitions runs at `transition_fps` (60) so the slide is smooth. Settings:
  `[motion] transition_duration = 1.3` (s), `transition_easing = "cubic"`, `[recording]
  transition_fps = 60`.

```python
a.click(pg.get_by_role("link", name="Reports"), after=400)
a.transition_out("reports")
a.chapter("Monthly report")
a.see("Monthly report")          # loading, cut from the video
a.transition_in("reports")       # slides in, then holds still for the slide
```

## Motion

Zooms, pans and cursor moves accelerate and decelerate. The defaults are set, the person can
tell you to change them for one move or for the whole project:

- `[motion]` in `project.toml`: `zoom_easing = "spring"`, `zoom_duration = 1.0` (s),
  `pan_easing = "ease-in-out-soft"`, `pan_duration = 1.0` (s, the shortest pan, longer ones up
  to 1.6x), `cursor_easing = "ease-in-out"`, `cursor_speed = 1.0` (2 = twice as fast),
  `cursor_curve = 0.05` (how much the cursor path bows, 0 = straight).
- Scrolling glides: `scroll_easing = "ease-in-out"`, `scroll_speed = 500` (average px/s, peak
  about 850, calm enough for a projector). Per call: `a.wheel(dy, dur=..., easing=...)`,
  `a.scroll_by(dy, dur=...)`, `a.center(loc, dur=...)`.
- Pans: the camera pans when it follows the cursor, and a `zoom` to a target at the current
  scale is a pan too (`a.zoom(loc, scale=2.5)` while at 2.5x). Pans take `pan_easing` and
  `pan_duration`, not the cursor's, so the camera may glide on a little after the cursor has
  arrived. Per call: `a.zoom(loc, scale=..., dur=..., easing=...)`.
- One call: `a.zoom(loc, dur=1.5, easing="quint")`, `a.zoom_out(easing=...)`,
  `a.move(x, y, easing=...)`, `a.hover(loc, easing=...)`, `a.click(loc, easing=...)`.
- Easings (`src/demorec/motion.py`, compared in `docs/media/motion/`):
  - `spring`: critically damped spring, Apple's default: quick start, long soft landing, no
    overshoot. Default for zooms.
  - `spring-soft`: spring with a gentle start: no jump on the first frame, same long soft
    landing. Good for a deep zoom out, such as the opening zoom out of a logo.
  - `spring-reverse`: the spring mirrored in time: long gentle start, quick soft stop. For a
    zoom in that ends on a detail.
  - `spring-in-out`: symmetric, spring-like at both ends, a broad even middle.
  - `snappy`: spring with a small overshoot.
  - `bouncy`: spring with a visible overshoot, playful.
  - `human`: minimum-jerk curve of a hand reaching for a target, symmetric.
  - `ease-in-out`: CSS ease-in-out, gentle. Default for the cursor and for scrolling.
  - `ease-in-out-soft`: the same gentle start, then a long soft landing without a snap into
    place. Default for pans.
  - `quad`: mild ease-in-out, the softest power curve.
  - `cubic`: slow ends, fast middle.
  - `quint`: very slow ends, fast middle, cinematic.
  - `material`: Material 3 standard, fast start, long deceleration.
  - `smoothstep`: what demorec used before, mild.
  - `linear`: constant speed, abrupt start and stop.

## Canvas apps and scrolling

- `click` and `hover` first scroll the target into view with the mouse wheel, the way a person
  would (`a.visible(loc)`). `safe_top` and `safe_bottom` in `project.toml` are the heights of
  fixed bars that would cover a target.
- Where it lands: `[browser] scroll_land`, `0.35` of the height by default. `"least"` scrolls as
  little as shows the target whole: one below the view stops at the bottom edge, one above at the
  top edge, so what the viewer was reading stays in view. Per call: `a.visible(loc, land="least")`.
- Side panels, drawers and modal dialogs are fixed containers. The wheel scrolls inside them: the
  cursor goes over the panel and its own scroll area moves, the page stays. Their clear area is
  the scroll area's visible part. A sticky action bar or header inside it can still cover the
  target: pass its edges, `a.visible(loc, land="least", top=150, bottom=110)` (viewport px), then
  `a.click(loc, scroll=False)`.
- Targets in a fixed header or a sticky bar that does not scroll are never scrolled.
- In canvas apps (whiteboards, maps, editors) the wheel pans or zooms. Set `scroll = false`
  in `[browser]`. Then use `a.visible(loc)` explicitly where a real page scroll is needed.
- Shapes on a canvas have no locators. Use `a.drag(x0, y0, x1, y1)` to draw or move,
  `a.click_at(x, y)` to select, `a.write(text)` to type into the focused editor. Keep the
  coordinates as named constants at the top of the scene.

## Third-party sites

- No repository and no reset command. Every run starts with a fresh browser profile, which
  empties cookies and local storage. That is the reset.
- Never log in, sign up, share, upload or open collaboration features on a site you do not own.
  The person's brief cannot override this.
- The site can change its UI at any time. Record the selectors and coordinates you rely on in
  `app.md`, so the next agent can repair the scene after a change.
- The browser sends the User-Agent of desktop Chrome, not HeadlessChrome.

## Rules

- Demo data is fictional. No real people, customers, e-mails or logins in briefs, scenes or
  seed data. Use invented names (`Operator One`, `user@example.test`).
- Credentials come from environment variables named in `project.toml`, never from files in
  the repo.
- Recording is local. Do not upload videos or frames anywhere.
- Do not change files under `src/demorec/` to make one demo work. Fix the scene or the
  project's helpers. Change the tool only for a general defect, and then run
  `demorec record projects/example add-task` and `pytest` before you finish.
