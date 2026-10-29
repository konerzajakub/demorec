"""Scene for demo add-task. One a.chapter() per key moment of brief.md."""
from helpers import *

OUTPUT = "add-task.mp4"


def scene(a):
    pg = a.pg
    a.chapter("Task list")
    a.hover(task_table(a).get_by_role("row").nth(1), fx=0.2)
    a.hold(1.5)

    a.chapter("New task")
    a.click(pg.get_by_role("button", name="New task"), after=700)
    dlg = a.dialog()
    a.type(dlg.get_by_label("Title"), "Check the fume hood")
    pick(a, dlg.get_by_label("Owner"), "Operator Two", after=400)
    due = dlg.get_by_label("Due date")
    a.click(due, fx=0.15, after=200)
    due.evaluate("e => { e.blur(); e.focus(); }")  # start at the month, the click can hit another part
    pg.keyboard.type("11152026", delay=90)
    a.key("Tab")
    a.hold(1.2)

    a.chapter("Task created")
    a.click(dlg.get_by_role("button", name="Save"), after=300)
    a.hover(task_table(a).get_by_role("row").nth(1), fx=0.2)
    a.see("Task created")  # the confirmation hides after 2.5 s, the chapter must end before that
    a.hold(1.0)

    a.chapter("Open tasks")
    pick(a, pg.get_by_label("Status"), "open")
    a.hold(2.0)
