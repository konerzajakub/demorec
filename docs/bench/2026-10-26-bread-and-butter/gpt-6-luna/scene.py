"""Scene for bread-and-butter. One chapter per confirmed key moment."""
from helpers import *

OUTPUT = "bread-and-butter.mp4"

# Keep the recipe diagram inside the 1280x720 viewport at its starting zoom.
BREAD = (250, 220, 370, 270)
BUTTER = (250, 310, 370, 360)
CHIVES = (250, 400, 370, 450)
SALT = (250, 490, 370, 540)

STEP_1 = (440, 190, 610, 280)
STEP_2 = (650, 300, 820, 395)
STEP_3 = (860, 415, 1045, 515)
ENJOY = (1090, 425, 1200, 505)
TIP = (850, 555, 1090, 630)


def setup(a):
    """Dismiss the welcome screen, leaving an empty canvas for the first chapter."""
    tool(a, "Rectangle")
    a.drag(590, 320, 690, 380)
    a.key("ControlOrMeta+z")
    a.move(1210, 630)


def scene(a):
    pg = a.pg

    a.chapter("Blank canvas")
    a.hover(toolbar(a))
    a.hold(1.5)

    a.chapter("Title")
    canvas_text(a, 390, 125, "Bread with butter and chives")
    deselect(a)
    park_cursor(a)
    a.hold(2.0)

    a.chapter("Ingredients")
    box(a, *BREAD, "bread")
    deselect(a)
    box(a, *BUTTER, "butter")
    deselect(a)
    box(a, *CHIVES, "chives")
    deselect(a)
    box(a, *SALT, "salt")
    deselect(a)
    park_cursor(a)
    a.hold(2.0)

    a.chapter("Steps")
    box(a, *STEP_1, "1. Slice the bread")
    deselect(a)
    box(a, *STEP_2, "2. Spread the butter")
    deselect(a)
    box(a, *STEP_3, "3. Top with chives and salt")
    deselect(a)
    arrow(a, STEP_1[2], 235, STEP_2[0], STEP_2[1])
    deselect(a)
    arrow(a, STEP_2[2], 347, STEP_3[0], STEP_3[1])
    deselect(a)
    park_cursor(a)
    a.hold(2.0)

    a.chapter("What goes where")
    arrow(a, BREAD[2], 245, STEP_1[0], 235)
    deselect(a)
    arrow(a, BUTTER[2], 335, STEP_2[0], 347)
    deselect(a)
    arrow(a, CHIVES[2], 425, STEP_3[0], 455)
    deselect(a)
    arrow(a, SALT[2], 515, STEP_3[0], 485)
    deselect(a)
    park_cursor(a)
    a.hold(2.0)

    a.chapter("Colors")
    fill_shape(a, BUTTER[0] + 70, (BUTTER[1] + BUTTER[3]) / 2, "#ffec99")
    deselect(a)
    fill_shape(a, CHIVES[0] + 70, (CHIVES[1] + CHIVES[3]) / 2, "#b2f2bb")
    deselect(a)
    park_cursor(a)
    a.hold(2.0)

    a.chapter("Tip")
    box(a, *TIP, "Chop the chives just before serving")
    fill_selected(a, "#ffec99")
    deselect(a)
    park_cursor(a)
    a.hold(2.0)

    a.chapter("Done")
    ellipse(a, *ENJOY, "Enjoy!")
    fill_selected(a, "transparent")
    deselect(a)
    arrow(a, STEP_3[2], 465, ENJOY[0], 465)
    deselect(a)
    a.click(pg.get_by_role("region", name="Canvas actions").get_by_role("button", name="Zoom out", exact=True), after=700)
    park_cursor(a)
    a.hold(2.5)
