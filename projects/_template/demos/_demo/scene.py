"""Scene for demo {{demo}}. One a.chapter() per key moment of brief.md, same titles, same order."""
from helpers import *

OUTPUT = "{{demo}}.mp4"
# SIZE = (1920, 1080)   # viewport for this demo only, default from project.toml
# LOGIN = False         # skip the automatic login, the scene starts on the login page


def setup(a):
    """Runs after login, before the recording starts. Not in the video."""


def scene(a):
    a.chapter("First moment")
    a.hold(2.0)
