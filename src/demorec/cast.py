"""Frame capture through the Chrome DevTools screencast, then encoding with ffmpeg.

The screencast reads frames from the browser itself, so recording works headless and on a
locked workstation. Each frame keeps its browser timestamp, and the encoder holds every frame
for its real duration, so the video plays at the speed the scene ran. A separate process
(capture.py) receives the frames, so the scene's own work never holds them back.

The recording clock can pause (pause() and resume()): the time between does not exist in the
video, the screencast frames of it are dropped. Frames rendered one by one in the meantime
(add_still) can fill the span the clock skips ahead on resume(advance)."""
import math, os, shutil, subprocess, sys, time

from .cdp import devtools_port
from .transitions import graph, pairs
from .util import NO_WINDOW, log

TRANSIENT = 0.5  # s: a frame of another size that a frame of the right size follows this soon is dropped
LONGEST = 2.0    # s: a frame held longer is listed several times, ffmpeg never waits on one long entry
STALL = 120      # s without encoding progress before ffmpeg is stopped


class Cast:
    def __init__(self, ctx, name, w, h, work_dir, profile=None, size=None):
        """w, h: frame size in device pixels. size: (width, height) of the video, default w, h.
        profile: user data folder of a browser started with --remote-debugging-port=0."""
        self.ctx, self.name, self.w, self.h, self.profile = ctx, name, w, h, profile
        self.size = size or (w, h)
        self.dir = os.path.join(work_dir, "frames", name)
        if os.path.exists(self.dir):
            shutil.rmtree(self.dir)
        os.makedirs(self.dir)
        self.frames = []  # (timestamp, path), filled by stop()
        self.sizes = {}  # (width, height) of captured frames -> count
        self.frame_size = {}  # path -> (width, height), frames not listed have the size w, h
        self.readers = []  # (process, file prefix), one per attach()
        self.end = None
        self.t0 = None
        self.offset = None  # browser frame clock minus time.time(), they can differ by seconds
        self.pauses = []  # [wall clock start, end, advance]: spans cut from the recording clock, see pause()
        self.stills = []  # (recording time, path): frames rendered one by one, see add_still()

    # ------------------------------------------------------------ capture
    def attach(self, page):
        """Captures from page. Call again after switching tabs."""
        self._stop_reader()
        s = self.ctx.new_cdp_session(page)
        target = s.send("Target.getTargetInfo")["targetInfo"]["targetId"]
        s.detach()
        prefix = "p%d-" % len(self.readers)
        proc = self._start_reader(target, prefix)
        self.readers.append((proc, prefix))
        # Wait for the first frame, so the screen at the start is on record.
        first = os.path.join(self.dir, prefix + "000000.jpg")
        t = time.time()
        while not os.path.exists(first) and time.time() - t < 5 and proc.poll() is None:
            page.wait_for_timeout(50)

    def _start_reader(self, target, prefix):
        """capture.py for one page, its output in <prefix>capture.*.log."""
        logs = [open(os.path.join(self.dir, prefix + x), "wb") for x in ("capture.out.log", "capture.err.log")]
        proc = subprocess.Popen([sys.executable, "-m", "demorec.capture", str(devtools_port(self.profile)), target,
                                 self.dir, prefix, str(self.w), str(self.h)],
                                stdin=subprocess.PIPE, stdout=logs[0], stderr=logs[1], creationflags=NO_WINDOW)
        for f in logs: f.close()
        return proc

    def _stop_reader(self):
        """Closing its stdin tells the running reader to stop."""
        if self.readers and self.readers[-1][0].poll() is None:
            proc = self.readers[-1][0]
            proc.stdin.close()
            try: proc.wait(timeout=10)
            except subprocess.TimeoutExpired: proc.kill()

    def _read_indexes(self):
        """Frames and frame sizes from every reader's index.tsv, sorted by timestamp."""
        self.frames, self.sizes = [], {}
        for _, prefix in self.readers:
            path = os.path.join(self.dir, prefix + "index.tsv")
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8") as f:
                for line in f:
                    ts, wall, w, h, name = line.rstrip("\n").split("\t")
                    ts, wall = float(ts), float(wall)
                    if self.offset is None:
                        self.offset = ts - wall
                    self.frames.append((ts, os.path.join(self.dir, name)))
                    self.sizes[(int(w), int(h))] = self.sizes.get((int(w), int(h)), 0) + 1
                    self.frame_size[self.frames[-1][1]] = (int(w), int(h))
        self.frames.sort()

    # ------------------------------------------------------------ recording time
    def start(self):
        self.t0 = time.time()
        log("cast start", self.name)

    def stop(self):
        if self.pauses and self.pauses[-1][1] is None:
            self.resume()
        self.end = time.time() - self.paused()
        self._stop_reader()
        self._read_indexes()
        self._apply_pauses()
        log("cast stop", self.name, len(self.frames), "frames", self.sizes)

    def elapsed(self):
        """Seconds on the recording clock: since start(), without the paused spans."""
        return time.time() - self.t0 - self.paused() if self.t0 else 0.0

    def pause(self):
        """Stop the recording clock. Until resume(), elapsed() stands still and the screencast
        frames are dropped. For work the video must not show in real time, such as rendering a
        camera move frame by frame (add_still)."""
        if self.pauses and self.pauses[-1][1] is None:
            raise RuntimeError("the recording is already paused")
        self.pauses.append([time.time(), None, 0.0])

    def resume(self, advance=0.0):
        """Run the recording clock again. advance: seconds it skips ahead at once, the span the
        stills added during the pause fill. Without stills there the last frame before holds."""
        self.pauses[-1][1:] = [time.time(), advance]

    def paused(self, wall=None):
        """Seconds the recording clock lags the wall clock at wall (default now): the paused time
        before it, less what resume() skipped ahead. A running pause counts up to wall."""
        wall = time.time() if wall is None else wall
        return sum(min(e if e is not None else wall, wall) - s - (a if e is not None and e <= wall else 0)
                   for s, e, a in self.pauses if s < wall)

    def add_still(self, t, path):
        """A frame rendered by the scene, shown from t seconds on the recording clock until the
        next frame. Its size must be the capture size (w, h)."""
        self.stills.append((t, path))

    def _apply_pauses(self):
        """Screencast frames onto the recording clock: frames inside a pause are dropped, later
        ones move back by the paused time. Then the stills join them."""
        if not self.pauses and not self.stills:
            return
        o = self.offset if self.offset is not None else 0.0
        frames = []
        for ts, p in self.frames:
            wall = ts - o
            if any(s <= wall < e for s, e, _ in self.pauses):
                continue
            frames.append((ts - self.paused(wall), p))
        frames += [(self.t0 + o + t, p) for t, p in self.stills]
        self.frames = sorted(frames)

    def _clock(self):
        """t0 and end on the frame clock."""
        o = self.offset or 0.0
        return self.t0 + o, (self.end or time.time() - self.paused()) + o

    def frame_at(self, t):
        """Path of the last captured frame at or before t seconds into the recording."""
        best = None
        t0, _ = self._clock()
        for ts, p in self.frames:
            if ts - t0 <= t: best = p
            else: break
        return best or (self.frames[0][1] if self.frames else None)

    # ------------------------------------------------------------ encoding
    def _recorded_frames(self, t0, end):
        """Frames from t0 to end. The screencast only sends a frame when the page changes, so the
        last frame before t0 is what the screen shows at the start. It opens the video at t0."""
        before = [f for f in self.frames if f[0] < t0]
        return ([(t0, before[-1][1])] if before else []) + [f for f in self.frames if t0 <= f[0] <= end]

    def _size(self, path):
        return self.frame_size.get(path, (self.w, self.h))

    def _usable_frames(self, frames, camera=None):
        """frames without the ones the video must not show:
        - frames during a camera switch to render mode (Camera.holds) can show either state. The
          last one of them shows the rendered view for sure, it starts at the end of the switch,
          when the encoder stops cropping. The cropped frame before the switch shows until then.
        - a frame of another size that a frame of the right size follows within TRANSIENT, for
          example a new window before the browser applied the viewport to it.
        The frame before a dropped one stays on screen instead."""
        t0, _ = self._clock()
        holds = [(t0 + a, t0 + b) for a, b in camera.holds()] if camera else []
        out = []
        for i, (ts, p) in enumerate(frames):
            span = next(((a, b) for a, b in holds if a <= ts < b), None)
            if out and span:
                if i + 1 < len(frames) and frames[i + 1][0] < span[1]:
                    continue  # not the last frame of the switch
                ts = span[1]
            if out and self._size(p) != (self.w, self.h):
                j = i + 1
                while j < len(frames) and frames[j][0] - ts <= TRANSIENT and self._size(frames[j][1]) != (self.w, self.h):
                    j += 1
                if j < len(frames) and frames[j][0] - ts <= TRANSIENT:
                    continue
            out.append((ts, p))
        return out

    def _fit_frames(self, frames, ffmpeg, log_dir):
        """Frames of another size, fitted into w x h (white bars, never stretched) by one ffmpeg
        run before the encode. The camera filter counts frames, and a frame of a new size would
        restart the filter graph and its count, so the encode must only see one size."""
        odd = list(dict.fromkeys(p for _, p in frames if self._size(p) != (self.w, self.h)))
        if not odd:
            return frames
        fdir = os.path.join(self.dir, "fitted")
        os.makedirs(fdir, exist_ok=True)
        lst = os.path.join(fdir, "list.txt")
        with open(lst, "w", encoding="utf-8") as f:
            f.writelines("file '%s'\n" % p.replace("\\", "/") for p in odd)
        with open(os.path.join(log_dir, "fit-%s.log" % self.name), "wb") as e:
            subprocess.run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", lst, "-fps_mode", "passthrough",
                            "-vf", "scale=%d:%d:flags=lanczos:force_original_aspect_ratio=decrease,"
                                   "pad=%d:%d:(ow-iw)/2:(oh-ih)/2:white" % (self.w, self.h, self.w, self.h),
                            "-q:v", "2", os.path.join(fdir, "%06d.jpg")],
                           stdout=e, stderr=e, creationflags=NO_WINDOW, check=True)
        fitted = {p: os.path.join(fdir, "%06d.jpg" % (i + 1)) for i, p in enumerate(odd)}
        log("fitted", len(odd), "frames of another size")
        return [(ts, fitted.get(p, p)) for ts, p in frames]

    def _write_concat_list(self, frames, end):
        """ffmpeg concat list that shows each frame until the next one arrives."""
        path = os.path.join(self.dir, "list.txt")
        with open(path, "w", encoding="utf-8") as f:
            for i, (ts, p) in enumerate(frames):
                nxt = frames[i + 1][0] if i + 1 < len(frames) else end
                dur = max(0.001, nxt - ts)
                n = int(math.ceil(dur / LONGEST))
                f.write(("file '%s'\nduration %.4f\n" % (p.replace("\\", "/"), dur / n)) * n)
            f.write("file '%s'\n" % frames[-1][1].replace("\\", "/"))
        return path

    def _filters(self, camera=None, t=None):
        """Size and camera for the still frame at t."""
        vf = ["scale=%d:%d:flags=lanczos:force_original_aspect_ratio=decrease,"
              "pad=%d:%d:(ow-iw)/2:(oh-ih)/2:white" % (self.w, self.h, self.w, self.h)]
        if camera:
            vf.append(camera.crop(t, self.w / camera.vw))
        vf.append("scale=%d:%d:flags=lanczos" % self.size)
        return ",".join(f for f in vf if f)

    def encode(self, dst, ffmpeg, fps=30, crf=20, log_dir=None, camera=None, transitions=None, slide=(1.3, "cubic")):
        """Encode the frames from start() to stop() to dst. transitions: the scene's slides (see
        transitions.py), slide: their (duration, easing). Returns the video length in seconds."""
        t0, end = self._clock()
        log_dir = log_dir or self.dir
        frames = self._fit_frames(self._usable_frames(self._recorded_frames(t0, end), camera), ffmpeg, log_dir)
        if not frames:
            raise RuntimeError("no frames captured")
        lst = self._write_concat_list(frames, end)
        os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
        # The fps filter makes the frame rate constant, the camera counts its frames to know the
        # time. round=up: a frame first shows in the first video frame at or after its time, the
        # same rule the camera uses, so a switch to render mode lands on the same video frame.
        # fps would also hold the last frame as long as the one before, -t ends the video.
        vf = ["fps=%d:round=up" % fps]
        cam = camera.filter(self.w / camera.vw, fps, end - t0) if camera else None
        if cam:
            vf.append(cam)
        if self.size != (self.w, self.h):
            vf.append("scale=%d:%d:flags=lanczos" % self.size)
        length = end - t0
        if transitions and pairs(transitions):
            # Cut and slide after the camera: the slide moves the zoomed picture.
            slides, length = graph(transitions, length, fps, *self.size, *slide)
            opt, vf = "filter_complex", "[0:v]%s[c];%s;[v]format=yuv420p[out]" % (",".join(vf), slides)
            map_args = ["-map", "[out]"]
        else:
            opt, vf, map_args = "vf", ",".join(vf + ["format=yuv420p"]), []
        if len(vf) > 20000:  # a long camera path would outgrow the Windows command line (32k)
            path = os.path.join(self.dir, "filters.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(vf)
            vf_args = ["-/" + opt, path]  # ffmpeg 7+ reads the option from the file
        else:
            vf_args = ["-" + opt, vf]
        cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", lst,
               "-fps_mode", "cfr", "-r", str(fps), *vf_args, *map_args, "-t", "%.3f" % length,
               "-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-tune", "stillimage",
               "-movflags", "+faststart", "-an", dst]
        run_watched(cmd, os.path.join(log_dir, "encode-%s" % self.name))
        log("encoded", dst)
        return length

    def still(self, t, dst, ffmpeg, camera=None):
        """The frame at t seconds as the video shows it, saved as JPEG. False without frames."""
        src = self.frame_at(t)
        if not src:
            return False
        if (self.w, self.h) == self.size == self._size(src) and not (camera and camera.crop(t, 1)):
            shutil.copy(src, dst)  # most frames: no camera, no resize, keep the original bytes
            return True
        subprocess.run([ffmpeg, "-y", "-v", "error", "-i", src, "-vf", self._filters(camera, t=t), "-q:v", "2", dst],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=NO_WINDOW, check=True)
        return True

    def cleanup(self):
        self._stop_reader()
        shutil.rmtree(self.dir, ignore_errors=True)


def run_watched(cmd, log_base, stall=STALL):
    """Run ffmpeg with its output in <log_base>.out.log and .err.log. Stops it when its progress
    report stays the same for stall seconds, so a stuck encode fails instead of hanging."""
    progress = log_base + ".progress.log"
    cmd = cmd[:1] + ["-progress", progress] + cmd[1:]
    with open(log_base + ".out.log", "wb") as o, open(log_base + ".err.log", "wb") as e:
        proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=o, stderr=e, creationflags=NO_WINDOW)
        last, since = -1, time.time()
        while proc.poll() is None:
            time.sleep(0.5)
            size = os.path.getsize(progress) if os.path.exists(progress) else 0
            if size != last:
                last, since = size, time.time()
            elif time.time() - since > stall:
                proc.kill()
                proc.wait()
                raise RuntimeError("ffmpeg made no progress for %d s and was stopped, see %s.err.log" % (stall, log_base))
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg failed, see %s.err.log" % log_base)
