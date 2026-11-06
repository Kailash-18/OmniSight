import functools
import http.server
import threading

import pytest

from automation.core import DefectCategory
from automation.interaction_check import run_interaction_check

PAGE = """<!doctype html><html><body>
<button data-testid="ok" onclick="document.body.dataset.clicked='1'">Works</button>
<button data-testid="dead">Dead</button>
<button data-testid="boom" onclick="throw new Error('boom')">Boom</button>
<a data-testid="broken" href="/missing-page">Missing</a>
<div style="position:relative;width:200px;height:40px">
  <button data-testid="covered" style="width:200px;height:40px">Covered</button>
  <div data-testid="overlay" style="position:absolute;inset:0;background:#c00;pointer-events:none"></div>
</div>
<button data-testid="remove">Remove item</button>
<a data-testid="self" href="/">Home</a>
<a data-testid="external" href="https://example.com/">Elsewhere</a>
<form><input required name="q"><button data-testid="submit">Search</button></form>
</body></html>"""


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture
def site(tmp_path):
    (tmp_path / "index.html").write_text(PAGE)
    handler = functools.partial(QuietHandler, directory=str(tmp_path))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/"
    server.shutdown()


def test_finds_each_problem_and_nothing_else(site):
    visited = []

    def prepare(p):
        p.on("request", lambda r: visited.append(r.url))
        p.goto(site, wait_until="load")

    findings = run_interaction_check(site, pages=[("home", prepare)])
    assert not any("example.com" in u for u in visited)  # never leaves the allowed site
    by_target = {f.target_element: f.category for f in findings}
    assert by_target['[data-testid="dead"]'] == DefectCategory.NO_EFFECT
    assert by_target['[data-testid="boom"]'] == DefectCategory.CLICK_ERROR
    assert by_target['[data-testid="broken"]'] == DefectCategory.BROKEN_LINK
    assert by_target['[data-testid="covered"]'] == DefectCategory.ELEMENT_OBSTRUCTION
    assert '[data-testid="ok"]' not in by_target           # working button
    assert '[data-testid="remove"]' not in by_target       # skipped by safety list
    assert '[data-testid="external"]' not in by_target     # links to other sites are not clicked
    assert '[data-testid="self"]' not in by_target         # link to the current page is not dead
    assert '[data-testid="submit"]' not in by_target       # blocked by form validation = an effect
    assert all(f.viewport == "desktop_1440x900" and f.id.startswith("interaction-home-") for f in findings)
