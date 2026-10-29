"""Steps that several demos of this app share. Scenes import them with `from helpers import *`.

Keep each helper one visible user action (open a menu item, open a record, confirm a dialog).
Define login(a) here only if the [login] form in project.toml does not fit the app."""
import re

from demorec import log


def goto_menu(a, label):
    nav = a.pg.get_by_role("navigation").first
    a.click(nav.get_by_text(label, exact=True).first, fx=0.3, after=900)
    a.settle(400)
