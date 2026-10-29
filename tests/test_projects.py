"""Every bundled scene compiles and every brief's key moments match the scene's chapters."""
import ast, glob, os

from demorec.brief import key_moments

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def chapters(src):
    return [n.args[0].value for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Call)
            and getattr(n.func, "attr", "") == "chapter" and n.args and isinstance(n.args[0], ast.Constant)]


def test_scenes_compile_and_follow_briefs():
    scenes = glob.glob(os.path.join(ROOT, "projects", "*", "demos", "*", "scene.py"))
    assert scenes
    for p in scenes:
        if os.path.basename(os.path.dirname(p)).startswith("_") or os.sep + "_template" + os.sep in p:
            continue  # templates and scratch demos
        with open(p, encoding="utf-8") as f:
            found = chapters(f.read())
        moments = key_moments(os.path.join(os.path.dirname(p), "brief.md"))
        if moments:
            assert found == moments, p
