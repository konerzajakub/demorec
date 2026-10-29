"""Frame capture through the Chrome DevTools screencast, then encoding with ffmpeg.

The screencast reads frames from the browser itself, so recording works headless and on a
locked workstation. Each frame keeps its browser timestamp, and the encoder holds every frame
for its real duration, so the video plays at the speed the scene ran. A separate process
(capture.py) receives the frames, so the scene's own work never holds them back."""
import os, shutil, subprocess, sys, time

from .cdp import devtools_port
from .util import NO_WINDOW, log


class Cast:
    def __init__(self, ctx, name, w, h, work_dir, profile=None):
        """w, h: frame size in device pixels. profile: user data folder of a browser started
        with --remote-debugging-port=0."""
        self.ctx, self.name, self.w, self.h, self.profile = ctx, name, w, h, profile
        self.dir = os.path.join(work_dir, "frames", name)
        if os.path.exists(self.dir):
            shutil.rmtree(self.dir)
        os.makedirs(self.dir)
        self.frames = []  # (timestamp, path), filled by stop()
        self.sizes = {}  # (width, height) of captured frames -> count
        self.readers = []  # (process, file prefix), one per attach()
        self.end = None
        self.t0 = None
        self.offset = None  # browser frame clock minus time.time(), they can differ by seconds

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
        self.frames.sort()

    # ------------------------------------------------------------ recording time
    def start(self):
        self.t0 = time.time()
        log("cast start", self.name)

    def stop(self):
        self.end = time.time()
        self._stop_reader()
        self._read_indexes()
        log("cast stop", self.name, len(self.frames), "frames", self.sizes)

    def elapsed(self):
        return time.time() - self.t0 if self.t0 else 0.0

    def _clock(self):
        """t0 and end on the frame clock."""
        o = self.offset or 0.0
        return self.t0 + o, (self.end or time.time()) + o

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

    def _write_concat_list(self, frames, end):
        """ffmpeg concat list that shows each frame until the next one arrives."""
        path = os.path.join(self.dir, "list.txt")
        with open(path, "w", encoding="utf-8") as f:
            for i, (ts, p) in enumerate(frames):
                nxt = frames[i + 1][0] if i + 1 < len(frames) else end
                dur = max(0.001, nxt - ts)
                f.write("file '%s'\nduration %.4f\n" % (p.replace("\\", "/"), dur))
            f.write("file '%s'\n" % frames[-1][1].replace("\\", "/"))
        return path

    def encode(self, dst, ffmpeg, fps=30, crf=20, log_dir=None):
        t0, end = self._clock()
        frames = self._recorded_frames(t0, end)
        if not frames:
            raise RuntimeError("no frames captured")
        lst = self._write_concat_list(frames, end)
        os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
        log_dir = log_dir or self.dir
        # Frames of another size are fitted in with white bars, never stretched.
        vf = ("scale=%d:%d:flags=lanczos:force_original_aspect_ratio=decrease,"
              "pad=%d:%d:(ow-iw)/2:(oh-ih)/2:white,format=yuv420p") % (self.w, self.h, self.w, self.h)
        with open(os.path.join(log_dir, "encode-%s.out.log" % self.name), "wb") as o, \
             open(os.path.join(log_dir, "encode-%s.err.log" % self.name), "wb") as e:
            r = subprocess.run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", lst,
                                "-fps_mode", "cfr", "-r", str(fps), "-vf", vf,
                                "-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-tune", "stillimage",
                                "-movflags", "+faststart", "-an", dst],
                               stdout=o, stderr=e, creationflags=NO_WINDOW)
        if r.returncode != 0:
            raise RuntimeError("ffmpeg failed, see %s" % log_dir)
        log("encoded", dst)

    def cleanup(self):
        self._stop_reader()
        shutil.rmtree(self.dir, ignore_errors=True)
