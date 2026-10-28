# -*- coding: utf-8 -*-
"""
Action Engine for OmniSight.
Parses natural language and multimodal responses from VLMs, isolates structured findings
and executable code blocks, and validates patches against strict security guardrails.
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

_backend_root = str(Path(__file__).resolve().parent.parent.parent)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from app.schemas.run_schema import (
    FindingSchema,
    PatchObject,
    VLMParseResponse,
    DefectCategory,
    Severity,
)
from app.services.patch_validator import validate_patch


class ActionEngine:
    """Action Engine for extracting, parsing, and verifying VLM visual defect audits."""

    @staticmethod
    def extract_code_blocks(text: str) -> List[Dict[str, str]]:
        """
        Extracts all markdown-fenced code blocks from prose text.
        Supports both backtick (```) and tilde (~~~) fences with LF or CRLF endings.
        Returns a list of dicts with 'lang' (lowercase) and 'code'.
        """
        pattern = r"(?:```|~~~)([a-zA-Z0-9_\-\+]*)[^\S\r\n]*(?:\r?\n)(.*?)(?:```|~~~)"
        matches = re.findall(pattern, text, re.DOTALL)
        blocks = []
        for lang, code in matches:
            blocks.append({
                "lang": lang.strip().lower(),
                "code": code.strip()
            })
        return blocks

    @staticmethod
    def _normalize_confidence(val: Any) -> float:
        """Normalizes confidence values (e.g. 0.95, '0.95', 95, '95%') to a float between 0.0 and 1.0."""
        try:
            if isinstance(val, str):
                cleaned = val.strip().rstrip("%")
                f = float(cleaned)
            else:
                f = float(val)
            if f > 1.0:
                f = f / 100.0
            return max(0.0, min(1.0, f))
        except (ValueError, TypeError):
            return 0.8

    CATEGORY_SYNONYMS = {
        "overlap": DefectCategory.ELEMENT_OVERLAP,
        "clipping": DefectCategory.ELEMENT_CLIPPING,
        "clipped": DefectCategory.ELEMENT_CLIPPING,
        "clip": DefectCategory.ELEMENT_CLIPPING,
        "obstruction": DefectCategory.ELEMENT_OBSTRUCTION,
        "obstructed": DefectCategory.ELEMENT_OBSTRUCTION,
        "contrast": DefectCategory.CONTRAST_ISSUE,
        "contrast_issue": DefectCategory.CONTRAST_ISSUE,
        "color_contrast": DefectCategory.CONTRAST_ISSUE,
        "overflow": DefectCategory.LAYOUT_OVERFLOW,
        "layout_overflow": DefectCategory.LAYOUT_OVERFLOW,
    }

    SEVERITY_SYNONYMS = {
        "crit": Severity.CRITICAL,
        "critical": Severity.CRITICAL,
        "blocker": Severity.CRITICAL,
        "high": Severity.HIGH,
        "major": Severity.HIGH,
        "med": Severity.MEDIUM,
        "medium": Severity.MEDIUM,
        "normal": Severity.MEDIUM,
        "low": Severity.LOW,
        "minor": Severity.LOW,
        "trivial": Severity.LOW,
    }

    @classmethod
    def _normalize_category(cls, cat_val: Any) -> Tuple[DefectCategory, Optional[str]]:
        """Normalizes defect categories handling case, hyphens, and common VLM synonyms."""
        warning = None
        s = str(cat_val).strip().lower().replace("-", "_")
        if s in cls.CATEGORY_SYNONYMS:
            return cls.CATEGORY_SYNONYMS[s], warning
        try:
            return DefectCategory(s), warning
        except ValueError:
            return DefectCategory.ELEMENT_OVERLAP, f"Unknown category '{cat_val}', normalized to element_overlap."

    @classmethod
    def _normalize_severity(cls, sev_val: Any) -> Tuple[Severity, Optional[str]]:
        """Normalizes severity strings handling case, level codes, and common VLM synonyms."""
        warning = None
        s = str(sev_val).strip().lower()
        if s in cls.SEVERITY_SYNONYMS:
            return cls.SEVERITY_SYNONYMS[s], warning
        try:
            return Severity(s), warning
        except ValueError:
            return Severity.MEDIUM, f"Unknown severity '{sev_val}', normalized to medium."

    @classmethod
    def extract_json_object(cls, text: str) -> Tuple[Optional[Any], List[str]]:
        """
        Robustly extracts the primary JSON object or list from raw VLM output.
        Handles pure JSON, markdown fenced JSON, single-quoted dicts, and smart quotes.
        Uses strict=False to tolerate literal control characters in diff strings.
        """
        import ast
        errors = []
        # Normalize Unicode smart/curly quotes to standard ASCII quotes
        cleaned_text = (
            text.strip()
            .replace("“", '"')
            .replace("”", '"')
            .replace("‘", "'")
            .replace("’", "'")
        )

        # Strategy 1: Check for ```json ... ``` or generic ``` ... ``` markdown block
        code_blocks = cls.extract_code_blocks(cleaned_text)
        for block in code_blocks:
            if block["lang"] in ("json", ""):
                try:
                    data = json.loads(block["code"], strict=False)
                    if isinstance(data, (dict, list)):
                        return data, errors
                except json.JSONDecodeError:
                    # Try single-quoted python literal fallback
                    try:
                        data = ast.literal_eval(block["code"])
                        if isinstance(data, (dict, list)):
                            return data, errors
                    except Exception:
                        continue

        # Strategy 2: Direct JSON parse
        try:
            data = json.loads(cleaned_text, strict=False)
            if isinstance(data, (dict, list)):
                return data, errors
        except json.JSONDecodeError:
            pass

        # Strategy 3: Find outermost balanced curly braces or brackets in prose
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            start_idx = cleaned_text.find(start_char)
            end_idx = cleaned_text.rfind(end_char)
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                candidate = cleaned_text[start_idx:end_idx + 1]
                try:
                    data = json.loads(candidate, strict=False)
                    if isinstance(data, (dict, list)):
                        return data, errors
                except json.JSONDecodeError:
                    # Attempt light sanitization (remove trailing commas before closing brackets)
                    sanitized = re.sub(r",\s*([\]}])", r"\1", candidate)
                    try:
                        data = json.loads(sanitized, strict=False)
                        if isinstance(data, (dict, list)):
                            return data, errors
                    except json.JSONDecodeError:
                        # Strategy 4: Try ast.literal_eval on candidate for single-quoted structures
                        try:
                            data = ast.literal_eval(candidate)
                            if isinstance(data, (dict, list)):
                                return data, errors
                        except Exception as err:
                            errors.append(f"Failed to decode embedded JSON structure: {str(err)}")

        errors.append("No valid JSON structure could be isolated from model response.")
        return None, errors

    @classmethod
    def parse_vlm_response(cls, raw_vlm_output: str) -> VLMParseResponse:
        """
        Full extraction and validation pipeline:
        1. Isolates JSON data from natural language (supports objects and top-level lists).
        2. Validates structured findings and normalizes categories/severities/confidence.
        3. Extracts the proposed patch and unified diff.
        4. Validates the patch using security allowlists and injection filters.
        """
        if not raw_vlm_output or not raw_vlm_output.strip():
            return VLMParseResponse(
                is_valid=False,
                findings=[],
                summary=None,
                proposed_patch=None,
                validation_status=False,
                validator_errors="Empty VLM output received.",
                parse_errors=["Empty response text."]
            )

        data, parse_errors = cls.extract_json_object(raw_vlm_output)

        if data is None:
            return VLMParseResponse(
                is_valid=False,
                findings=[],
                summary=None,
                proposed_patch=None,
                validation_status=False,
                validator_errors="Unable to parse JSON from VLM response.",
                parse_errors=parse_errors
            )

        # Support both {"findings": [...]} and top-level [...] list format
        if isinstance(data, list):
            raw_findings = data
            summary = "Audit report containing list of findings"
            proposed_patch_data = None
        else:
            raw_findings = data.get("findings", [])
            summary = data.get("summary")
            proposed_patch_data = data.get("proposed_patch")

        # 1. Parse findings
        parsed_findings: List[FindingSchema] = []
        for idx, item in enumerate(raw_findings):
            if not isinstance(item, dict):
                parse_errors.append(f"Finding at index {idx} is not an object.")
                continue

            category, cat_warn = cls._normalize_category(item.get("category", "element_overlap"))
            if cat_warn:
                parse_errors.append(f"Finding {item.get('id', idx)}: {cat_warn}")

            severity, sev_warn = cls._normalize_severity(item.get("severity", "medium"))
            if sev_warn:
                parse_errors.append(f"Finding {item.get('id', idx)}: {sev_warn}")

            confidence = cls._normalize_confidence(item.get("confidence", 0.8))

            fp = item.get("fingerprint")
            if not fp:
                try:
                    from app.services.fingerprint_service import generate_defect_fingerprint
                    fp = generate_defect_fingerprint(
                        category=category,
                        target_element=item.get("target_element"),
                        viewport=str(item.get("viewport", "all")),
                        suggested_change=str(item.get("suggested_change", ""))
                    )
                except Exception:
                    fp = None

            try:
                finding = FindingSchema(
                    id=str(item.get("id", f"defect-{idx+1}")),
                    category=category,
                    severity=severity,
                    description=str(item.get("description", "Unspecified visual defect")),
                    viewport=str(item.get("viewport", "all")),
                    target_element=item.get("target_element"),
                    confidence=confidence,
                    suggested_change=str(item.get("suggested_change", "")),
                    rationale=str(item.get("rationale", "")),
                    status=str(item.get("status", "detected")),
                    fingerprint=fp
                )
                parsed_findings.append(finding)
            except Exception as e:
                parse_errors.append(f"Failed to validate finding schema at index {idx}: {str(e)}")

        # 2. Extract proposed patch
        proposed_patch: Optional[PatchObject] = None

        if isinstance(proposed_patch_data, dict):
            target_file = proposed_patch_data.get("target_file", "").strip()
            diff_text = proposed_patch_data.get("diff", "").strip()
            explanation = proposed_patch_data.get("explanation")

            proposed_patch = PatchObject(
                target_file=target_file,
                diff=diff_text,
                explanation=explanation
            )
        else:
            # Check if there is an isolated diff code block in the outer prose
            code_blocks = cls.extract_code_blocks(raw_vlm_output)
            diff_blocks = [b["code"] for b in code_blocks if b["lang"] in ("diff", "patch", "css")]
            if diff_blocks:
                target_file = (data.get("target_file") if isinstance(data, dict) else None) or "app-under-test/src/styles/defects.css"
                proposed_patch = PatchObject(
                    target_file=target_file,
                    diff=diff_blocks[0],
                    explanation="Isolated code block extracted from VLM response"
                )

        # 3. Validate patch security if a proposed patch was extracted
        validation_status = False
        validator_errors = None

        if proposed_patch:
            val_result = validate_patch(proposed_patch.target_file, proposed_patch.diff)
            validation_status = val_result["validation_status"]
            validator_errors = val_result["validator_errors"]
            proposed_patch.target_file = val_result.get("target_file", proposed_patch.target_file)
            proposed_patch.validation_status = validation_status
            proposed_patch.validator_errors = validator_errors
        else:
            validator_errors = "No proposed patch provided in VLM response."

        return VLMParseResponse(
            is_valid=True,
            findings=parsed_findings,
            summary=summary,
            proposed_patch=proposed_patch,
            validation_status=validation_status,
            validator_errors=validator_errors,
            parse_errors=parse_errors
        )


action_engine = ActionEngine()
