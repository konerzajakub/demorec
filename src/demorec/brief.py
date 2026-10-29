"""Reads the key moments from a demo brief. The runner compares them with the chapters the scene
created, so a moment the scene forgot shows up in result.json as `missing_moments`."""
import os, re


def key_moments(path):
    """Numbered items under the `## Key moments` heading. The title is the text before the
    first colon, without Markdown emphasis: `1. Edit a price: ...` gives `Edit a price`."""
    if not os.path.exists(path):
        return []
    moments, inside = [], False
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                inside = line.lstrip("#").strip().lower() == "key moments"
                continue
            m = re.match(r"\s*\d+\.\s+(.*)", line)
            if inside and m:
                title = m.group(1).split(":", 1)[0]
                moments.append(re.sub(r"[*_`]", "", title).strip())
    return moments
