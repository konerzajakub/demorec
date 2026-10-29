# {{project}}

What the agent needs to know about the application before it writes any demo. Fill it from the
app's repository, docs and a running instance. Ask the person only what those cannot answer.
Keep it factual. Delete what stops being true.

## What it is

One paragraph: what the application does, for whom, and the problem it solves.

## Users and roles

Who uses it, what each role does, which role the demos show.

## Glossary

Domain terms as the UI shows them, with a short meaning. Use exactly these words in chapter
titles and briefs.

## Screens

Main screens with their URL path and what the viewer sees there. Include how to reach each one
from the menu.

## Demo data

The fictional entities that exist after a reset (customers, orders, users) and their identifiers.
Never real people or customers.

## Running and resetting

How to start the app locally, how to put it back into the demo state (the `before` command in
project.toml), ports, accounts. Secrets go into environment variables, not into this file.

## Selectors

How to address elements reliably: test ids, ARIA labels, the UI language. Note components that
need special handling (custom selects, date pickers, virtualised tables, drawers).

## Pitfalls

Timing problems, animations, dialogs that appear only sometimes, anything that broke a recording
before, with the fix.
