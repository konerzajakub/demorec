"""Scene for demo bread-and-butter. One a.chapter() per key moment of brief.md, same titles, same order.

Viewport coordinates at 100 % zoom. The properties panel covers x < 220 while a shape is
selected or a tool is active, so the diagram starts right of it. 16 drawn shapes and arrows
make this a dense demo: it uses the few-step mouse helpers (see helpers.py) to stay near 90 s.
The first use of a tool is a click in the toolbar, repeats use its number key."""
from helpers import *

OUTPUT = "bread-and-butter.mp4"

TITLE_AT = (505, 125)          # Text tool: left edge, vertical centre of the title

# Ingredients, a column on the left: (x0, y0, x1, y1)
COL = (235, 335)
BREAD = (COL[0], 202, COL[1], 258)
BUTTER = (COL[0], 312, COL[1], 368)
CHIVES = (COL[0], 422, COL[1], 478)
SALT = (COL[0], 532, COL[1], 588)

# Steps, a row to the right
ROW = (185, 275)
STEP1 = (405, ROW[0], 555, ROW[1])
STEP2 = (625, ROW[0], 775, ROW[1])
STEP3 = (845, ROW[0], 995, ROW[1])
ROW_Y = (ROW[0] + ROW[1]) // 2

NOTE = (965, 320, 1175, 420)   # sticky note under step 3
DISH = (1060, 185, 1240, 275)  # ellipse "Enjoy!" after step 3

GAP = 8                        # arrow ends this far outside a shape, so they bind to it
EMPTY = (700, 630)             # empty canvas, click here to deselect
REST = (720, 600)              # empty canvas, the cursor waits here so it covers no label


def mid_y(r):
    return (r[1] + r[3]) // 2


def center(r):
    return (r[0] + r[2]) / 2, (r[1] + r[3]) / 2


def rest(a):
    """Deselect and park the cursor where it covers nothing, before a chapter's end."""
    a.key("Escape", after=120)
    glide(a, *REST, steps=2)


def setup(a):
    # The welcome screen lists Live collaboration and Sign up. Drawing a first shape hides it,
    # deleting that shape leaves the blank canvas.
    tool(a, "Rectangle", after=200)
    a.drag(600, 400, 700, 460, after=200)
    a.key("Delete", after=400)
    a.move(700, 420)


def scene(a):
    a.chapter("Blank canvas")
    glide(a, *a.point(toolbar(a), fx=0.3), steps=4)
    a.hold(1.2)  # after the runner's 1.5 s opening hold

    a.chapter("Title")
    pick(a, "Text")
    press(a, panel(a).get_by_title("Very large"), after=250)
    tap(a, *TITLE_AT, after=250)
    a.write("Bread with butter and chives", delay=25, after=200)
    a.key("Escape", after=200)
    rest(a)
    a.hold(1.5)

    a.chapter("Ingredients")
    # The title set Very large for new text, the labels go back to Medium.
    pick(a, "Text")
    press(a, panel(a).get_by_title("Medium"), after=250)
    shape(a, *BREAD, "bread", key=False)
    shape(a, *BUTTER, "butter")
    shape(a, *CHIVES, "chives")
    shape(a, *SALT, "salt")
    rest(a)
    a.hold(1.5)

    a.chapter("Steps")
    shape(a, *STEP1, "1. Slice the bread")
    shape(a, *STEP2, "2. Spread the butter")
    shape(a, *STEP3, "3. Top with chives and salt")
    link(a, STEP1[2] + GAP, ROW_Y, STEP2[0] - GAP, ROW_Y, key=False)
    link(a, STEP2[2] + GAP, ROW_Y, STEP3[0] - GAP, ROW_Y)
    rest(a)
    a.hold(1.5)

    a.chapter("What goes where")
    below = ROW[1] + GAP
    link(a, COL[1] + GAP, mid_y(BREAD), STEP1[0] - GAP, ROW_Y)
    link(a, COL[1] + GAP, mid_y(BUTTER), 690, below)
    link(a, COL[1] + GAP, mid_y(CHIVES), 895, below)
    link(a, COL[1] + GAP, mid_y(SALT), 945, below)
    rest(a)
    a.hold(1.8)

    a.chapter("Colors")
    tap(a, *center(BUTTER), after=300)
    fill(a, "#ffec99")
    tap(a, *center(CHIVES), after=300)
    fill(a, "#b2f2bb")
    rest(a)
    a.hold(1.8)

    a.chapter("Tip")
    # A sticky note: a rectangle with sharp corners and a paper colour unlike the ingredients.
    pick(a, "Rectangle")
    press(a, panel(a).get_by_title("Sharp").first, after=250)
    fill_from_palette(a, "color-orange")
    pick(a, "Rectangle", key=True)
    pull(a, *NOTE)
    a.key("Enter", after=150)
    a.write("Chop the chives just before serving", delay=0, after=150)
    a.key("Escape", after=120)
    rest(a)
    a.hold(2.0)

    a.chapter("Done")
    pick(a, "Ellipse")
    fill(a, "transparent", after=250)
    pull(a, *DISH)
    a.key("Enter", after=150)
    a.write("Enjoy!", delay=0, after=150)
    a.key("Escape", after=120)
    link(a, STEP3[2] + GAP, ROW_Y, DISH[0] - GAP, ROW_Y)
    a.key("Escape", after=120)
    a.key("Shift+1", after=800)
    glide(a, 1150, 640, steps=2)
    a.hold(0.5)  # the runner adds 2.5 s at the end
