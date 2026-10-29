from demorec.brief import key_moments


def test_key_moments_takes_titles_before_colon(tmp_path):
    p = tmp_path / "brief.md"
    p.write_text("# x\n\n## Goal\n\n1. not a moment\n\n## Key moments\n\n1. **Open list**: rows visible\n"
                 "2. Save: done\n10. No colon\n\n## Format\n\n1. ignored\n", encoding="utf-8")
    assert key_moments(p) == ["Open list", "Save", "No colon"]


def test_missing_brief_has_no_moments(tmp_path):
    assert key_moments(tmp_path / "nope.md") == []
