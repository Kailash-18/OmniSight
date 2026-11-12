"""
Interaction check: clicks every visible button and link on each store page (desktop 1440x900)
and reports ones that are covered, lead to an error page, throw on click, or (possibly) do nothing.
Each element is tested from a freshly prepared page, so sequence-dependent bugs are out of scope.
"""

import logging
import re
import time
from typing import Callable, List, Optional, Tuple
from urllib.parse import urldefrag, urlparse

from playwright.sync_api import Page

from automation.core import STANDARD_VIEWPORTS, DefectCategory, Finding, Severity
from automation.engine import StoreJourney, UniversalWebJourney, create_journey, is_mock_store, create_isolated_page, launch_browser

logger = logging.getLogger("omnisight.automation.interaction")

CLICKABLE = "button, a[href], [role=button]"
SKIP_TEXT = re.compile(r"\b(pay|delete|remove|log ?out|sign ?out)\b", re.I)
MAX_PER_PAGE = 40
SETTLE_MS = 1500

COLLECT_JS = """(sel) => {
  const out = [];
  document.querySelectorAll(sel).forEach((el) => {
    const r = el.getBoundingClientRect(), s = getComputedStyle(el);
    if (!r.width || !r.height || s.visibility === 'hidden' || s.display === 'none') return;
    const disabled = el.hasAttribute('disabled') || el.getAttribute('aria-disabled') === 'true';
    el.setAttribute('data-omni-idx', String(out.length));
    out.push({ index: out.length, testid: el.getAttribute('data-testid'), tag: el.tagName.toLowerCase(),
      text: (el.innerText || el.getAttribute('aria-label') || '').trim().slice(0, 60),
      href: el.tagName === 'A' ? el.href : null, disabled: disabled });
  });
  return out;
}"""

# Hit-test with pointer-events forced on, so a visual overlay with pointer-events:none still counts as covering.
BLOCKER_JS = """(idx) => {
  const el = document.querySelector(`[data-omni-idx="${idx}"]`);
  if (!el) return null;
  el.scrollIntoView({ block: 'center', inline: 'center' });
  const r = el.getBoundingClientRect();
  const st = document.createElement('style');
  st.textContent = '* { pointer-events: auto !important; }';
  document.head.appendChild(st);
  const top = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  st.remove();
  if (!top || top === el || el.contains(top) || top.contains(el)) return null;
  const cls = typeof top.className === 'string' && top.className.trim() ? '.' + top.className.trim().split(/\\s+/)[0] : '';
  return top.getAttribute('data-testid') ? `[data-testid="${top.getAttribute('data-testid')}"]` : top.tagName.toLowerCase() + cls;
}"""

INVALID_FORM_JS = """(idx) => {
  const el = document.querySelector(`[data-omni-idx="${idx}"]`);
  return !!(el && el.form && el.type === 'submit' && !el.form.checkValidity());
}"""

OBSERVE_JS = """() => {
  window.__omniMut = 0;
  new MutationObserver((m) => { window.__omniMut += m.length; })
    .observe(document, { subtree: true, childList: true, attributes: true, characterData: true });
}"""


def _target(item: dict) -> str:
    return f'[data-testid="{item["testid"]}"]' if item["testid"] else f'{item["tag"]}:"{item["text"]}"'


def _finding(kind: DefectCategory, severity: Severity, page_name: str, viewport: str, item: dict,
             description: str, fix: str, rationale: str, confidence: float) -> Finding:
    return Finding(
        id=f"interaction-{page_name}-{kind.value}-{item['index']}",
        category=kind, severity=severity, description=description, viewport=viewport,
        target_element=_target(item), confidence=confidence, suggested_change=fix, rationale=rationale,
    )


def _click_and_watch(page: Page, item: dict, settle_ms: int = SETTLE_MS) -> Tuple[List[str], bool]:
    """Clicks one element; returns (errors seen, whether anything changed)."""
    errors: List[str] = []
    dialog = [False]

    def on_error(exc):
        errors.append(f"page error: {exc}")

    def on_console(msg):
        if msg.type == "error":
            errors.append(f"console error: {msg.text}")

    def on_failed(req):
        errors.append(f"request failed: {req.url}")

    def on_dialog(d):
        dialog[0] = True
        d.dismiss()

    handlers = {"pageerror": on_error, "console": on_console, "requestfailed": on_failed, "dialog": on_dialog}
    for event, fn in handlers.items():
        page.on(event, fn)
    try:
        before_url = page.url
        validation = page.evaluate(INVALID_FORM_JS, item["index"])
        page.evaluate(OBSERVE_JS)
        try:
            loc = page.locator(f'[data-omni-idx="{item["index"]}"]')
            try:
                loc.scroll_into_view_if_needed(timeout=1000)
                loc.click(timeout=3000)
            except Exception:
                # Resilient single retry after brief settling debounce for animated or hydrating controls
                page.wait_for_timeout(250)
                loc.click(timeout=2500)
        except Exception as e:
            errors.append(f"click failed: {str(e).splitlines()[0]}")
        page.wait_for_timeout(settle_ms)
        # A link to the page you're already on legitimately changes nothing.
        self_link = bool(item["href"]) and urldefrag(item["href"])[0] == urldefrag(before_url)[0]
        mutated = page.url != before_url or dialog[0] or validation or self_link
        if not mutated:
            try:
                mutated = (page.evaluate("() => window.__omniMut || 0") or 0) > 0
            except Exception:
                mutated = True  # navigated away mid-evaluate: something happened
        return errors, mutated
    finally:
        for event, fn in handlers.items():
            page.remove_listener(event, fn)


def check_page(page: Page, prepare: Callable[[Page], None], page_name: str, viewport_name: str,
               max_elements: int = MAX_PER_PAGE, settle_ms: int = SETTLE_MS,
               time_budget_s: Optional[float] = None) -> List[Finding]:
    started = time.monotonic()
    prepare(page)
    items = page.evaluate(COLLECT_JS, CLICKABLE)[:max_elements]
    origin = urlparse(page.url).netloc
    findings: List[Finding] = []
    needs_reset = False
    for item in items:
        if time_budget_s is not None and (time.monotonic() - started) >= time_budget_s:
            break
        label = item["text"] or item["testid"] or item["tag"]
        if SKIP_TEXT.search(label):
            continue
        href = item["href"]
        if href and urlparse(href).netloc and urlparse(href).netloc != origin:
            continue  # never follow links off the site under test (it is the only allowlisted host)
        if href and urlparse(href).scheme in ("http", "https") and urlparse(href).netloc == origin:
            try:
                status = page.request.get(href, timeout=3000).status
            except Exception:
                continue
            if status >= 400:
                findings.append(_finding(
                    DefectCategory.BROKEN_LINK, Severity.MEDIUM, page_name, viewport_name, item,
                    f"Link “{label}” on the {page_name} page leads to an error page (HTTP {status}).",
                    f"Fix or remove the link target {href}.", f"GET {href} returned {status}.", 0.95))
                continue
        if needs_reset:
            prepare(page)
            page.evaluate(COLLECT_JS, CLICKABLE)
        blocker = page.evaluate(BLOCKER_JS, item["index"])
        if blocker:
            findings.append(_finding(
                DefectCategory.ELEMENT_OBSTRUCTION, Severity.HIGH, page_name, viewport_name, item,
                f"“{label}” on the {page_name} page is covered by {blocker}.",
                f"Stop {blocker} from overlapping “{label}” (positioning/z-index).",
                f"The topmost element at the centre of “{label}” is {blocker}.", 0.9))
            continue
        needs_reset = True
        errors, changed = _click_and_watch(page, item, settle_ms=settle_ms)
        if errors:
            findings.append(_finding(
                DefectCategory.CLICK_ERROR, Severity.HIGH, page_name, viewport_name, item,
                f"Clicking “{label}” on the {page_name} page causes an error.",
                "Fix the click handler so it completes without errors.", "; ".join(errors[:3]), 0.9))
        elif not changed and not item.get("disabled"):
            findings.append(_finding(
                DefectCategory.NO_EFFECT, Severity.LOW, page_name, viewport_name, item,
                f"“{label}” on the {page_name} page possibly does nothing when clicked.",
                "Check that this control has a working action, or remove it.",
                f"No URL change, DOM change, or dialog within {settle_ms} ms of the click.", 0.5))
    return findings


def store_pages(base_url: str) -> List[Tuple[str, Callable[[Page], None]]]:
    if is_mock_store(base_url):
        def home(p: Page) -> None:
            StoreJourney(p, base_url).navigate_home()

        def cart(p: Page) -> None:
            j = StoreJourney(p, base_url)
            j.navigate_home()
            j.add_product_to_cart("mug")
            j.navigate_to_cart()

        def checkout(p: Page) -> None:
            cart(p)
            StoreJourney(p, base_url).continue_to_checkout()

        return [("home", home), ("cart", cart), ("checkout", checkout)]
    else:
        def home_generic(p: Page) -> None:
            p.goto(base_url, wait_until="domcontentloaded", timeout=15000)
            try:
                p.wait_for_load_state("load", timeout=1500)
            except Exception:
                pass

        return [("home", home_generic)]


def run_interaction_check(app_url: str, pages: Optional[List[Tuple[str, Callable[[Page], None]]]] = None,
                          viewport_name: str = "desktop_1440x900") -> List[Finding]:
    findings: List[Finding] = []
    external = pages is None and not is_mock_store(app_url)
    check_kwargs = {"max_elements": 6, "settle_ms": 500, "time_budget_s": 15.0} if external else {}
    with launch_browser() as browser:
        with create_isolated_page(browser, STANDARD_VIEWPORTS[viewport_name]) as page:
            for name, prepare in pages or store_pages(app_url):
                try:
                    findings.extend(check_page(page, prepare, name, viewport_name, **check_kwargs))
                except Exception as e:
                    logger.warning("Interaction check skipped %s page: %s", name, e)
    return findings
