"""Shared steps for excalidraw.com. Scenes import them with `from helpers import *`.

Excalidraw draws on a <canvas>, so shapes have no locators. Shapes are addressed by viewport
coordinates with a.drag() and a.click_at(), toolbar buttons and panels by role and name."""
from demorec import log


def toolbar(a):
    return a.pg.get_by_role("region", name="Shapes")


def tool_button(a, name):
    """Toolbar tool by name. excalidraw.com marks tools as buttons, older self-hosted builds as radios."""
    bar = toolbar(a)
    return bar.get_by_role("button", name=name, exact=True).or_(bar.get_by_role("radio", name=name, exact=True))


def tool(a, name, after=500):
    """Pick a tool in the top toolbar, e.g. "Rectangle", "Arrow"."""
    a.click(tool_button(a, name), after=after)


def box(a, x0, y0, x1, y1, label):
    """Draw a rectangle and type a label into it (Enter on a selected shape opens its text)."""
    tool(a, "Rectangle")
    a.drag(x0, y0, x1, y1)
    a.key("Enter", after=400)
    a.write(label, delay=90, after=400)
    a.key("Escape", after=600)
