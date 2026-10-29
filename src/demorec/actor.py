"""Actor: drives the page the way a person would, so the recording is easy to follow.

The mouse travels along an eased path, the wheel scrolls in small steps, and text is typed key
by key. Every method takes Playwright locators. Pauses (`hold`) are part of the video."""
import math, os, time
from pathlib import Path

from .util import log, slug

# True if e or one of its ancestors is position fixed or sticky.
FIXED_JS = """e => { for (let n = e; n && n.nodeType === 1; n = n.parentElement) {
  const p = getComputedStyle(n).position; if (p === 'fixed' || p === 'sticky') return true; } return false; }"""


class Actor:
    """What a scene gets as `a`. `a.pg` is the Playwright page, for waits and reads."""

    def __init__(self, ctx, pg, cast, cfg):
        self.ctx, self.pg, self.cast, self.cfg = ctx, pg, cast, cfg
        self.w, self.h = cfg.width, cfg.height
        self.mx, self.my = self.w * 0.62, self.h * 0.45
        self.speed = 1.0     # check mode sets this low so a scene runs in seconds
        self.saved = 0.0     # seconds check mode skipped, to estimate the real duration
        self.shot_dir = None # check mode: screenshot at the end of every chapter
        self.chapters = []   # [{"title", "start"}], seconds from the start of the recording

    # ------------------------------------------------------------ structure
    def chapter(self, title):
        """Start a chapter. Use one per key moment of the demo brief, with the same title.
        Chapters become the video's chapter list and its keyframes for review."""
        self.chapter_end()
        t = self.cast.elapsed() if self.cast else 0.0
        self.chapters.append({"title": title, "start": round(t, 2)})
        log("chapter", "%.1fs" % t, title)

    def chapter_end(self):
        """Check mode: screenshot of the running chapter's final state. Called by chapter() and
        by the runner after the scene."""
        if self.shot_dir and self.chapters and "screenshot" not in self.chapters[-1]:
            n = "%02d-%s.png" % (len(self.chapters), slug(self.chapters[-1]["title"]))
            self.pg.screenshot(path=os.path.join(self.shot_dir, n))
            self.chapters[-1]["screenshot"] = "check/" + n

    # ------------------------------------------------------------ timing
    def wait(self, ms):
        """Pause in milliseconds that check mode does not shorten, for the app to react."""
        self.pg.wait_for_timeout(ms)

    def hold(self, s=2.0):
        """Pause so the viewer can read the screen."""
        self.saved += s * (1 - self.speed)
        self.wait(int(s * 1000 * self.speed))

    def settle(self, ms=500):
        """Wait for network silence, then a short pause."""
        try: self.pg.wait_for_load_state("networkidle", timeout=8000)
        except Exception: pass
        self.wait(ms)

    # ------------------------------------------------------------ mouse
    def park(self):
        """Show the cursor again at its last position, needed after a page navigation."""
        self.pg.mouse.move(self.mx, self.my)

    def move(self, x, y, dur=None):
        """Move the cursor to a viewport point. dur in seconds, by default from the distance."""
        x0, y0 = self.mx, self.my
        dist = math.hypot(x - x0, y - y0)
        if dur is None:
            dur = min(0.85, max(0.25, dist / 1300))
        self.saved += dur * (1 - self.speed)
        dur *= self.speed
        n = max(2, int(dur * 50))
        t_start = time.time()
        for k in range(1, n + 1):
            t = k / n
            e = t * t * (3 - 2 * t)
            self.pg.mouse.move(x0 + (x - x0) * e, y0 + (y - y0) * e)
            # Pace by the clock, so a move takes `dur` however slow each step is.
            left = t_start + dur * t - time.time()
            if left > 0:
                self.pg.wait_for_timeout(int(left * 1000))
        self.mx, self.my = x, y

    def box(self, loc, timeout=20000):
        """Bounding box of the first match, once it is visible."""
        loc = loc.first
        loc.wait_for(state="visible", timeout=timeout)
        bb = loc.bounding_box()
        if bb is None:
            raise RuntimeError("element has no bounding box")
        return bb

    def point(self, loc, fx=0.5, fy=0.5, dx=0, dy=0):
        """Point inside loc. fx and fy are fractions of its width and height."""
        bb = self.box(loc)
        return bb["x"] + bb["width"] * fx + dx, bb["y"] + bb["height"] * fy + dy

    def hover(self, loc, fx=0.5, fy=0.5, dx=0, dy=0, scroll=None):
        """scroll=None follows `scroll` in project.toml."""
        if self.cfg.scroll if scroll is None else scroll:
            self.visible(loc)
        self.move(*self.point(loc, fx, fy, dx, dy))

    def click(self, loc, fx=0.5, fy=0.5, dx=0, dy=0, scroll=None, after=500):
        self.hover(loc, fx, fy, dx, dy, scroll)
        self._press(after)

    def click_at(self, x, y, after=400):
        """Click a viewport point, for canvas apps where shapes have no locator."""
        self.move(x, y)
        self._press(after)

    def _press(self, after):
        """Click where the cursor is, slow enough that the viewer sees it land first."""
        self.wait(150)
        self.pg.mouse.down(); self.wait(70); self.pg.mouse.up()
        self.wait(after)

    def drag(self, x0, y0, x1, y1, dur=0.9, after=500):
        """Press at (x0, y0), move visibly to (x1, y1), release. Drawing, resizing, drag and drop."""
        self.move(x0, y0)
        self.wait(150)
        self.pg.mouse.down(); self.wait(80)
        self.move(x1, y1, dur=dur)
        self.wait(80)
        self.pg.mouse.up()
        self.wait(after)

    # ------------------------------------------------------------ scrolling
    def wheel(self, dy):
        """Scroll by dy pixels in wheel steps of 40 at the cursor."""
        # A focused number input would change its value on wheel instead of scrolling the page.
        self.pg.evaluate("() => { const e = document.activeElement; if (e && e.tagName === 'INPUT' && e.type === 'number') e.blur(); }")
        for _ in range(max(1, int(abs(dy) / 40))):
            self.pg.mouse.wheel(0, 40 if dy > 0 else -40)
            self.pg.wait_for_timeout(16)

    def visible(self, loc, at=None, land=0.35):
        """Scroll with the wheel until loc is fully in view. If it has to scroll, loc lands at
        `land` (fraction of viewport height). Elements in the fixed header never scroll."""
        loc = loc.first
        loc.wait_for(state="visible", timeout=20000)
        if loc.evaluate(FIXED_JS):
            return  # inside a fixed or sticky container: scrolling cannot move it
        moved = False
        for _ in range(60):
            bb = loc.bounding_box()
            if bb is None:
                break
            if not moved:
                if self._in_view(bb):
                    break
                self.move(*(at if at is not None else self._wheel_spot(bb)))
                moved = True
            elif self.h * (land - 0.12) <= bb["y"] <= self.h * (land + 0.12):
                break  # close enough to `land`
            y = bb["y"]
            delta = y - self.h * land
            step = max(40, min(240, abs(delta)))
            self.wheel(step if delta > 0 else -step)
            self.wait(120)
            if self._stuck(loc, y):
                self.center(loc)  # the wheel does not move this container, scroll it directly
                break
        self.wait(250)

    def _in_view(self, bb):
        """bb is clear of the fixed bars (a tall one at least fills the space between them), or
        lies inside the fixed header."""
        header = self.cfg.fixed_header
        if header and bb["y"] >= 0 and bb["y"] + bb["height"] <= header:
            return True
        lo, hi = self.cfg.safe_top, self.h - self.cfg.safe_bottom
        return bb["y"] >= lo and bb["y"] + min(bb["height"], hi - lo) <= hi

    def _wheel_spot(self, bb):
        """Where the cursor scrolls from: over the target's left part, below the middle."""
        return min(max(bb["x"] + min(bb["width"] / 2, 80), 20), self.w - 30), self.h * 0.55

    def _stuck(self, loc, y):
        """loc is still at y after a wheel step, also on a second look."""
        def now():
            return (loc.bounding_box() or {}).get("y", y)
        if abs(now() - y) >= 1:
            return False
        self.wait(250)
        return abs(now() - y) < 1

    def center(self, loc, block="center"):
        """Scroll loc into view with a script, for containers the wheel does not move."""
        loc.first.evaluate("(e, b) => e.scrollIntoView({block: b, behavior: 'smooth'})", block)
        self.wait(900)

    def scroll_by(self, dy, at=None):
        """Wheel-scroll dy pixels, with the cursor at `at` (x, y) if given."""
        if at:
            self.move(*at)
        self.wheel(dy)
        self.wait(400)

    # ------------------------------------------------------------ keyboard and forms
    def type(self, loc, text, clear=False, delay=75, fx=0.5):
        """Click into a field and type. Retypes if the app reformatted or dropped keys."""
        self.click(loc, fx=fx, after=200)
        if clear:
            self.pg.keyboard.press("ControlOrMeta+A"); self.wait(150)
        self.pg.keyboard.type(text, delay=delay)
        self.wait(300)
        for _ in range(2):
            try: v = loc.first.input_value(timeout=2000)
            except Exception: return
            if v == text or v.replace("\u00a0", " ") == text:  # apps that format with non-breaking spaces
                return
            log("retype", repr(v), "->", repr(text))
            loc.first.focus(); self.pg.keyboard.press("ControlOrMeta+A"); self.wait(150)
            self.pg.keyboard.type(text, delay=delay); self.wait(400)

    def write(self, text, delay=75, after=300):
        """Type into whatever has focus, for editors without a locator (canvas text, rich text)."""
        self.pg.keyboard.type(text, delay=delay)
        self.wait(after)

    def choose(self, combo, option, exact=True, after=600, fx=0.6):
        """Open a combobox and click an option (ARIA role "option")."""
        self.click(combo, fx=fx, after=600)
        opt = self.pg.get_by_role("option", name=option, exact=exact).first
        opt.wait_for(state="visible", timeout=10000)
        opt.scroll_into_view_if_needed(); self.wait(250)
        self.click(opt, fx=0.3, scroll=False, after=after)

    def key(self, k, after=300):
        """Press a key or a chord, e.g. "Enter", "ControlOrMeta+A"."""
        self.pg.keyboard.press(k)
        self.wait(after)

    def see(self, text, scope=None, exact=False, timeout=20000):
        """Wait until text is visible. Returns its locator."""
        loc = (scope or self.pg).get_by_text(text, exact=exact).first
        loc.wait_for(state="visible", timeout=timeout)
        return loc

    def dialog(self):
        """The last dialog in the page, usually the one just opened. Scope locators to it."""
        return self.pg.get_by_role("dialog").last

    # ------------------------------------------------------------ browser level
    def print_preview(self, wait_for=None, show=3.5, zoom=2.5):
        """The browser print dialog is outside the page and cannot be captured. Show the page in
        print layout instead (what the dialog would preview), then dismiss the print."""
        self.wait(800)
        if wait_for:
            self.pg.locator(wait_for).wait_for(state="attached", timeout=10000)
        self.pg.emulate_media(media="print")
        cdp = self.ctx.new_cdp_session(self.pg)
        cdp.send("Emulation.setPageScaleFactor", {"pageScaleFactor": zoom})
        self.wait(int(show * 1000))
        cdp.send("Emulation.setPageScaleFactor", {"pageScaleFactor": 1})
        cdp.detach()
        self.pg.emulate_media(media="screen")
        self.pg.evaluate("dispatchEvent(new Event('afterprint'))")
        self.wait(800)
        self.park()

    def download(self, loc, name):
        """Click loc, save the download under the work dir, return its path."""
        with self.pg.expect_download(timeout=30000) as dl:
            self.click(loc, after=300)
        path = os.path.join(self.cfg.work_dir, "downloads", self.cast.name, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        dl.value.save_as(path)
        self.wait(1200)
        return path

    def show_file(self, path, scroll_steps=0, hold=3.0):
        """Open a local file (a downloaded PDF) in a new tab, show it, return to the app tab."""
        app = self.pg
        tab = self.ctx.new_page()
        self.cast.attach(tab)
        tab.goto(Path(path).resolve().as_uri())
        tab.wait_for_timeout(2500)
        tab.mouse.move(self.w / 2, self.h / 2)
        for _ in range(scroll_steps):
            for _ in range(6):
                tab.mouse.wheel(0, 40); tab.wait_for_timeout(16)
            tab.wait_for_timeout(500)
        tab.wait_for_timeout(int(hold * 1000))
        app.bring_to_front()
        self.cast.attach(app)
        tab.close()
        self.wait(600)
        self.park()
