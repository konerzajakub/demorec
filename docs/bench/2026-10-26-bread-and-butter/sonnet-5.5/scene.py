"""Scene for demo bread-and-butter. One a.chapter() per key moment of brief.md, same titles, same order.

The panel with the shape properties opens on the left (x < 216) whenever something is selected,
so the whole diagram lives to the right of x = 240. Everything is drawn at 100 % zoom; the last
chapter zooms to fit. This build has no Sticky note tool, the note is a yellow rectangle with text."""
from helpers import *

OUTPUT = "bread-and-butter.mp4"

# Viewport coordinates (1280x720). Boxes are (x0, y0, x1, y1).
TITLE = (609, 105)
INGREDIENTS = {                       # column on the left, one box per ingredient
    "bread":   (240, 310, 350, 366),
    "butter":   (240, 390, 350, 446),
    "chives": (240, 470, 350, 526),
    "salt":     (240, 550, 350, 606),
}
STEPS = [                             # row at the top, left to right
    (410, 155, 560, 255, "1. Slice the bread"),
    (640, 155, 790, 255, "2. Spread the butter"),
    (870, 155, 1020, 255, "3. Top with chives and salt"),
]
STEP_Y = 205                          # vertical middle of the step row, the arrows between steps run here
NOTE = (970, 300, 1210, 400)          # below step 3 and the dish
NOTE_TEXT = "Chop the chives just before serving"
DISH = (1090, 155, 1240, 255)         # right of step 3

GAP = 6                               # arrows start and end this far outside a shape, so they bind to it
YELLOW, GREEN, NONE = "#ffec99", "#b2f2bb", "transparent"
PARK = (640, 665)                     # where the mouse rests in the last frames, on empty canvas
AWAY_POSTUP = (640, 420)              # empty canvas, so the cursor does not hide the last arrowhead
AWAY_ARROWS = (640, 540)              # empty canvas below the ingredient arrows

# Pace: shorter waits and faster typing than the default, to get to about 90 s. A tool is picked
# with a click on the toolbar the first time, later with the shortcut next to its button.
FAST = dict(delay=22, dur=0.3, after=200)
RECT, ARROW = "2", "5"


def scene(a):
    ing = INGREDIENTS
    s1, s2, s3 = STEPS

    a.chapter("Blank canvas")
    a.hover(tool_button(a, "Rectangle"))
    a.hold(1.2)

    a.chapter("Title")
    title_text(a, *TITLE, "Bread with butter and chives", delay=22, after=200)
    deselect(a)
    a.hold(1.5)

    a.chapter("Ingredients")
    for i, (name, (x0, y0, x1, y1)) in enumerate(ing.items()):
        box(a, x0, y0, x1, y1, name, key=None if i == 0 else RECT, **FAST)
    deselect(a)
    a.hold(1.5)

    a.chapter("Steps")
    for x0, y0, x1, y1, label in STEPS:
        box(a, x0, y0, x1, y1, label, key=RECT, **FAST)
    arrow(a, s1[2] + GAP, STEP_Y, s2[0] - GAP, STEP_Y, dur=0.35, after=200)
    arrow(a, s2[2] + GAP, STEP_Y, s3[0] - GAP, STEP_Y, dur=0.35, after=200, key=ARROW)
    deselect(a)
    a.move(*AWAY_POSTUP)
    a.hold(1.8)

    a.chapter("What goes where")
    # Each ingredient arrow fans up from the right edge of the ingredient to the bottom edge of
    # its step. The arrows to step 3 end apart from each other, so both stay visible.
    targets = [
        ("bread",   s1, (s1[0] + s1[2]) // 2),
        ("butter",   s2, (s2[0] + s2[2]) // 2),
        ("chives", s3, s3[0] + 40),
        ("salt",     s3, s3[2] - 30),
    ]
    for name, step, end_x in targets:
        x0, y0, x1, y1 = ing[name]
        arrow(a, x1 + GAP, (y0 + y1) // 2, end_x, step[3] + GAP, dur=0.5, after=200, key=ARROW)
    deselect(a)
    a.move(*AWAY_ARROWS)
    a.hold(1.8)

    a.chapter("Colors")
    for name, color in (("butter", YELLOW), ("chives", GREEN)):
        x0, y0, x1, y1 = ing[name]
        fill(a, (x0 + x1) // 2, y0 + 2, color, after=300)
    deselect(a)
    a.hold(1.8)

    a.chapter("Tip")
    # The color is set while the Rectangle tool is active, so the note is yellow from the start
    # (without this it would get the green of "chives").
    box(a, *NOTE, NOTE_TEXT, key=RECT, before=lambda a: background(a, YELLOW), **FAST)
    deselect(a)
    a.hold(2.2)

    a.chapter("Done")
    # The dish has no fill: Excalidraw would give it the yellow of the note.
    box(a, *DISH, "Enjoy!", shape="Ellipse", before=lambda a: background(a, NONE), **FAST)
    arrow(a, s3[2] + GAP, STEP_Y, DISH[0] - GAP, STEP_Y, dur=0.35, after=200, key=ARROW)
    deselect(a)
    a.hold(0.6)
    a.key("Shift+1", after=1000)       # zoom to fit the whole diagram
    a.move(*PARK)
    a.hold(0.5)                        # the runner holds another 2.5 s after the scene
