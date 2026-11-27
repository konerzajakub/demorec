"""Actor: drives the page the way a person would, so the recording is easy to follow.

The mouse travels along an eased, slightly curved path, the wheel scrolls at a calm, eased pace,
and text is typed key by key. Every method takes Playwright locators. Pauses (`hold`) are part of
the video. Easings and durations come from [motion] in project.toml (see motion.py)."""
import math, os, time
from pathlib import Path

from .camera import SWITCH_HOLD, Camera, fit, follow
from .motion import arc, curve, ease, pan_duration, scroll_duration, scroll_steps
from .util import log, slug

# The nearest ancestor of e that scrolls vertically (else the page), kept as window.__demorecScroller.
# Returns how far it must scroll so e sits at block: start, center, end or nearest.
SCROLLER_JS = """(e, block) => {
  let s = e.parentElement;
  for (; s && s !== document.body && s !== document.documentElement; s = s.parentElement) {
    const o = getComputedStyle(s).overflowY;
    if (/auto|scroll|overlay/.test(o) && s.scrollHeight > s.clientHeight + 1) break;
  }
  const page = !s || s === document.body || s === document.documentElement;
  if (page) s = document.scrollingElement;
  const r = e.getBoundingClientRect();
  const top = page ? 0 : s.getBoundingClientRect().top + s.clientTop, h = page ? innerHeight : s.clientHeight;
  const d = block === 'start' ? r.top - top : block === 'end' ? r.bottom - top - h
    : block === 'nearest' ? (r.top < top ? r.top - top : r.bottom > top + h ? Math.min(r.bottom - top - h, r.top - top) : 0)
    : r.top + r.height / 2 - top - h / 2;
  window.__demorecScroller = s;
  return Math.max(-s.scrollTop, Math.min(s.scrollHeight - s.clientHeight - s.scrollTop, d));
}"""

# Where e scrolls. {pinned: true} if a fixed or sticky element comes before any scrolling one on
# the way up (a fixed header, a sticky toolbar): scrolling cannot move e. Else the nearest scrolling
# ancestor: {box: [top, bottom, left, right]} of its visible part in the viewport (none for the
# page) and {fixed: true} if it lies in a fixed container (a side panel, a modal dialog).
AREA_JS = """e => {
  let box = null;
  for (let n = e; n && n.nodeType === 1 && n !== document.body && n !== document.documentElement; n = n.parentElement) {
    const s = getComputedStyle(n);
    if (!box && n !== e && /auto|scroll|overlay/.test(s.overflowY) && n.scrollHeight > n.clientHeight + 1) {
      const r = n.getBoundingClientRect(), top = r.top + n.clientTop;
      box = [Math.max(top, 0), Math.min(top + n.clientHeight, innerHeight), Math.max(r.left, 0), Math.min(r.right, innerWidth)];
    }
    if (s.position === 'fixed' || s.position === 'sticky')
      return box ? {box, fixed: true} : {pinned: true};
  }
  return {box, fixed: false};
}"""
TWITCH = 48  # px: a least scroll this short, for a target already whole on screen, is left out


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
        self.camera = Camera(self.w, self.h, cfg.max_zoom)
        self.render = True   # big zooms rendered by the browser. Off in check mode and inspect
        self._cdp = None     # CDP session of the viewport override, see _show()
        self._shown = None   # (view, scrollX, scrollY) the browser renders now
        self.transitions = []  # [{"name", "out", "in", "back"}], see transitions.py

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

    # ------------------------------------------------------------ transitions
    def transition_out(self, name, t=None, back=False):
        """The last frame of the old scene: the video slides from here to transition_in(name),
        the time between is cut. t: seconds on the recording clock, default now. back: a return
        (closing what the slide opened), the slide goes the other way."""
        now = self.cast.elapsed() if self.cast else 0.0
        t = now if t is None else t
        if any(tr["name"] == name for tr in self.transitions):
            raise ValueError("transition %r is marked twice, every transition needs its own name" % name)
        if self.transitions and self.transitions[-1]["in"] is None:
            raise ValueError("transition_out(%r) before transition_in(%r)" % (name, self.transitions[-1]["name"]))
        if self.transitions and t < self.transitions[-1]["in"] + self.cfg.transition_duration * self.speed - 1e-6:
            raise ValueError("transition_out(%r) during the slide of %r, hold longer after transition_in()"
                             % (name, self.transitions[-1]["name"]))
        self.transitions.append({"name": name, "out": round(t, 4), "in": None, "back": back})
        log("transition out %s %.3f%s" % (name, t, " back" if back else ""))

    def transition_in(self, name, hold=True):
        """The first finished frame of the new scene, the slide ends here. hold: wait while the new
        scene slides in ([motion] transition_duration), it has to stand still for that."""
        tr = self.transitions[-1] if self.transitions else None
        if tr is None or tr["name"] != name or tr["in"] is not None:
            raise ValueError("transition_in(%r) without transition_out(%r) before it" % (name, name))
        tr["in"] = round(max(self.cast.elapsed() if self.cast else 0.0, tr["out"]), 4)
        log("transition in %s %.3f" % (name, tr["in"]))
        if hold:
            self.hold(self.cfg.transition_duration + 1.0 / self.cfg.transition_fps)

    def transitions_end(self):
        """Called by the runner after the scene: every transition_out() needs its transition_in()."""
        open_ = [tr["name"] for tr in self.transitions if tr["in"] is None]
        if open_:
            raise ValueError("transition_out(%r) has no transition_in()" % open_[0])

    # ------------------------------------------------------------ timing
    def wait(self, ms):
        """Pause in milliseconds that check mode does not shorten, for the app to react."""
        if not self._rendering():
            self.pg.wait_for_timeout(ms)
            return
        end = time.time() + ms / 1000
        while True:  # the rendered view follows page scrolls while we wait
            self._tick()
            left = end - time.time()
            if left <= 0:
                break
            self.pg.wait_for_timeout(max(1, int(min(left, 0.016) * 1000)))

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

    def move(self, x, y, dur=None, easing=None):
        """Move the cursor to a viewport point. dur in seconds, by default from the distance and
        [motion] cursor_speed. easing: a name from motion.py, default [motion] cursor_easing."""
        x0, y0 = self.mx, self.my
        dist = math.hypot(x - x0, y - y0)
        if dur is None:
            dur = min(0.85, max(0.25, dist / 1300)) / self.cfg.cursor_speed
        easing = easing or self.cfg.cursor_easing
        curve(easing)  # unknown names fail before anything moves
        self.saved += dur * (1 - self.speed)
        dur *= self.speed
        self._follow(x, y, dur)
        n = max(2, int(dur * 60))
        t_start = time.time()
        for k in range(1, n + 1):
            t = k / n
            self.pg.mouse.move(*arc(x0, y0, x, y, ease(easing, t), t, self.cfg.cursor_curve))
            if self._rendering():
                self._tick()
            # Pace by the clock, so a move takes `dur` however slow each step is.
            left = t_start + dur * t - time.time()
            if left > 0:
                self.pg.wait_for_timeout(int(left * 1000))
        self.mx, self.my = x, y
        if self._rendering():
            self._render_until(self.camera.busy_until())  # a pan that outlasts the cursor

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

    def hover(self, loc, fx=0.5, fy=0.5, dx=0, dy=0, scroll=None, easing=None):
        """scroll=None follows `scroll` in project.toml."""
        if self.cfg.scroll if scroll is None else scroll:
            self.visible(loc)
        self.move(*self.point(loc, fx, fy, dx, dy), easing=easing)

    def click(self, loc, fx=0.5, fy=0.5, dx=0, dy=0, scroll=None, after=500, easing=None):
        self.hover(loc, fx, fy, dx, dy, scroll, easing)
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

    # ------------------------------------------------------------ camera
    def zoom(self, target, scale=None, dur=None, pad=24, easing=None):
        """Zoom the video in on a locator or a viewport rect (x, y, w, h), so small text can be
        read. scale=None fits the target with pad px around it, up to max_zoom in project.toml.
        The camera glides there in dur seconds ([motion] zoom_duration) with easing ([motion]
        zoom_easing) and stays until the next zoom() or zoom_out(). Zooms up to crop_zoom crop
        the video, larger ones make the browser render the view magnified, sharp at any zoom.
        The page layout stays as it is. Called in setup(a), the video opens zoomed in.
        Zoomed in, a target at the same scale is a pan: dur and easing then default to
        [motion] pan_duration (growing a little with the distance) and pan_easing."""
        if not isinstance(target, (tuple, list)):
            bb = self.box(target)
            target = (bb["x"], bb["y"], bb["width"], bb["height"])
        self._camera(fit(target, self.w, self.h, pad, scale, self.camera.max_zoom), dur, easing)

    def zoom_out(self, dur=None, easing=None):
        """Glide back to the full frame."""
        self._camera(self.camera.full, dur, easing)

    def _rolling(self):
        return self.cast is not None and self.cast.t0 is not None

    def _now(self):
        return self.cast.elapsed() if self._rolling() else 0.0

    def _rendering(self):
        return self._cdp is not None and self.camera.rendering()

    def _pan(self, aim, to):
        """Default duration of a camera pan from view aim to view to."""
        return pan_duration(math.hypot(to[0] - aim[0], to[1] - aim[1]), aim[2], self.cfg.pan_duration)

    def _camera(self, view, dur, easing):
        cam = self.camera
        aim = cam.moves[-1][3] if cam.moves else cam.full  # where the camera is or is heading
        if aim != cam.full and view != aim and abs(cam.zoom(view) - cam.zoom(aim)) < 1e-6:
            dur = self._pan(aim, view) if dur is None else dur  # same zoom: a pan
            easing = easing or self.cfg.pan_easing
        dur = self.cfg.zoom_duration if dur is None else dur
        easing = easing or self.cfg.zoom_easing
        curve(easing)
        cam, rolling = self.camera, self._rolling()
        t = self._now()
        cur = cam.at(t)
        if self.render and not cam.rendering() and max(cam.zoom(view), cam.zoom(cur)) > self.cfg.crop_zoom + 1e-6:
            # From a cropped zoom the camera stands still while the browser takes over, the
            # encoder drops the frames of that moment (they can show either state).
            hold = SWITCH_HOLD if rolling and cur != cam.full else 0.0
            cam.render_on(t, hold)
            self._show(cur)
            log("camera: the browser renders the zoom from %.2fs" % t)
            if hold:
                self.pg.wait_for_timeout(int(hold * 1000))
                t += hold
        cam.move(t, view, dur if rolling else 0, easing)
        if cam.rendering():
            end = t + (dur if rolling else 0)
            self._render_until(end)
            if view == cam.full:
                cam.render_off(end)
                self._show(cam.full)
                log("camera: cropped again from %.2fs" % end)
        elif rolling:
            self.hold(dur)  # the scene waits, so the viewer sees the camera move

    def _follow(self, x, y, dur):
        """Zoomed in, the camera pans along with a cursor that would leave the picture."""
        if not self.camera.moves or not self._rolling():
            return
        aim = self.camera.moves[-1][3]  # where the camera is or is heading
        if aim != self.camera.full:
            to = follow(aim, x, y, self.w, self.h)
            if to != aim:  # the camera may glide on a little after the cursor has arrived
                self.camera.move(self._now(), to, max(dur, self._pan(aim, to)), self.cfg.pan_easing)

    def _show(self, view):
        """Render mode: the browser draws view (CSS px of the viewport) magnified to the whole
        frame. A viewport override the page never sees: layout, scroll and clicks stay as they
        are. Its x and y are document coordinates times the device scale factor, so they
        follow the page scroll."""
        if self._cdp is None:
            self._cdp = self.pg.context.new_cdp_session(self.pg)
        try:
            sx, sy = self.pg.evaluate("[scrollX, scrollY]")
        except Exception:
            sx, sy = 0, 0  # the page is navigating
        if (view, sx, sy) == self._shown:
            return
        p = {"width": self.w, "height": self.h, "deviceScaleFactor": self.cfg.scale, "mobile": False,
             "screenWidth": self.w, "screenHeight": self.h}
        if view != self.camera.full:
            x, y, w, h = view
            k = self.cfg.scale
            p["viewport"] = {"x": (x + sx) * k, "y": (y + sy) * k, "width": w, "height": h, "scale": self.w / w}
        self._cdp.send("Emulation.setDeviceMetricsOverride", p)
        self._shown = (view, sx, sy)

    def _tick(self):
        """Render mode: bring the rendered view up to date with the camera path and the scroll."""
        self._show(self.camera.at(self._now()))

    def _render_until(self, end):
        """Render mode: play the camera path live until end (recording clock)."""
        while self._rolling() and self._now() < end:
            self._tick()
            self.pg.wait_for_timeout(8)
        self._show(self.camera.at(end))

    # ------------------------------------------------------------ scrolling
    def wheel(self, dy, dur=None, easing=None):
        """Scroll by dy pixels with the mouse wheel at the cursor. Real wheel events, 60 per
        second, small at the start and the end: the page glides. dur in seconds, by default dy
        over [motion] scroll_speed. easing: a name from motion.py, default [motion] scroll_easing."""
        # A focused number input would change its value on wheel instead of scrolling the page.
        self.pg.evaluate("() => { const e = document.activeElement; if (e && e.tagName === 'INPUT' && e.type === 'number') e.blur(); }")
        self._glide(dy, dur, easing, lambda step: self.pg.mouse.wheel(0, step))

    def _glide(self, dist, dur, easing, send):
        """Call send(px) with the eased steps of a dist px scroll, paced by the clock."""
        dist = round(dist)
        if not dist:
            return
        easing = easing or self.cfg.scroll_easing
        curve(easing)  # unknown names fail before anything moves
        if dur is None:
            dur = scroll_duration(dist, self.cfg.scroll_speed)
        self.saved += dur * (1 - self.speed)
        dur *= self.speed
        t_start = time.time()
        for t, step in scroll_steps(dist, dur, easing):
            left = t_start + t - time.time()
            if left > 0:
                self.pg.wait_for_timeout(int(left * 1000))
            send(step)
            if self._rendering():
                self._tick()

    def visible(self, loc, at=None, land=None, top=None, bottom=None):
        """Scroll with the wheel until loc is fully in view. land: where loc lands if it has to
        scroll, a fraction of the height, or "least" for the shortest scroll that shows it whole
        (one below the view stops at the bottom edge, one above at the top edge), default
        [browser] scroll_land. Elements in a fixed header never scroll. Inside a fixed
        container (a side panel, a modal) the cursor goes over the container and its own
        scrollbar moves, top and bottom (viewport px) are then the edges of its clear area, by
        default the container's visible edges."""
        loc = loc.first
        loc.wait_for(state="visible", timeout=20000)
        area = loc.evaluate(AREA_JS)
        if area.get("pinned"):
            return  # inside a fixed or sticky container that does not scroll: scrolling cannot move it
        land = self.cfg.scroll_land if land is None else land
        box, fixed = area.get("box"), area.get("fixed")
        if fixed:
            lo, hi = box[0], box[1]
        else:
            lo, hi = self.cfg.safe_top, self.h - self.cfg.safe_bottom
            if box:
                lo, hi = max(lo, box[0]), min(hi, box[1])
        lo = lo if top is None else top
        hi = hi if bottom is None else self.h - bottom
        if land == "least":
            self._least(loc, at, box, lo, hi, fixed)
        else:
            self._land(loc, at, box, lo, hi, fixed, land)
        self.wait(250)

    def _land(self, loc, at, box, lo, hi, fixed, land):
        """visible() with loc landing at land: one glide, the loop corrects what it missed."""
        anchor, span = (lo + (hi - lo) * land, hi - lo) if fixed else (self.h * land, self.h)
        moved = False
        for _ in range(60):
            bb = loc.bounding_box()
            if bb is None:
                break
            if not moved:
                if self._in_view(bb, lo, hi, page=not fixed):
                    break
                self.move(*(at if at is not None else self._wheel_spot(bb, box)))
                moved = True
            elif abs(bb["y"] - anchor) <= span * 0.12:
                break  # close enough to `land`
            y = bb["y"]
            delta = y - anchor
            step = max(40, min(2 * self.h, abs(delta)))
            self.wheel(step if delta > 0 else -step)
            self.wait(120)
            if self._stuck(loc, y):
                self.center(loc)  # the wheel does not move this container, scroll it directly
                break

    def _least(self, loc, at, box, lo, hi, fixed):
        """visible() with the shortest scroll: one eased glide, a short second one corrects what
        the container's end (or content loaded on the way) left over."""
        for attempt in range(2):
            bb = loc.bounding_box()
            if bb is None or self._in_view(bb, lo, hi, page=not fixed):
                break
            y, tall = bb["y"], min(bb["height"], hi - lo)
            dy = y - lo if y < lo else y + tall - hi
            if abs(dy) < 2:
                break  # a rounding remainder, a zero wheel would look like a container that never scrolls
            edge = box or (0, self.h)
            if abs(dy) < TWITCH and y >= edge[0] and y + bb["height"] <= edge[1]:
                break  # whole on screen, only inside the margin: a twitch of the page helps nobody
            if attempt == 0:
                self.move(*(at if at is not None else self._wheel_spot(bb, box)))
            self.wheel(dy)
            self.wait(150)
            if self._stuck(loc, y):
                self.center(loc, block="nearest")
                break

    def _in_view(self, bb, lo=None, hi=None, page=True):
        """bb is clear of the fixed bars (a tall one at least fills the space between them), or
        lies inside the fixed header."""
        header = self.cfg.fixed_header
        if page and header and bb["y"] >= 0 and bb["y"] + bb["height"] <= header:
            return True
        lo = self.cfg.safe_top if lo is None else lo
        hi = self.h - self.cfg.safe_bottom if hi is None else hi
        return bb["y"] >= lo - 1 and bb["y"] + min(bb["height"], hi - lo) <= hi + 1

    def _wheel_spot(self, bb, box=None):
        """Where the cursor scrolls from: over the target's left part, below the middle, inside
        the scrolling container if there is one (the wheel moves what is under the cursor)."""
        x, y = bb["x"] + min(bb["width"] / 2, 80), self.h * 0.55
        top, bottom, left, right = box or (0, self.h, 0, self.w)
        x = min(max(x, left + 20, 20), right - 30, self.w - 30)
        y = min(max(y, top + 20), bottom - 20)
        return x, y

    def _stuck(self, loc, y):
        """loc is still at y after a wheel step, also on a second look."""
        def now():
            return (loc.bounding_box() or {}).get("y", y)
        if abs(now() - y) >= 1:
            return False
        self.wait(250)
        return abs(now() - y) < 1

    def center(self, loc, block="center", dur=None, easing=None):
        """Scroll loc into view with a script, for containers the wheel does not move. Its nearest
        scrolling container glides like wheel(), outer ones follow with scrollIntoView."""
        loc = loc.first
        dist = loc.evaluate(SCROLLER_JS, block)
        self._glide(dist, dur, easing, lambda step: self.pg.evaluate(
            "d => window.__demorecScroller.scrollBy({top: d, behavior: 'instant'})", step))
        loc.evaluate("(e, b) => e.scrollIntoView({block: b, behavior: 'smooth'})", block)
        self.wait(400)

    def scroll_by(self, dy, at=None, dur=None, easing=None):
        """Wheel-scroll dy pixels, with the cursor at `at` (x, y) if given."""
        if at:
            self.move(*at)
        self.wheel(dy, dur, easing)
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
        print layout instead (what the dialog would preview), then dismiss the print. A zoomed
        camera zooms out first."""
        if self.camera.at(self._now()) != self.camera.full:
            self.zoom_out()
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

    def download(self, loc, name, transition=None, scroll=None):
        """Click loc, save the download under the work dir, return its path. transition: the
        name of a transition_out() marked as the button's press has been seen, so the wait for
        the file is cut from the video."""
        with self.pg.expect_download(timeout=30000) as dl:
            self.click(loc, scroll=scroll, after=400 if transition else 300)
            if transition:
                self.transition_out(transition)
        path = os.path.join(self.cfg.work_dir, "downloads", self.cast.name, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        dl.value.save_as(path)
        if not transition:
            self.wait(1200)
        return path

    def show_file(self, path, scroll_steps=0, hold=3.0):
        """Open a local file (a downloaded PDF) in a new window, show it, return to the app."""
        app = self.pg
        try:
            # A window, not a tab: in new headless Chrome a second tab shrinks the app's frames
            # by the height of a tab strip.
            s = self.ctx.new_cdp_session(app)
            with self.ctx.expect_page(timeout=10000) as ev:
                s.send("Target.createTarget", {"url": "about:blank", "newWindow": True})
            tab = ev.value
            s.detach()
        except Exception:
            tab = self.ctx.new_page()
        self.cast.attach(tab)
        tab.goto(Path(path).resolve().as_uri())
        tab.wait_for_timeout(2500)
        tab.mouse.move(self.w / 2, self.h / 2)
        for _ in range(scroll_steps):
            self._glide(240, None, None, lambda step: tab.mouse.wheel(0, step))
            tab.wait_for_timeout(500)
        tab.wait_for_timeout(int(hold * 1000))
        app.bring_to_front()
        self.cast.attach(app)
        tab.close()
        self.wait(600)
        self.park()
