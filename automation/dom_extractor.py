"""
DOM Context Extractor and Element Snapshot Logic.
Extracts structural and spatial coordinates of key elements to accompany screenshots.
"""

from typing import Dict, Any, List
from playwright.sync_api import Page


def extract_dom_context(page: Page) -> Dict[str, Any]:
    """
    Evaluates key interactive and visual elements in the current page,
    returning structured geometry and semantic identifiers.
    """
    script = """
    () => {
        const elements = [];
        const targets = document.querySelectorAll(
            '[data-testid], h1, h2, h3, button, a, form, input, textarea, .promo-banner, .hero-title, .cart-summary'
        );

        targets.forEach((el) => {
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            
            // Only capture elements with non-zero dimensions
            if (rect.width > 0 || rect.height > 0) {
                elements.push({
                    tag: el.tagName.toLowerCase(),
                    test_id: el.getAttribute('data-testid') || null,
                    classes: Array.from(el.classList),
                    text: (el.innerText || el.textContent || '').trim().slice(0, 100),
                    box: {
                        x: Math.round(rect.x),
                        y: Math.round(rect.y),
                        width: Math.round(rect.width),
                        height: Math.round(rect.height)
                    },
                    computed: {
                        display: style.display,
                        position: style.position,
                        zIndex: style.zIndex,
                        overflow: style.overflow,
                        visibility: style.visibility,
                        pointerEvents: style.pointerEvents
                    }
                });
            }
        });

        return {
            url: window.location.href,
            viewport: {
                width: window.innerWidth,
                height: window.innerHeight
            },
            element_count: elements.length,
            elements: elements
        };
    }
    """
    try:
        return page.evaluate(script)
    except Exception as e:
        return {
            "url": page.url,
            "error": f"Failed to extract DOM context: {str(e)}",
            "elements": []
        }
