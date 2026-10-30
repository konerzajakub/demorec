"""Easing curves for the camera and the cursor: how a move speeds up and slows down.

Every curve maps the time fraction u (0 to 1) of a move to the fraction of the distance covered,
0 at the start and exactly 1 at the end. Springs may pass 1 on the way (overshoot). The names are
what `[motion]` in project.toml and the `easing=` argument of `zoom`, `zoom_out`, `move`, `hover`
and `click` accept."""
import math


def _spring(bounce):
    """Spring released from rest, in Apple's duration and bounce terms (WWDC23 "Animate with
    springs"): stiffness (2 pi / duration)^2, damping ratio 1 - bounce. bounce 0 is critically
    damped, no overshoot. The tiny rest it has not covered at the end is blended in, so it lands
    exactly."""
    w0, zeta = 2 * math.pi, 1.0 - bounce

    def x(u):
        if zeta >= 1:
            return 1 - (1 + w0 * u) * math.exp(-w0 * u)
        wd = w0 * math.sqrt(1 - zeta * zeta)
        return 1 - math.exp(-zeta * w0 * u) * (math.cos(wd * u) + zeta * w0 / wd * math.sin(wd * u))

    rest = 1 - x(1.0)
    return lambda u: x(u) + rest * u * u * (3 - 2 * u)


def _bezier(x1, y1, x2, y2):
    """CSS cubic-bezier(x1, y1, x2, y2): solve x(s) = u for s, return y(s)."""
    def coord(s, a, b):
        return 3 * a * s * (1 - s) ** 2 + 3 * b * s * s * (1 - s) + s ** 3

    def slope(s, a, b):
        return 3 * a * (1 - s) ** 2 + 6 * (b - a) * s * (1 - s) + 3 * (1 - b) * s * s

    def f(u):
        s = u
        for _ in range(8):  # Newton, then bisection where the slope is flat
            d = slope(s, x1, x2)
            if abs(d) < 1e-6:
                break
            s = min(max(s - (coord(s, x1, x2) - u) / d, 0.0), 1.0)
        if abs(coord(s, x1, x2) - u) > 1e-6:
            lo, hi = 0.0, 1.0
            for _ in range(40):
                s = (lo + hi) / 2
                lo, hi = (s, hi) if coord(s, x1, x2) < u else (lo, s)
        return coord(s, y1, y2)
    return f


def _in_out(p):
    """Symmetric power curve: easeInOutCubic for p = 3, easeInOutQuint for p = 5."""
    return lambda u: 2 ** (p - 1) * u ** p if u < 0.5 else 1 - (2 - 2 * u) ** p / 2


# name: (curve, one line for AGENTS.md and README)
EASINGS = {
    "spring": (_spring(0.0), "critically damped spring, Apple's default (bounce 0): quick start, long soft landing, no overshoot"),
    "snappy": (_spring(0.2), "spring with a small overshoot (bounce 0.2), lively but calm"),
    "bouncy": (_spring(0.3), "spring with a visible overshoot (bounce 0.3), playful"),
    "human": (lambda u: u * u * u * (10 + u * (6 * u - 15)), "minimum-jerk curve of a human hand reaching for a target (Flash and Hogan 1985), symmetric"),
    "ease-in-out": (_bezier(0.42, 0, 0.58, 1), "CSS ease-in-out, cubic-bezier(.42, 0, .58, 1), gentle"),
    "cubic": (_in_out(3), "easeInOutCubic, slow ends and a fast middle"),
    "quint": (_in_out(5), "easeInOutQuint, very slow ends and a fast middle, cinematic"),
    "material": (_bezier(0.2, 0, 0, 1), "Material 3 standard, cubic-bezier(.2, 0, 0, 1): fast start, long deceleration"),
    "smoothstep": (lambda u: u * u * (3 - 2 * u), "the curve demorec used before, mild ease-in-out"),
    "linear": (lambda u: u, "constant speed, abrupt start and stop, for comparison"),
}
ZOOM_DEFAULT, CURSOR_DEFAULT = "spring", "human"


def curve(name):
    """The easing function called name. Unknown names fail with the list of known ones."""
    if name not in EASINGS:
        raise ValueError("unknown easing %r, use one of: %s" % (name, ", ".join(EASINGS)))
    return EASINGS[name][0]


def ease(name, u):
    """Fraction of the distance covered at time fraction u, 0 before the start, 1 after the end."""
    if u <= 0:
        return 0.0
    if u >= 1:
        return 1.0
    return curve(name)(u)


def arc(x0, y0, x1, y1, e, u, bend):
    """Point at eased fraction e of the way from (x0, y0) to (x1, y1) on a slight arc: the path
    bows to the side by bend times the distance at its middle, like a wrist turning. u is the
    time fraction, the bow fades in and out with sin(pi u), so start and end stay exact."""
    dx, dy = x1 - x0, y1 - y0
    side = bend * math.sin(math.pi * min(max(u, 0.0), 1.0))
    return x0 + dx * e - dy * side, y0 + dy * e + dx * side
