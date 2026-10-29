"""Scene for demo first-diagram. One a.chapter() per key moment of brief.md, same titles, same order."""
from helpers import *

OUTPUT = "first-diagram.mp4"

IDEA = (360, 270, 570, 390)
DIAGRAM = (790, 270, 1000, 390)


def scene(a):
    pg = a.pg
    a.chapter("Empty canvas")
    a.hover(toolbar(a))
    a.hold(1.5)
    a.hover(tool_button(a, "Rectangle"))
    a.hold(1.0)

    a.chapter("First box")
    box(a, *IDEA, "Idea")
    a.move(640, 520)
    a.hold(1.5)

    a.chapter("Second box")
    box(a, *DIAGRAM, "Diagram")
    a.move(680, 520)
    a.hold(1.5)

    a.chapter("Arrow")
    tool(a, "Arrow")
    a.drag(IDEA[2] + 8, 330, DIAGRAM[0] - 8, 330, dur=1.0)
    a.key("Escape", after=300)
    a.move(680, 520)
    a.hold(1.5)

    a.chapter("Color")
    a.click_at((IDEA[0] + IDEA[2]) / 2, IDEA[1] + 4, after=600)
    panel = pg.get_by_role("region", name="Selected shape actions")
    a.click(panel.get_by_role("button", name="#a5d8ff", exact=True), after=800)
    a.hold(2.0)

    a.chapter("Finished diagram")
    a.click_at(680, 560, after=600)
    a.hold(2.5)
