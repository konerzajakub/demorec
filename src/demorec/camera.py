"""Camera: zooms the video in on a part of the page, like a screen-recording editor.

The page layout is never changed, so the clicks stay where they are. The actor records where the
camera looks and when. A view is a rect (x, y, w, h) in CSS px with the viewport's aspect ratio.
Two ways to show a view:

- crop: Cast.encode crops every recorded frame to the view and scales it back up. Exact timing,
  cheap, but the frames only have `scale` device px per CSS px, so big zooms get blurry.
- render: the browser itself renders the view magnified (a viewport override, see Actor), so text
  stays sharp at any zoom. The frames arrive already zoomed and the encoder leaves them alone.

Zooms up to crop_zoom use crop. A move that goes past it switches to render and stays there
until the camera is back at the full frame."""
import math

from .motion import ZOOM_DEFAULT, ease

SWITCH_HOLD = 0.15  # s the camera stands still while a zoomed crop view becomes a rendered one


def fit(rect, vw, vh, pad=24, scale=None, max_zoom=12.0):
    """View that frames rect (x, y, w, h) with pad px around it, inside the vw x vh viewport.
    scale=None zooms as far as rect fits. The zoom stays between 1 and max_zoom."""
    x, y, w, h = rect
    if scale is None:
        scale = min(vw / max(w + 2 * pad, 1), vh / max(h + 2 * pad, 1))
    z = min(max(scale, 1.0), max_zoom)
    cw, ch = vw / z, vh / z
    return (min(max(x + w / 2 - cw / 2, 0), vw - cw), min(max(y + h / 2 - ch / 2, 0), vh - ch), cw, ch)


def follow(view, x, y, vw, vh, margin=0.1):
    """view shifted as little as possible so the point (x, y) lies inside it, margin (fraction of
    the view) away from its edges."""
    vx, vy, w, h = view
    mx, my = w * margin, h * margin
    nx = min(max(min(max(vx, x + mx - w), x - mx), 0), vw - w)
    ny = min(max(min(max(vy, y + my - h), y - my), 0), vh - h)
    return (nx, ny, w, h)


def progress(a, b, e):
    """Fraction of the way from view a to view b at eased time e. The zoom changes at an even
    pace (on a log scale), and a point both views share stays put on screen."""
    r = b[2] / a[2]
    return e if abs(r - 1) < 1e-9 else (r ** e - 1) / (r - 1)


class Camera:
    def __init__(self, vw, vh, max_zoom=12.0):
        self.vw, self.vh, self.max_zoom = vw, vh, max_zoom
        self.full = (0.0, 0.0, float(vw), float(vh))
        self.moves = []   # (start, dur, from view, to view, easing), seconds on the recording clock
        self.render = []  # [start, hold, end or None]: the browser renders the view, see the module doc

    def zoom(self, view):
        return self.vw / view[2]

    def _clamp(self, v):
        """A spring that overshoots must not zoom out past the full frame or leave the page."""
        x, y, w, h = v
        if w >= self.vw:
            return self.full
        return (min(max(x, 0.0), self.vw - w), min(max(y, 0.0), self.vh - h), w, h)

    def at(self, t):
        """The view at t seconds into the recording."""
        view = self.full
        for s, d, a, b, easing in self.moves:
            if t < s:
                break
            if t >= s + d:
                view = b
            else:
                f = progress(a, b, ease(easing, (t - s) / d))
                view = self._clamp(tuple(p + (q - p) * f for p, q in zip(a, b)))
        return view

    def move(self, t, view, dur, easing=ZOOM_DEFAULT):
        """Glide from wherever the camera is at t to view, in dur seconds."""
        self.moves.append((t, dur, self.at(t), tuple(float(v) for v in view), easing))

    def busy_until(self):
        """End of the last move, 0 without moves."""
        return max((s + d for s, d, *_ in self.moves), default=0.0)

    # ------------------------------------------------------------ render mode
    def render_on(self, t, hold=0.0):
        self.render.append([t, hold, None])

    def render_off(self, t):
        self.render[-1][2] = t

    def rendering(self):
        return bool(self.render) and self.render[-1][2] is None

    def holds(self):
        """(start, end) spans whose frames the encoder drops, keeping the frame before: the browser
        switches to rendering the view during them, and frames can show either state."""
        return [(s, s + h) for s, h, _ in self.render if h > 0]

    def crop_at(self, t):
        """The view the encoder crops at t: the full frame while the browser renders the zoom."""
        for s, h, e in self.render:
            if s + h <= t and (e is None or t < e):
                return self.full
        return self.at(t)

    # ------------------------------------------------------------ ffmpeg
    def crops(self, k, fps, duration):
        """[[first frame, last frame + 1, (left, top, right, bottom)]] of the video in device px
        (k per CSS px), one entry per run of frames with the same crop. Frame n shows t = n / fps."""
        runs = []
        for n in range(int(math.ceil(duration * fps)) + 1):
            x, y, w, h = self.crop_at(n / fps)
            c = tuple(round(v * k, 2) for v in (x, y, x + w, y + h))
            if runs and runs[-1][2] == c:
                runs[-1][1] = n + 1
            else:
                runs.append([n, n + 1, c])
        return runs

    def filter(self, k, fps, duration):
        """perspective filter that applies the camera to a stream at fps frames per second whose
        frames have k device px per CSS px, None if the video is never cropped.

        perspective only knows the frame number `in` (from 1). Its value per frame comes from a
        balanced if() tree over the runs of crops(): any easing works, and the tree stays shallow
        for long videos. The frame number is only right if the filter graph never restarts, so
        every frame must have one size before this filter (Cast.encode makes sure)."""
        runs = self.crops(k, fps, duration)
        full = tuple(round(v * k, 2) for v in (0, 0, self.vw, self.vh))
        if all(c == full for _, _, c in runs):
            return None

        def tree(lo, hi, i):
            if hi - lo == 1:
                return "%.2f" % runs[lo][2][i]
            mid = (lo + hi) // 2
            return "if(lt(in,%d),%s,%s)" % (runs[mid][0] + 1, tree(lo, mid, i), tree(mid, hi, i))

        left, top, right, bottom = (tree(0, len(runs), i) for i in range(4))
        corners = [(left, top), (right, top), (left, bottom), (right, bottom)]
        opts = ["%s%d='%s'" % (axis, i, e) for i, xy in enumerate(corners) for axis, e in zip("xy", xy)]
        # Timeline: only frames that are cropped pay for the filter. t is exact here.
        spans = []
        for a, b, c in runs:
            if c == full:
                continue
            if spans and spans[-1][1] == a:
                spans[-1][1] = b
            else:
                spans.append([a, b])
        on = "+".join("between(t,%.4f,%.4f)" % ((a - 0.5) / fps, (b - 0.5) / fps) for a, b in spans)
        return "perspective=%s:interpolation=cubic:eval=frame:enable='%s'" % (":".join(opts), on)

    def crop(self, t, k):
        """crop filter for a still frame at t, None if the view is the full frame."""
        x, y, w, h = self.crop_at(t)
        if (x, y, w, h) == self.full:
            return None
        return "crop=%d:%d:%d:%d" % (round(w * k), round(h * k), round(x * k), round(y * k))
