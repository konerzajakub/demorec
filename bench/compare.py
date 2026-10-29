"""Comparison grid video and a sped-up GIF of a finished comparison.

    python bench/compare.py docs/bench/2026-10-26-bread-and-butter \
        opus-5.5 gpt-6.1-sol sonnet-5.5 gpt-6.1-terra haiku-5.5 gpt-6-luna

Two columns, filled row by row, so each row pairs one Claude and one GPT model of the same
tier. Each tile is one model's video at half size with its name in the corner. Shorter videos
hold their last frame. Writes comparison.mp4 at full speed and comparison-3x.gif.
"""
import argparse, json, os, subprocess, sys

LABELS = {"claude-opus-5-5": "Claude Opus 5.5", "claude-sonnet-5-5": "Claude Sonnet 5.5",
          "claude-haiku-5-5": "Claude Haiku 5.5", "gpt-6.1-sol": "GPT-6.1 sol",
          "gpt-6.1-terra": "GPT-6.1 Terra", "gpt-6-luna": "GPT-6 Luna"}
# drawtext font: a file on Windows, a fontconfig name elsewhere
FONT = "fontfile='C\\:/Windows/Fonts/arialbd.ttf'" if sys.platform == "win32" else "font=DejaVuSans-Bold"


def probe(path, entry):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", entry,
                        "-of", "csv=p=0", path], capture_output=True, text=True, check=True)
    return r.stdout.strip().split(",")


def model_label(run_dir, run):
    with open(os.path.join(run_dir, "result.json"), encoding="utf-8") as f:
        model = json.load(f).get("model", run)
    return LABELS.get(model, model)


def tile(i, label, tw, th, longest):
    """Filter for input i: scaled to the tile, held to the longest video, label at the bottom left."""
    size = round(th / 16)
    return ("[%d:v]scale=%d:%d:flags=lanczos,tpad=stop_mode=clone:stop_duration=%.2f,"
            "drawtext=%s:text='%s':fontsize=%d:fontcolor=white:box=1:boxcolor=0x333a40@0.95:"
            "boxborderw=%d:x=%d:y=h-th-%d[v%d]"
            % (i, tw, th, longest, FONT, label, size, round(size / 3), round(size / 3), round(size / 2), i))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bench_dir")
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--demo", default="bread-and-butter")
    ap.add_argument("--speed", type=int, default=3)
    a = ap.parse_args()
    d = os.path.abspath(a.bench_dir)
    videos = [os.path.join(d, r, a.demo + ".mp4") for r in a.runs]
    w, h = (int(x) for x in probe(videos[0], "stream=width,height"))
    tw, th = w // 2, h // 2
    longest = max(float(probe(v, "format=duration")[0]) for v in videos)
    n = len(a.runs)
    tiles = [tile(i, model_label(os.path.join(d, r), r), tw, th, longest) for i, r in enumerate(a.runs)]
    layout = "|".join("%d_%d" % (i % 2 * tw, i // 2 * th) for i in range(n))
    graph = (";".join(tiles) + ";" + "".join("[v%d]" % i for i in range(n))
             + "xstack=inputs=%d:layout=%s:fill=white,trim=duration=%.2f[out]" % (n, layout, longest))
    mp4 = os.path.join(d, "comparison.mp4")
    gif = os.path.join(d, "comparison-%dx.gif" % a.speed)
    log_path = os.path.join(d, "..", "compare.log")
    with open(log_path, "wb") as log:
        args = ["ffmpeg", "-y"] + sum((["-i", v] for v in videos), []) + [
            "-filter_complex", graph, "-map", "[out]", "-r", "30", "-c:v", "libx264", "-preset", "slow",
            "-crf", "20", "-tune", "stillimage", "-pix_fmt", "yuv420p", "-movflags", "+faststart", mp4]
        subprocess.run(args, stdout=log, stderr=log, check=True)
        vf = ("setpts=PTS/%d,fps=10,scale=1280:-2:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];"
              "[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" % a.speed)
        subprocess.run(["ffmpeg", "-y", "-i", mp4, "-vf", vf, gif], stdout=log, stderr=log, check=True)
    os.remove(log_path)
    print(mp4, gif)


if __name__ == "__main__":
    main()
