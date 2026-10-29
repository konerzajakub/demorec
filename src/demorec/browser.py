"""The browser a demo runs in: launch, sign in, and the accessibility tree of a page."""
import os, sys, uuid

CURSOR_JS = open(os.path.join(os.path.dirname(__file__), "cursor.js"), encoding="utf-8").read()
UA_PLATFORM = {"win32": "Windows NT 10.0; Win64; x64", "darwin": "Macintosh; Intel Mac OS X 10_15_7"}


def new_profile(cfg):
    """Path for a fresh browser profile. Every run starts with empty cookies and storage."""
    return os.path.join(cfg.work_dir, "profile-%s" % uuid.uuid4().hex[:6])


def desktop_user_agent(p, cfg):
    """Headless Chrome announces itself as HeadlessChrome. Sites get the User-Agent of desktop
    Chrome instead, with the major version of the installed browser (Chrome's reduced format)."""
    try:
        b = p.chromium.launch(channel="chrome", headless=True)
    except Exception:
        b = p.chromium.launch(channel=cfg.channel or None, headless=True)
    major = b.version.split(".")[0]
    b.close()
    plat = UA_PLATFORM.get(sys.platform, "X11; Linux x86_64")
    return "Mozilla/5.0 (%s) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/%s.0.0.0 Safari/537.36" % (plat, major)


def open_context(p, cfg, profile):
    """Headless browser with the drawn cursor. Returns the context and its first page."""
    ctx = p.chromium.launch_persistent_context(
        profile, channel=cfg.channel or None, headless=True,
        user_agent=desktop_user_agent(p, cfg),
        viewport={"width": cfg.width, "height": cfg.height},
        screen={"width": cfg.width, "height": cfg.height}, device_scale_factor=cfg.scale,
        locale=cfg.locale, timezone_id=cfg.timezone, accept_downloads=True,
        # --force-device-scale-factor: without it the screencast sends frames at CSS size.
        # --remote-debugging-port: Cast reads frames on its own connection, see cdp.py.
        args=["--lang=" + cfg.locale, "--force-device-scale-factor=%d" % cfg.scale, "--remote-debugging-port=0"],
        ignore_default_args=["--hide-scrollbars"])
    ctx.add_init_script(CURSOR_JS)
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    return ctx, pg


def sign_in(a, cfg, helpers):
    """helpers.login(a) wins. Otherwise fill the form from [login] in project.toml."""
    pg = a.pg
    if helpers and hasattr(helpers, "login"):
        helpers.login(a)
    elif cfg.login:
        login = cfg.login
        pg.goto(login.url or cfg.url)
        pg.wait_for_selector(login.username_selector, timeout=60000)
        pg.fill(login.username_selector, login.username)
        pg.fill(login.password_selector, login.password)
        pg.click(login.submit_selector)
        pg.wait_for_load_state("load", timeout=30000)
    else:
        pg.goto(cfg.url)
    if cfg.ready:
        pg.locator(cfg.ready).first.wait_for(state="visible", timeout=60000)
    a.settle(1000)


def save_aria_tree(pg, path):
    """The roles and names that get_by_role() and get_by_label() match, under the page URL."""
    with open(path, "w", encoding="utf-8") as f:
        f.write("# url: %s\n" % pg.url + pg.locator("body").aria_snapshot())
