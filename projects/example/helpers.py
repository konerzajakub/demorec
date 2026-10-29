"""Shared steps for the example task list."""
import sys

from demorec import log


def task_table(a):
    return a.pg.get_by_role("table", name="Tasks")


def pick(a, select, value, after=900):
    """Native <select>: show the click, then set the value (the open list is drawn by the OS)."""
    a.click(select, fx=0.5, after=200)
    select.select_option(value)
    if sys.platform == "darwin":  # headless Chrome on macOS opens no list, Escape would close a dialog
        a.wait(after)
    else:
        a.key("Escape", after=after)
