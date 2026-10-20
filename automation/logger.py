"""
Console and Network Error Logger.
Attaches runtime listeners to Playwright pages to collect error diagnostics.
"""

from typing import List, Dict, Any
from playwright.sync_api import Page, ConsoleMessage, Request
from automation.evidence import EvidenceCollector


def attach_browser_listeners(page: Page, evidence: EvidenceCollector) -> None:
    """
    Hooks page console messages, uncaught exceptions, and network request failures
    into the evidence collection stream.
    """
    def on_console(msg: ConsoleMessage):
        if msg.type in ("error", "warning"):
            evidence.record_console_log(
                level=msg.type,
                message=msg.text,
                url=page.url
            )

    def on_page_error(exc):
        evidence.record_console_log(
            level="uncaught_exception",
            message=str(exc),
            url=page.url
        )

    def on_request_failed(request: Request):
        failure = request.failure
        evidence.record_console_log(
            level="request_failed",
            message=f"{request.method} {request.url} failed: {failure}",
            url=page.url
        )

    page.on("console", on_console)
    page.on("pageerror", on_page_error)
    page.on("requestfailed", on_request_failed)
