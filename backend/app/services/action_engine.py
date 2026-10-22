"""
Action Engine for OmniSight.
Parses natural language and multimodal responses from VLMs, isolates structured findings
and executable code blocks, and validates patches against strict security guardrails.
"""

import json
import re
from typing import Dict, Any, List, Optional, Tuple
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
        Returns a list of dicts with 'lang' and 'code'.
        """
        pattern = r"```([a-zA-Z0-9_\-\+]*)\s*\n(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL)
        blocks = []
        for lang, code in matches:
            blocks.append({
                "lang": lang.strip().lower(),
                "code": code.strip()
            })
        return blocks

    @classmethod
    def extract_json_object(cls, text: str) -> Tuple[Optional[Dict[str, Any]], List[str]]:
        """
        Robustly extracts the primary JSON object from raw VLM output.
        Handles pure JSON, markdown fenced JSON, and JSON surrounded by natural language.
        Uses strict=False to tolerate literal control characters / unescaped newlines in diff strings.
        """
        errors = []
        cleaned_text = text.strip()

        # Strategy 1: Check for ```json ... ``` or generic ``` ... ``` markdown block
        code_blocks = cls.extract_code_blocks(cleaned_text)
        for block in code_blocks:
            if block["lang"] in ("json", ""):
                try:
                    data = json.loads(block["code"], strict=False)
                    if isinstance(data, dict):
                        return data, errors
                except json.JSONDecodeError:
                    continue

        # Strategy 2: Direct JSON parse
        try:
            data = json.loads(cleaned_text, strict=False)
            if isinstance(data, dict):
                return data, errors
        except json.JSONDecodeError:
            pass

        # Strategy 3: Find outermost balanced curly braces in prose
        start_idx = cleaned_text.find("{")
        end_idx = cleaned_text.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            candidate = cleaned_text[start_idx:end_idx + 1]
            try:
                data = json.loads(candidate, strict=False)
                if isinstance(data, dict):
                    return data, errors
            except json.JSONDecodeError as e:
                # Attempt light sanitization (remove trailing commas before closing brackets)
                sanitized = re.sub(r",\s*([\]}])", r"\1", candidate)
                try:
                    data = json.loads(sanitized, strict=False)
                    if isinstance(data, dict):
                        return data, errors
                except json.JSONDecodeError:
                    errors.append(f"Failed to decode embedded JSON structure: {str(e)}")

        errors.append("No valid JSON structure could be isolated from model response.")
        return None, errors

    @classmethod
    def parse_vlm_response(cls, raw_vlm_output: str) -> VLMParseResponse:
        """
        Full extraction and validation pipeline:
        1. Isolates JSON data from natural language.
        2. Validates structured findings and normalizes categories/severities.
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

        if not data:
            return VLMParseResponse(
                is_valid=False,
                findings=[],
                summary=None,
                proposed_patch=None,
                validation_status=False,
                validator_errors="Unable to parse JSON from VLM response.",
                parse_errors=parse_errors
            )

        # 1. Parse findings
        raw_findings = data.get("findings", [])
        parsed_findings: List[FindingSchema] = []
        for idx, item in enumerate(raw_findings):
            if not isinstance(item, dict):
                parse_errors.append(f"Finding at index {idx} is not an object.")
                continue

            # Normalize category fallback
            cat_val = item.get("category", "element_overlap")
            try:
                category = DefectCategory(cat_val)
            except ValueError:
                category = DefectCategory.ELEMENT_OVERLAP
                parse_errors.append(f"Finding {item.get('id')}: unknown category '{cat_val}', defaulted to element_overlap.")

            # Normalize severity fallback
            sev_val = item.get("severity", "medium")
            try:
                severity = Severity(sev_val)
            except ValueError:
                severity = Severity.MEDIUM
                parse_errors.append(f"Finding {item.get('id')}: unknown severity '{sev_val}', defaulted to medium.")

            try:
                finding = FindingSchema(
                    id=str(item.get("id", f"defect-{idx+1}")),
                    category=category,
                    severity=severity,
                    description=str(item.get("description", "Unspecified visual defect")),
                    viewport=str(item.get("viewport", "all")),
                    target_element=item.get("target_element"),
                    confidence=float(item.get("confidence", 0.8)),
                    suggested_change=str(item.get("suggested_change", "")),
                    rationale=str(item.get("rationale", "")),
                    status=str(item.get("status", "detected"))
                )
                parsed_findings.append(finding)
            except Exception as e:
                parse_errors.append(f"Failed to validate finding schema at index {idx}: {str(e)}")

        summary = data.get("summary")

        # 2. Extract proposed patch
        proposed_patch_data = data.get("proposed_patch")
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
                target_file = data.get("target_file", "app-under-test/src/styles/defects.css")
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
