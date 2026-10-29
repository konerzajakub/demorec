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
- A chapter ends where the next one starts. Wait for its result (`a.see(...)`) and hold before
  the next `chapter()` call, so the keyframe shows the outcome.
- Things that disappear on their own (notifications, toasts) must be visible at the chapter's end.
- Put preparation the viewer must not see (navigation, creating data) into `setup(a)`.
- To inspect a state that only exists after some steps (an open panel, a selected item), create
  a scratch demo whose name starts with `_` (`new-demo <project> _probe`), put the steps into its
  `setup(a)` and run `inspect <project> --demo _probe`. `list` and the tests skip `_` demos.
  Delete it when done.
- Native `<select>` and file pickers are drawn by the OS and are not captured. Show the click,
  then set the value with Playwright (see `projects/example/helpers.py`).
- The browser print dialog is not captured. Use `a.print_preview()`.
- Downloads: `a.download(locator, name)` returns the path, `a.show_file(path)` shows it in a tab.

## Canvas apps and scrolling

- `click` and `hover` first scroll the target into view with the mouse wheel, the way a person
  would. Targets inside fixed or sticky containers are never scrolled. `safe_top` and
  `safe_bottom` in `project.toml` are the heights of fixed bars that would cover a target.
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
