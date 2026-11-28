"""Shared steps for the example task list."""
from demorec import log


def task_table(a):
    return a.pg.get_by_role("table", name="Tasks")

