# excalidraw

## What it is

Excalidraw (https://excalidraw.com) is a free online whiteboard for quick diagrams that look
hand-drawn. It runs in the browser, needs no account, and keeps the drawing in the browser's
local storage. The demos only use local drawing features of the public site.

## Users and roles

One role: a guest without an account. The demos never sign in.

## Glossary

UI terms as the site shows them (en-US):
- Canvas: the drawing area ("Drawing canvas").
- Toolbar ("Shapes" region): Hand, Selection, Rectangle, Diamond, Ellipse, Arrow, Line, Draw,
  Text, Sticky note, Eraser, More tools.
- Properties panel ("Selected shape actions"): Stroke, Background, Stroke width, Stroke style,
  Sloppiness, Edges, Font family, Font size, Opacity, Layers, Actions. Appears on the left when a
  shape is selected or a drawing tool is active.
- Welcome screen: logo, storage hint and Open, Help, Live collaboration, Sign up. Shown on an
  empty canvas, disappears when the first shape is drawn.

## Screens

Single page `https://excalidraw.com/`. Menu button top left, toolbar top centre, "Try
Excalidraw+" link, share button ("Live collaboration...") and Library top right, zoom and
undo/redo bottom left, Help bottom right.

## Demo data

None. Every run starts with a fresh browser profile, so the canvas is empty.

## Running and resetting

Public site, nothing to start. Reset happens by itself: demorec opens a new browser profile per
run, so local storage is empty. No `before` command.

## Selectors

- Toolbar buttons: `get_by_role("region", name="Shapes").get_by_role("button", name="Rectangle", exact=True)`.
- Colors in the properties panel are buttons named by hex value, e.g. Background light blue
  `#a5d8ff`, inside `get_by_role("region", name="Selected shape actions")`.
- Shapes live on a <canvas> and have no locators. Draw and select them by viewport
  coordinates with `a.drag()` and `a.click_at()`. `scroll = false` in project.toml, because the
  mouse wheel pans the canvas.
- Enter on a selected shape opens its text editor, Escape closes it and keeps the shape selected.

## Pitfalls

- The "Try Excalidraw+" link and the share button are always visible top right. Never click
  them, and never use Live collaboration, Sign up or export to the cloud.
- Third-party site: the UI can change without notice. If a selector or a coordinate stops
  working, run `demorec inspect projects/excalidraw` and compare with this file.
- After a tool is used once, Excalidraw returns to Selection (unless the lock is on).
