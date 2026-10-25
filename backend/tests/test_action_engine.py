"""
Unit Tests for Multimodal Action Engine and VLM Response Parser.
Verifies extraction of structured findings and executable code blocks from VLM output.
"""

from app.services.action_engine import action_engine
from app.schemas.run_schema import DefectCategory, Severity


def test_action_engine_pure_json():
    raw_vlm = """
{
  "findings": [
    {
      "id": "defect-checkout-clipped",
      "category": "element_clipping",
      "severity": "high",
      "description": "Place Order button overflows mobile viewport boundary",
      "viewport": "mobile_375x667",
      "target_element": "[data-testid='btn-place-order']",
      "confidence": 0.94,
      "suggested_change": "Change button width from 500px to 100% with box-sizing: border-box",
      "rationale": "Bounding box extends past viewport right boundary at 375px width"
    }
  ],
  "summary": "Detected critical mobile checkout button clipping defect",
  "proposed_patch": {
    "target_file": "app-under-test/src/styles/defects.css",
    "diff": "-.btn-order { width: 500px; }\n+.btn-order { width: 100%; box-sizing: border-box; }",
    "explanation": "Ensure button respects fluid mobile container"
  }
}
"""
    result = action_engine.parse_vlm_response(raw_vlm)
    assert result.is_valid is True
    assert len(result.findings) == 1
    f = result.findings[0]
    assert f.id == "defect-checkout-clipped"
    assert f.category == DefectCategory.ELEMENT_CLIPPING
    assert f.severity == Severity.HIGH
    assert f.confidence == 0.94
    assert result.proposed_patch is not None
    assert result.proposed_patch.target_file == "app-under-test/src/styles/defects.css"
    assert result.validation_status is True
    assert result.validator_errors is None


def test_action_engine_markdown_fenced_json():
    raw_vlm = """Here is my visual audit analysis of the checkout page:

```json
{
  "findings": [
    {
      "id": "defect-overlap-header",
      "category": "element_overlap",
      "severity": "medium",
      "description": "Heading overlaps with promo banner",
      "viewport": "desktop_1440x900",
      "confidence": 0.88,
      "suggested_change": "Add margin-top: 24px",
      "rationale": "Negative margin causes visual collision"
    }
  ],
  "summary": "Visual collision detected between promo and heading",
  "proposed_patch": {
    "target_file": "app-under-test/src/styles/defects.css",
    "diff": "-h1.header { margin-top: -20px; }\n+h1.header { margin-top: 24px; }",
    "explanation": "Remove negative margin"
  }
}
```

Please review the proposed diff before applying."""

    result = action_engine.parse_vlm_response(raw_vlm)
    assert result.is_valid is True
    assert len(result.findings) == 1
    assert result.findings[0].category == DefectCategory.ELEMENT_OVERLAP
    assert result.validation_status is True


def test_action_engine_code_block_extraction():
    text = """The VLM generated the following CSS patch:
```diff
--- a/app-under-test/src/styles/defects.css
+++ b/app-under-test/src/styles/defects.css
@@ -1,3 +1,3 @@
-.clipped { width: 500px; }
+.clipped { max-width: 100%; }
```
"""
    blocks = action_engine.extract_code_blocks(text)
    assert len(blocks) == 1
    assert blocks[0]["lang"] == "diff"
    assert ".clipped" in blocks[0]["code"]


def test_action_engine_confidence_normalization():
    raw_vlm = """
{
  "findings": [
    {
      "id": "defect-pct",
      "category": "element_clipping",
      "severity": "high",
      "description": "Percentage confidence test",
      "viewport": "all",
      "confidence": "95%",
      "suggested_change": "width: 100%",
      "rationale": "Test"
    },
    {
      "id": "defect-int",
      "category": "element_obstruction",
      "severity": "critical",
      "description": "Integer 90 confidence test",
      "viewport": "all",
      "confidence": 90,
      "suggested_change": "z-index: 10",
      "rationale": "Test"
    }
  ]
}
"""
    result = action_engine.parse_vlm_response(raw_vlm)
    assert result.is_valid is True
    assert len(result.findings) == 2
    assert result.findings[0].confidence == 0.95
    assert result.findings[1].confidence == 0.90


def test_action_engine_case_and_hyphen_normalization():
    raw_vlm = """
{
  "findings": [
    {
      "id": "defect-upper",
      "category": "ELEMENT_OVERLAP",
      "severity": "CRITICAL",
      "description": "Uppercase enums",
      "viewport": "mobile_375x667",
      "confidence": 0.85,
      "suggested_change": "margin: 0",
      "rationale": "Test"
    }
  ]
}
"""
    result = action_engine.parse_vlm_response(raw_vlm)
    assert result.is_valid is True
    assert result.findings[0].category == DefectCategory.ELEMENT_OVERLAP
    assert result.findings[0].severity == Severity.CRITICAL


def test_action_engine_top_level_array_json():
    raw_vlm = """[
  {
    "id": "defect-array-item",
    "category": "layout_overflow",
    "severity": "low",
    "description": "Direct list response from model",
    "viewport": "desktop_1440x900",
    "confidence": 0.80,
    "suggested_change": "overflow-x: hidden",
    "rationale": "Test"
  }
]"""
    result = action_engine.parse_vlm_response(raw_vlm)
    assert result.is_valid is True
    assert len(result.findings) == 1
    assert result.findings[0].id == "defect-array-item"
    assert result.findings[0].category == DefectCategory.LAYOUT_OVERFLOW


def test_action_engine_rejects_unapproved_target_file_in_patch():
    raw_vlm = """
{
  "findings": [],
  "proposed_patch": {
    "target_file": "backend/app/main.py",
    "diff": "+# bad edit",
    "explanation": "Malicious attempt to modify server code"
  }
}
"""
    result = action_engine.parse_vlm_response(raw_vlm)
    assert result.is_valid is True
    assert result.proposed_patch is not None
    assert result.validation_status is False
    assert "not in the approved allowlist" in result.validator_errors


def test_action_engine_handles_malformed_json_gracefully():
    malformed = "This is a corrupted response without valid JSON { findings: [ broken "
    result = action_engine.parse_vlm_response(malformed)
    assert result.is_valid is False
    assert len(result.findings) == 0
    assert result.validation_status is False
    assert len(result.parse_errors) > 0


def test_action_engine_empty_input():
    result = action_engine.parse_vlm_response("")
    assert result.is_valid is False
    assert "Empty" in result.validator_errors


def test_action_engine_multiple_diff_blocks_selects_first():
    """Verify code block extraction isolates multiple language blocks correctly."""
    text = """First diff:
```diff
-.first { display: none; }
+.first { display: block; }
```
Second diff:
```css
.second { color: red; }
```"""
    blocks = action_engine.extract_code_blocks(text)
    assert len(blocks) == 2
    assert blocks[0]["lang"] == "diff"
    assert blocks[1]["lang"] == "css"


def test_action_engine_single_quoted_python_dict_json():
    """Verify parser recovers from single-quoted Python dict representations from VLMs."""
    raw_vlm = """The model returned python dict format:
{'findings': [{'id': 'defect-single-quote', 'category': 'element_clipping', 'severity': 'high', 'description': 'Clipped CTA', 'viewport': 'mobile_375x667', 'confidence': 0.92, 'suggested_change': 'overflow: visible;'}]}"""
    result = action_engine.parse_vlm_response(raw_vlm)
    assert result.is_valid is True
    assert len(result.findings) == 1
    assert result.findings[0].id == "defect-single-quote"


def test_action_engine_smart_curly_quotes_normalization():
    """Verify parser normalizes smart/curly quotes (e.g. from rich text or LLM prose)."""
    raw_vlm = """Here is the audit:
{
  “findings”: [
    {
      “id”: “defect-smart-quote”,
      “category”: “element_overlap”,
      “severity”: “medium”,
      “description”: “Overlapping text elements”,
      “viewport”: “desktop_1440x900”,
      “confidence”: 0.88,
      “suggested_change”: “margin-top: 10px;”
    }
  ]
}"""
    result = action_engine.parse_vlm_response(raw_vlm)
    assert result.is_valid is True
    assert len(result.findings) == 1
    assert result.findings[0].id == "defect-smart-quote"


