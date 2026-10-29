# example

## What it is

A one-page task list (`site/index.html`) that ships with demorec. It needs no server and no login.
It exists so that `demorec record projects/example add-task` proves the installation works.

## Users and roles

One role, a lab operator who plans their own tasks.

## Glossary

- Task: a row in the list, with title, owner, due date and status.
- Status: Open or Done.

## Screens

- Task list (`site/index.html`): table of tasks, `New task` button, `Status` filter.
- New task dialog: Title, Owner, Due date, Save, Cancel.

## Demo data

Three tasks on every page load: Calibrate the scale (open), Order reagents (done), Archive
September samples (open). Owners are Operator One and Operator Two. Data lives in memory, a
reload resets it.

## Running and resetting

Nothing to start. Reset is a page reload, which every run does.

## Selectors

- Labels are English. Form fields have `<label for>`, so `get_by_label("Title")` works.
- The table has the accessible name `Tasks`.
- The Status filter is a native `<select>`: use `locator.select_option()`, Actor.choose() is
  for ARIA comboboxes.

## Pitfalls

- A native date input takes typed digits in the browser locale order, en-US is MMDDYYYY.
