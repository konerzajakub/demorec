"""End to end: records the bundled example and checks the video and the artifacts."""
import json, os, shutil, subprocess

from demorec import config, runner

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_record_example(tmp_path):
    cfg = config.load(os.path.join(ROOT, "projects", "example"), out_root=str(tmp_path))
    result, out = runner.run_demo(cfg, "add-task")
    assert result["status"] == "ok", result
    assert result["missing_moments"] == []
    assert [c["title"] for c in result["chapters"]] == ["Task list", "New task", "Task created", "Open tasks"]
    probe = subprocess.run([shutil.which("ffprobe"), "-v", "error", "-show_entries", "stream=width,height",
                            "-show_entries", "format=duration", "-of", "json", os.path.join(out, "add-task.mp4")],
                           capture_output=True, text=True, check=True)
    info = json.loads(probe.stdout)
    assert (info["streams"][0]["width"], info["streams"][0]["height"]) == (1280 * cfg.scale, 720 * cfg.scale)
    assert abs(float(info["format"]["duration"]) - result["duration_s"]) < 0.5
    assert len(os.listdir(os.path.join(out, "keyframes"))) == 4
    assert os.path.exists(os.path.join(out, "contact.jpg"))
