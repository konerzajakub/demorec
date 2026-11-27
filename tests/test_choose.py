"""Picking from menus and dropdowns: the cursor reads down the list, then clicks the option."""
import pytest
from playwright.sync_api import sync_playwright

from demorec.actor import Actor
from demorec.config import Config

PAGE = """<!doctype html><body style='margin:0;font:16px sans-serif'>
<style>
  [role=listbox], [role=menu] { position: absolute; margin: 0; padding: 4px 0; list-style: none; background: #fff;
    border: 1px solid #999; width: 220px; }
  [role=option], [role=menuitem] { padding: 6px 10px; cursor: pointer; }
  [hidden] { display: none !important; }
</style>
<button id=fruit role=combobox aria-haspopup=listbox aria-expanded=false aria-label=Fruit
  style='position:absolute;left:40px;top:30px;width:200px'>Choose a fruit</button>
<ul id=fruits role=listbox hidden style='left:40px;top:60px'>
  <li role=option>Apple</li><li role=option>Banana</li><li role=option>Cherry</li>
  <li role=option>Date</li><li role=option>Elderberry</li><li role=option>Fig</li>
</ul>
<button id=actions aria-haspopup=menu style='position:absolute;left:320px;top:30px'>Actions</button>
<ul id=menu role=menu hidden style='left:320px;top:60px'>
  <li role=menuitem>Rename</li><li role=menuitem id=export aria-haspopup=menu>Export</li>
</ul>
<ul id=sub role=menu hidden style='left:545px;top:90px;width:120px'>
  <li role=menuitem>PNG</li><li role=menuitem>PDF</li>
</ul>
<input id=lab role=combobox aria-label=Lab style='position:absolute;left:40px;top:300px;width:200px'>
<ul id=labs role=listbox hidden style='left:40px;top:330px'></ul>
<select id=size aria-label=Size style='position:absolute;left:320px;top:300px'>
  <option value=s>Small</option><option value=m>Medium</option><option value=l>Large</option></select>
<ul id=long role=listbox hidden style='left:40px;top:430px;height:120px;overflow:auto'></ul>
<button id=city role=combobox aria-label=City style='position:absolute;left:40px;top:400px'>City</button>
<div id=out style='position:absolute;left:320px;top:400px'></div>
<script>
  const show = (el, on) => on ? el.removeAttribute('hidden') : el.setAttribute('hidden', '');
  const done = text => { out.textContent = text; document.querySelectorAll('[role=listbox],[role=menu]').forEach(l => show(l, false)); };
  fruit.onclick = () => show(fruits, true);
  fruits.onclick = e => { fruit.textContent = e.target.textContent; done('fruit ' + e.target.textContent); };
  actions.onclick = () => show(menu, true);
  menu.onclick = e => e.target === exportItem() ? show(sub, true) : done('menu ' + e.target.textContent);
  const exportItem = () => document.getElementById('export');
  sub.onclick = e => done('export ' + e.target.textContent);
  const LABS = ['Alpha Labs', 'Beta Works', 'Gamma Labs', 'Gamma Tech'];
  lab.oninput = () => { labs.innerHTML = LABS.filter(l => l.toLowerCase().includes(lab.value.toLowerCase()))
    .map(l => '<li role=option>' + l + '</li>').join(''); show(labs, true); };
  labs.onclick = e => { lab.value = e.target.textContent; done('lab ' + e.target.textContent); };
  for (let i = 1; i <= 30; i++) long.insertAdjacentHTML('beforeend', '<li role=option>City ' + i + '</li>');
  city.onclick = () => show(long, true);
  long.onclick = e => { city.textContent = e.target.textContent; done('city ' + e.target.textContent); };
</script></body>"""


@pytest.fixture
def actor(tmp_path):
    cfg = Config(project_dir=str(tmp_path), name="t", url="", width=800, height=600, scroll=False)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 800, "height": 600})
        pg.set_content(PAGE)
        a = Actor(None, pg, None, cfg)
        a.speed = 0.05
        a.render = False
        a.path = []
        move = a.move

        def record(x, y, *args, **kw):
            a.path.append((x, y))
            move(x, y, *args, **kw)
        a.move = record
        yield a
        b.close()


def entry(pg, role, name):
    return pg.get_by_role(role, name=name, exact=True).bounding_box()


def test_choose_reads_down_the_list_beside_the_text(actor):
    a, pg = actor, actor.pg
    a.choose(pg.get_by_role("combobox", name="Fruit"), "Elderberry")
    assert pg.locator("#out").text_content() == "fruit Elderberry"
    assert pg.locator("#fruit").text_content() == "Elderberry"
    # After the click on the control: Banana, Cherry, Date (the three above), then Elderberry.
    opened = pg.locator("#fruit").bounding_box()
    stops = [p for p in a.path if p[1] > opened["y"] + opened["height"]]
    assert len(stops) >= 4
    pg.evaluate("document.getElementById('fruits').removeAttribute('hidden')")  # open again to measure
    for name, (x, y) in zip(["Banana", "Cherry", "Date", "Elderberry"], stops[:4]):
        bb = entry(pg, "option", name)
        text_right = pg.get_by_role("option", name=name, exact=True).evaluate(
            "e => { const r = document.createRange(); r.selectNodeContents(e); return r.getBoundingClientRect().right; }")
        assert bb["y"] <= y + 6 <= bb["y"] + bb["height"], name  # on its line
        assert x > text_right, name  # right of the text, never on it
    pg.evaluate("document.getElementById('fruits').setAttribute('hidden', '')")
    # rest: the cursor ends beside the control, not on the closed list
    fruit = pg.locator("#fruit").bounding_box()
    assert a.my < fruit["y"] + fruit["height"] + 40


def test_choose_without_glide_goes_straight(actor):
    a, pg = actor, actor.pg
    a.choose(pg.get_by_role("combobox", name="Fruit"), "Fig", glide=0, rest=False)
    assert pg.locator("#out").text_content() == "fruit Fig"
    assert len(a.path) == 2  # to the control, to the option


def test_choose_through_a_submenu(actor):
    a, pg = actor, actor.pg
    a.choose(pg.get_by_role("button", name="Actions"), ["Export", "PDF"])
    assert pg.locator("#out").text_content() == "export PDF"


def test_choose_types_a_search_first(actor):
    a, pg = actor, actor.pg
    a.choose(pg.get_by_role("combobox", name="Lab"), "Gamma Tech", search="gam")
    assert pg.locator("#lab").input_value() == "Gamma Tech"
    assert pg.locator("#out").text_content() == "lab Gamma Tech"


def test_choose_on_a_native_select_sets_the_value(actor):
    a, pg = actor, actor.pg
    a.choose(pg.get_by_role("combobox", name="Size"), "Large", after=100)
    assert pg.locator("#size").input_value() == "l"
    box = pg.locator("#size").bounding_box()
    assert box["x"] <= a.path[0][0] <= box["x"] + box["width"]  # the click was shown


def test_choose_scrolls_a_long_list_to_the_option(actor):
    a, pg = actor, actor.pg
    a.choose(pg.get_by_role("combobox", name="City"), "City 25")
    assert pg.locator("#out").text_content() == "city City 25"
