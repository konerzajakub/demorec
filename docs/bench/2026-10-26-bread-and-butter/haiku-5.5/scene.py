"""Scene for demo bread-and-butter. One a.chapter() per key moment of brief.md, same titles, same order."""
from helpers import *

OUTPUT = "bread-and-butter.mp4"

# Layout in viewport pixels. The properties panel covers x 16-216 while a shape is selected,
# so the ingredients start at x 250.
TITLE = (470, 120)
STEPS = [(470, 230, 690, 300), (750, 230, 970, 300), (1030, 230, 1250, 300)]
BREAD = (250, 340, 390, 400)
BUTTER = (250, 420, 390, 480)
CHIVES = (250, 500, 390, 560)
SALT = (250, 580, 390, 640)
TIP = (1030, 140, 1250, 210)
ENJOY = (1135, 410, 1265, 470)


def scene(a):
    a.chapter("Blank canvas")
    a.hover(toolbar(a))
    a.hold(1.5)
    a.hover(tool_button(a, "Rectangle"))
    a.hold(1.0)

    a.chapter("Title")
    tool(a, "Text")
    a.click_at(*TITLE, after=400)
    a.write("Bread with butter and chives", delay=55, after=300)
    a.key("Escape", after=300)
    a.key("Escape", after=300)
    a.hold(1.0)

    a.chapter("Ingredients")
    box(a, *BREAD, "bread", delay=55, dur=0.6, after=200)
    box(a, *BUTTER, "butter", delay=55, dur=0.6, after=200)
    box(a, *CHIVES, "chives", delay=55, dur=0.6, after=200)
    box(a, *SALT, "salt", delay=55, dur=0.6, after=200)
    a.key("Escape", after=300)
    a.hold(1.0)

    a.chapter("Steps")
    box(a, *STEPS[0], "1. Slice the bread", delay=55, dur=0.6, after=200)
    box(a, *STEPS[1], "2. Spread the butter", delay=55, dur=0.6, after=200)
    box(a, *STEPS[2], "3. Top with chives and salt", delay=55, dur=0.6, after=200)
    arrow(a, 698, 265, 742, 265, after=200)
    arrow(a, 978, 265, 1022, 265, after=200)
    a.hold(1.5)

    a.chapter("What goes where")
    arrow(a, 396, 370, 580, 308, after=200)
    arrow(a, 396, 450, 860, 308, after=200)
    arrow(a, 396, 530, 1060, 308, after=200)
    arrow(a, 396, 610, 1120, 308, after=200)
    a.hold(1.5)

    a.chapter("Colors")
    fill(a, 320, BUTTER[1] + 3, "#ffec99")
    fill(a, 320, CHIVES[1] + 3, "#b2f2bb")
    a.key("Escape", after=300)
    a.hold(1.5)

    a.chapter("Tip")
    tool(a, "Rectangle", after=200)
    a.drag(*TIP, dur=0.6, after=200)
    background(a, "transparent")   # before the label, else the box shows the last fill (green) while typing
    a.key("Enter", after=400)
    a.write("Chop the chives just before serving", delay=55, after=400)
    a.key("Escape", after=300)
    a.key("Escape", after=300)
    a.hold(1.5)

    a.chapter("Done")
    tool(a, "Ellipse")
    a.drag(*ENJOY, dur=0.6)
    a.key("Enter", after=300)
    a.write("Enjoy!", delay=55, after=300)
    a.key("Escape", after=300)
    arrow(a, 1200, 306, 1200, 408, after=200)
    a.key("Shift+Digit1", after=800)
    a.hold(2.5)
