"""Scene transitions: the video slides from one scene to the next, like switching desktops.

The scene marks the last frame of the old scene with Actor.transition_out(name) and the first
finished frame of the new one with Actor.transition_in(name). The encoder cuts the time between
the two marks (a page load, a download, a panel closing) and, over `duration` seconds, slides the
old scene, held at its last frame, out to the left while the new one slides in from the right.
`back` slides the other way, for a return. Chapter times move back by the cut time, a chapter
that starts inside a cut starts with the slide.

A transition is a dict {"name", "out", "in", "back"}, times in seconds on the recording clock."""
from .motion import ease

BACKGROUND = "0x1e1e1e"  # shows only where a spring easing overshoots


def pairs(transitions):
    """The finished transitions, sorted by time."""
    return sorted((t for t in transitions if t.get("in") is not None), key=lambda t: t["out"])


def cut_total(transitions):
    return sum(t["in"] - t["out"] for t in pairs(transitions))


def remap(t, transitions):
    """Time t of the recording in the video: cuts before it are taken out, a time inside a cut
    becomes the start of its slide."""
    cut = 0.0
    for tr in pairs(transitions):
        a, b = tr["out"], tr["in"]
        if t <= a:
            break
        if t < b:
            return a - cut
        cut += b - a
    return t - cut


def shown(t, transitions):
    """Time t of the recording, or the out mark of the cut it lies in: the last frame the video
    shows before it. For keyframes, which come from the recorded frames."""
    for tr in pairs(transitions):
        if tr["out"] < t < tr["in"]:
            return tr["out"]
    return t


def check(transitions, duration):
    """Raise ValueError when slides overlap: the next out mark must come after the slide of the
    one before (its in mark plus duration)."""
    end = 0.0
    for tr in pairs(transitions):
        if tr["out"] < end - 1e-6:
            raise ValueError("transition %r starts %.2f s before the slide before it ends, hold longer after "
                             "transition_in()" % (tr["name"], end - tr["out"]))
        if tr["in"] < tr["out"]:
            raise ValueError("transition %r: transition_in() before transition_out()" % tr["name"])
        end = tr["in"] + duration


def _tree(values, var):
    """Balanced if() expression over var (0, 1, 2 ...) that is values[var], short for long lists."""
    runs = []
    for i, v in enumerate(values):
        if runs and runs[-1][1] == v:
            continue
        runs.append((i, v))

    def node(lo, hi):
        if hi - lo == 1:
            return "%.5f" % runs[lo][1]
        mid = (lo + hi) // 2
        return "if(lt(%s,%d),%s,%s)" % (var, runs[mid][0], node(lo, mid), node(mid, hi))
    return node(0, len(runs))


def fractions(duration, fps, easing):
    """The eased fraction of the slide in each of its frames, frame n at n / fps seconds."""
    n = max(1, round(duration * fps))
    return [round(ease(easing, k / n), 5) for k in range(n)]


def graph(transitions, length, fps, w, h, duration=1.3, easing="cubic", src="c", dst="v"):
    """filter_complex part that cuts and slides the [src] stream (constant fps, length seconds,
    w x h px) into [dst]. Returns (filters, output length in seconds)."""
    trs = pairs(transitions)
    check(trs, duration)
    frame = 1.0 / fps
    segs, cur = [], 0.0
    for tr in trs:
        if tr["out"] - cur > frame / 2:
            segs.append(("keep", cur, tr["out"], False))
        segs.append(("slide", tr["out"], tr["in"], tr.get("back", False)))
        cur = tr["in"] + duration
    if length - cur > frame / 2:
        segs.append(("keep", cur, length, False))
    e = _tree(fractions(duration, fps, easing), "n")
    n_src = sum(1 if s[0] == "keep" else 2 for s in segs)
    f = ["[%s]split=%d%s" % (src, n_src, "".join("[s%d]" % i for i in range(n_src)))]
    labels, i = [], 0
    for j, (kind, x, y, back) in enumerate(segs):
        if kind == "keep":
            f.append("[s%d]trim=start=%.4f:end=%.4f,setpts=PTS-STARTPTS[k%d]" % (i, x, y, j))
            i += 1
            labels.append("[k%d]" % j)
            continue
        # The old scene's last frame, held. The new scene plays on as it slides in, so the scene
        # holds still after transition_in().
        f.append("[s%d]trim=start=%.4f:end=%.4f,setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration=%g,"
                 "trim=duration=%g[a%d]" % (i, max(0.0, x - frame), x, duration, duration, j))
        f.append("[s%d]trim=start=%.4f:end=%.4f,setpts=PTS-STARTPTS[b%d]" % (i + 1, y, y + duration, j))
        f.append("color=c=%s:s=%dx%d:r=%d:d=%g[g%d]" % (BACKGROUND, w, h, fps, duration, j))
        sign = -1 if back else 1  # forward: the old scene leaves to the left, the new one comes from the right
        f.append("[g%d][b%d]overlay=x='%d*W*(1-(%s))':y=0:eval=frame:shortest=1[n%d]" % (j, j, sign, e, j))
        f.append("[n%d][a%d]overlay=x='%d*W*(%s)':y=0:eval=frame:shortest=1[k%d]" % (j, j, -sign, e, j))
        i += 2
        labels.append("[k%d]" % j)
    f.append("%sconcat=n=%d:v=1:a=0[%s]" % ("".join(labels), len(labels), dst))
    return ";".join(f), length - cut_total(trs)
