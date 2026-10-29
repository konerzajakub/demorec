"""Project configuration: `project.toml` in the project folder. See projects/_template."""
import os, tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Login:
    url: str = ""                 # empty: open app.url and expect the login form there
    username: str = ""
    password: str = ""
    username_env: str = "DEMOREC_USERNAME"   # env vars win over the values above
    password_env: str = "DEMOREC_PASSWORD"
    username_selector: str = "#username"
    password_selector: str = "#password"
    submit_selector: str = "#kc-login"       # Keycloak default


@dataclass
class Config:
    project_dir: str
    name: str
    url: str
    ready: str = ""               # selector that is visible once the app is usable
    width: int = 1440
    height: int = 900
    locale: str = "en-US"
    timezone: str = "UTC"
    channel: str = ""             # "chrome" uses installed Chrome, empty uses Playwright Chromium
    safe_top: int = 80            # px under fixed bars: Actor.visible() scrolls elements below this
    safe_bottom: int = 60
    fixed_header: int = 0         # px height of a fixed header whose elements never need scrolling
    scroll: bool = True           # click/hover scroll the target into view with the wheel first
    fps: int = 30
    crf: int = 20
    scale: int = 2                # device pixels per CSS pixel, 2 = a 2560x1440 video from a 1280x720 viewport
    before: str = ""              # shell command run before every recording (reset demo data)
    login: Login | None = None
    out_dir: str = ""
    work_dir: str = ""
    extra: dict = field(default_factory=dict)


# Config fields each table of project.toml can set. Keys a project leaves out keep the defaults above.
TABLE_FIELDS = {
    "app": ("ready",),
    "browser": ("width", "height", "locale", "timezone", "channel", "safe_top", "safe_bottom", "fixed_header", "scroll"),
    "recording": ("fps", "crf", "scale", "before"),
}


def load(project_dir, out_root=None):
    """Config of the project in project_dir. out_root replaces <project>/out, the tests use it."""
    project_dir = os.path.abspath(project_dir)
    path = os.path.join(project_dir, "project.toml")
    if not os.path.exists(path):
        raise SystemExit("no project.toml in %s (create one with: demorec new-project)" % project_dir)
    with open(path, "rb") as f:
        d = tomllib.load(f)
    app = d.get("app", {})
    if not app.get("url"):
        raise SystemExit("%s: [app] url is required" % path)
    settings = {key: d[table][key] for table, keys in TABLE_FIELDS.items()
                for key in keys if key in d.get(table, {})}
    out = out_root or os.path.join(project_dir, "out")
    return Config(project_dir=project_dir, name=d.get("name") or os.path.basename(project_dir),
                  url=app_url(project_dir, app["url"]), login=read_login(d), out_dir=out,
                  work_dir=os.path.join(out, ".work"), extra=d.get("extra", {}), **settings)


def app_url(project_dir, url):
    if url.startswith("./"):  # a local file next to project.toml, for static demo apps
        return Path(project_dir, url[2:]).resolve().as_uri()
    return url


def read_login(d):
    if "login" not in d:
        return None
    login = Login(**d["login"])
    login.username = os.environ.get(login.username_env, login.username)
    login.password = os.environ.get(login.password_env, login.password)
    return login
