"""Build the confirmed recipe using the local Excalidraw UI."""
from helpers import *

OUTPUT = "bread-and-butter.mp4"

TITLE = (530, 125)
BREAD = (265, 225, 400, 285)
BUTTER = (265, 335, 400, 395)
CHIVES = (265, 445, 400, 505)
SALT = (265, 555, 400, 615)
CUT = (490, 220, 665, 305)
SPREAD = (745, 220, 925, 305)
SPRINKLE = (1005, 220, 1220, 305)
NOTE = (900, 515, 1220, 620)
DISH = (1020, 385, 1220, 455)
CUT_TO_SPREAD = (671, 262, 739, 262)
SPREAD_TO_SPRINKLE = (931, 262, 999, 262)
BREAD_TO_CUT = (406, 255, 484, 262)
BUTTER_TO_SPREAD = (406, 365, 825, 311)
CHIVES_TO_SPRINKLE = (406, 475, 1030, 311)
SALT_TO_SPRINKLE = (406, 585, 1080, 311)
SPRINKLE_TO_DISH = (1150, 311, 1150, 379)
BUTTER_EDGE = (268, 365)
CHIVES_EDGE = (268, 475)
CLEAR = (740, 650)


def setup(a):
    # Dismiss the welcome screen before capture, leaving an empty canvas and toolbar.
    tool(a, "Rectangle", after=120)
    a.click(shape_actions(a).get_by_role("group", name="Stroke width", exact=True)
            .get_by_role("radio").nth(0), after=120)
    tool(a, "Hand (panning tool)", after=120)
    a.move(*CLEAR)


def scene(a):
    # Capture adds overhead to each cursor frame. Use brisk travel, full reading holds.
    if a.speed == 1.0:
        a.speed = 0.2
    a.chapter("Blank canvas")
    a.hover(tool_button(a, "Rectangle"))
    reading_pause(a, 1.5)

    a.chapter("Title")
    tool(a, "Text", after=120)
    font_size(a, "L")
    a.click_at(*TITLE, after=120)
    a.write("Bread with butter and chives", delay=45, after=120)
    a.key("Escape", after=150)
    canvas_overview(a, CLEAR)

    a.chapter("Ingredients")
    tool(a, "Text", after=120)
    font_size(a, "M")
    labelled_shape(a, "Rectangle", BREAD, "bread")
    labelled_shape(a, "Rectangle", BUTTER, "butter")
    labelled_shape(a, "Rectangle", CHIVES, "chives")
    labelled_shape(a, "Rectangle", SALT, "salt")
    canvas_overview(a, CLEAR)

    a.chapter("Steps")
    labelled_shape(a, "Rectangle", CUT, "1. Slice the bread")
    labelled_shape(a, "Rectangle", SPREAD, "2. Spread the butter")
    labelled_shape(a, "Rectangle", SPRINKLE, "3. Top with chives and salt")
    connector(a, CUT_TO_SPREAD)
    connector(a, SPREAD_TO_SPRINKLE)
    canvas_overview(a, CLEAR, 2.0)

    a.chapter("What goes where")
    connector(a, BREAD_TO_CUT)
    connector(a, BUTTER_TO_SPREAD)
    connector(a, CHIVES_TO_SPRINKLE)
    connector(a, SALT_TO_SPRINKLE)
    canvas_overview(a, CLEAR, 2.0)

    a.chapter("Colors")
    a.click_at(*BUTTER_EDGE, after=120)
    shape_background(a, "#ffec99")
    a.click_at(*CHIVES_EDGE, after=120)
    shape_background(a, "#b2f2bb")
    canvas_overview(a, CLEAR, 2.0)

    a.chapter("Tip")
    a.key("2", after=120)
    shape_background(a, "#ffec99")
    a.click(shape_actions(a).get_by_role("group", name="Edges", exact=True)
            .get_by_role("radio").nth(0), after=120)
    a.drag(*NOTE, dur=0.55, after=150)
    a.key("Enter", after=100)
    a.write("Chop the chives just before serving", delay=32, after=100)
    a.key("Escape", after=150)
    canvas_overview(a, CLEAR, 2.5)

    a.chapter("Done")
    a.key("4", after=120)
    shape_background(a, "transparent")
    a.drag(*DISH, dur=0.55, after=150)
    a.key("Enter", after=100)
    a.write("Enjoy!", delay=45, after=100)
    a.key("Escape", after=150)
    connector(a, SPRINKLE_TO_DISH)
    canvas_overview(a, CLEAR, 1.0)
    a.key("Shift+1", after=700)  # Excalidraw: zoom to fit all elements.
    a.move(*CLEAR)
    reading_pause(a, 3.0)
    if a.speed > 0.1:
        a.speed = 1.0
