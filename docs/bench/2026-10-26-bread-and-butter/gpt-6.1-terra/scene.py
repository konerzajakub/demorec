"""A recipe, built on the local Excalidraw canvas."""
from helpers import *

OUTPUT = "bread-and-butter.mp4"

TITLE = (410, 110)
BREAD = (230, 165, 350, 220)
BUTTER = (230, 250, 350, 305)
CHIVES = (230, 335, 350, 390)
SALT = (230, 420, 350, 475)
STEP1 = (405, 525, 565, 605)
STEP2 = (635, 525, 795, 605)
STEP3 = (865, 525, 1045, 605)
FINISH = (1090, 525, 1240, 605)
NOTE = (920, 290, 1140, 420)


def setup(a):
    # Dismiss the welcome screen before capture without leaving anything on the canvas.
    tool(a, "Rectangle", after=150)
    a.drag(500, 300, 600, 400, dur=0.4, after=150)
    a.key("Delete", after=200)


def box(a, x0, y0, x1, y1, label):
    a.key("2", after=150)
    a.drag(x0, y0, x1, y1, dur=0.55, after=150)
    a.key("Enter", after=150)
    a.write(label, delay=35, after=150)
    a.key("Escape", after=200)


def arrow(a, start, end):
    a.key("5", after=150)
    a.drag(*start, *end, dur=0.7, after=250)
    a.key("Escape", after=150)


def scene(a):
    panel = a.pg.get_by_role("region", name="Selected shape actions")

    a.chapter("Blank canvas")
    a.hover(toolbar(a))
    a.hold(2)

    a.chapter("Title")
    tool(a, "Text", after=200)
    a.click_at(*TITLE, after=200)
    a.write("Bread with butter and chives", delay=55, after=200)
    a.key("Escape", after=200)
    a.click_at(750, 145, after=200)
    a.hold(2)

    a.chapter("Ingredients")
    box(a, *BREAD, "bread")
    box(a, *BUTTER, "butter")
    box(a, *CHIVES, "chives")
    box(a, *SALT, "salt")
    a.click_at(385, 460, after=200)
    a.hold(2)

    a.chapter("Steps")
    box(a, *STEP1, "1. Slice the bread")
    box(a, *STEP2, "2. Spread the butter")
    box(a, *STEP3, "3. Top with chives and salt")
    arrow(a, (570, 565), (630, 565))
    arrow(a, (800, 565), (860, 565))
    a.move(825, 625)
    a.hold(2)

    a.chapter("What goes where")
    arrow(a, (350, 193), (480, 520))
    arrow(a, (350, 278), (715, 520))
    arrow(a, (350, 363), (930, 520))
    arrow(a, (350, 448), (980, 520))
    a.move(600, 640)
    a.hold(2)

    a.chapter("Colors")
    a.click_at(290, 251, after=300)
    a.click(panel.get_by_role("button", name="#ffec99", exact=True), after=300)
    a.click_at(290, 336, after=300)
    a.click(panel.get_by_role("button", name="#b2f2bb", exact=True), after=300)
    a.click_at(600, 640, after=300)
    a.hold(2)

    a.chapter("Tip")
    box(a, *NOTE, "Chop the chives just before serving")
    a.click(panel.get_by_role("button", name="#ffec99", exact=True), after=300)
    a.click(panel.get_by_role("group", name="Edges").get_by_role("radio").first, after=300)
    a.click_at(1170, 450, after=300)
    a.hold(2)

    a.chapter("Done")
    tool(a, "Ellipse", after=200)
    a.drag(*FINISH, dur=0.7, after=300)
    a.click(panel.get_by_role("button", name="transparent", exact=True), after=200)
    a.key("Enter", after=200)
    a.write("Enjoy!", delay=55, after=200)
    a.key("Escape", after=200)
    arrow(a, (1050, 565), (1085, 565))
    a.key("Shift+1", after=700)
    a.move(650, 660)
    a.hold(3)
