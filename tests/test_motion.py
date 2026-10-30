"""Easing curves and the cursor arc."""
import math

import pytest

from demorec import config
from demorec.motion import EASINGS, arc, curve, ease

U = [i / 100 for i in range(101)]


@pytest.mark.parametrize("name", list(EASINGS))
def test_every_easing_starts_at_0_and_lands_at_1(name):
    assert ease(name, 0) == 0 and ease(name, 1) == 1
    assert ease(name, -1) == 0 and ease(name, 2) == 1
    f = curve(name)
    assert f(0.0) == pytest.approx(0, abs=1e-9) and f(1.0) == pytest.approx(1, abs=1e-9)
    assert f(0.999) == pytest.approx(1, abs=0.02)  # no jump at the end


@pytest.mark.parametrize("name", [n for n in EASINGS if n not in ("snappy", "bouncy")])
def test_easings_without_bounce_never_go_back_or_overshoot(name):
    v = [ease(name, u) for u in U]
    assert all(b >= a - 1e-12 for a, b in zip(v, v[1:]))
    assert max(v) <= 1 + 1e-9


@pytest.mark.parametrize("name,peak", [("snappy", 1.005), ("bouncy", 1.03)])
def test_bouncy_springs_overshoot_a_little(name, peak):
    top = max(ease(name, u) for u in U)
    assert peak < top < 1.15


@pytest.mark.parametrize("name", ["human", "ease-in-out", "cubic", "quint", "smoothstep", "linear"])
def test_symmetric_curves(name):
    for u in U:
        assert ease(name, u) + ease(name, 1 - u) == pytest.approx(1, abs=1e-6)


def test_ease_in_out_starts_slow_and_ends_slow():
    for name in ("spring", "human", "ease-in-out", "cubic", "quint", "material", "smoothstep"):
        f = curve(name)
        assert f(0.01) < 0.01 * 0.6, name  # starts slower than linear
        assert 1 - f(0.99) < 0.01 * 0.6, name  # and lands slower than linear


def test_known_values():
    assert ease("ease-in-out", 0.5) == pytest.approx(0.5, abs=1e-6)
    assert ease("ease-in-out", 0.25) == pytest.approx(0.1291, abs=2e-3)  # CSS reference value
    assert ease("cubic", 0.25) == pytest.approx(4 * 0.25 ** 3)
    assert ease("quint", 0.25) == pytest.approx(16 * 0.25 ** 5)
    assert ease("human", 0.5) == pytest.approx(0.5)
    w = 2 * math.pi  # critically damped spring, about 82 % there at half time
    assert ease("spring", 0.5) == pytest.approx(1 - (1 + w / 2) * math.exp(-w / 2), abs=0.01)
    assert ease("material", 0.5) > 0.85  # fast start, long deceleration


def test_spring_is_quicker_than_ease_in_out_then_lands_softly():
    assert ease("spring", 0.3) > ease("ease-in-out", 0.3)


def test_spring_soft_is_monotonic_from_0_to_1():
    v = [ease("spring-soft", i / 1000) for i in range(1001)]
    assert v[0] == 0 and v[-1] == 1
    assert all(b >= a for a, b in zip(v, v[1:]))
    assert max(v) <= 1


def test_spring_soft_has_zero_speed_at_both_ends():
    f, h = curve("spring-soft"), 1e-3
    assert f(h) / h < 0.01  # 1 = the average speed of the whole move
    assert (1 - f(1 - h)) / h < 0.01
    assert ((1 - curve("spring")(1 - h)) / h) > 0.05  # the plain spring still moves there


def test_spring_soft_starts_gentler_and_lands_like_the_spring():
    soft, spring = curve("spring-soft"), curve("spring")
    assert soft(0.05) < spring(0.05) / 2  # no jump on the first frames
    assert soft(0.5) > 0.6  # most of the way at half time, like the spring
    speed = [(soft((i + 1) / 100) - soft(i / 100)) * 100 for i in range(100)]
    assert 0.12 < speed.index(max(speed)) / 100 < 0.3  # the peak comes a little later than the spring's


def test_unknown_easing_fails_with_the_names():
    with pytest.raises(ValueError, match="spring"):
        curve("springy")


def test_arc_is_exact_at_the_ends_and_bows_in_the_middle():
    assert arc(0, 0, 100, 0, 0, 0, 0.05) == (0, 0)
    assert arc(0, 0, 100, 0, 1, 1, 0.05) == pytest.approx((100, 0))
    x, y = arc(0, 0, 100, 0, 0.5, 0.5, 0.05)
    assert x == pytest.approx(50) and y == pytest.approx(5)
    assert arc(0, 0, 100, 0, 0.5, 0.5, 0) == (50, 0)


def test_motion_table_in_project_toml(tmp_path):
    (tmp_path / "project.toml").write_text('[app]\nurl = "http://x/"\n[motion]\nzoom_easing = "quint"\n'
                                           'cursor_speed = 2\n[recording]\ncrop_zoom = 2\n', encoding="utf-8")
    cfg = config.load(tmp_path)
    assert (cfg.zoom_easing, cfg.cursor_easing, cfg.cursor_speed, cfg.crop_zoom) == ("quint", "human", 2, 2)
    (tmp_path / "project.toml").write_text('[app]\nurl = "http://x/"\n[motion]\ncursor_easing = "wobbly"\n',
                                           encoding="utf-8")
    with pytest.raises(SystemExit, match="cursor_easing"):
        config.load(tmp_path)
