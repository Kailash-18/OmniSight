"""
Patch Security Validator for OmniSight.
Enforces zero-trust guardrails on AI-generated patches to protect codebase integrity.
"""

import os
import re
from urllib.parse import unquote
from typing import Dict, Any, Optional
from app.core.config import settings

# Disallowed patterns that could signify malicious script injection or arbitrary code execution
DANGEROUS_PATTERNS = [
    r"<\s*script\b",
    r"javascript\s*:",
    r"expression\s*\(",
    r"data\s*:\s*text\/html",
    r"\bonerror\s*=",
    r"\bonload\s*=",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"\b__import__\b",
    r"\bimport\s+os\b",
    r"\bimport\s+subprocess\b",
    r"\bdocument\.cookie\b",
    r"\bwindow\.location\b",
    r"@import\b",
    r"behavior\s*:",
    r"-moz-binding\s*:",
]

ALLOWED_EXTENSIONS = {".css", ".jsx", ".js"}

WINDOWS_RESERVED_NAMES = {
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10))
}


def validate_css_safety(css_text: str) -> tuple[bool, Optional[str]]:
    """
    Validates that CSS content does not contain dangerous directives:
    Rejects @import (external exfiltration), behavior:, -moz-binding / -webkit-binding,
    expression(), and malicious url() schemes (javascript:, vbscript:, data:text/html).
    """
    if re.search(r"@import\b", css_text, re.IGNORECASE):
        return False, "Security violation: '@import' directives are forbidden in visual QA patches."
    if re.search(r"(?:-moz-|-ms-)?behavior\s*:", css_text, re.IGNORECASE):
        return False, "Security violation: 'behavior' property is forbidden in CSS patches."
    if re.search(r"-(?:moz|webkit)-binding\s*:", css_text, re.IGNORECASE):
        return False, "Security violation: binding properties are forbidden in CSS patches."
    if re.search(r"expression\s*\(", css_text, re.IGNORECASE):
        return False, "Security violation: CSS 'expression()' execution is forbidden in visual QA patches."
    if re.search(r"url\s*\(\s*['\"]?\s*(?:java\s*script|vb\s*script)\s*:", css_text, re.IGNORECASE):
        return False, "Security violation: 'javascript:' or 'vbscript:' URI schemes are forbidden in CSS patches."
    if re.search(r"url\s*\(\s*['\"]?\s*data:\s*text\/html", css_text, re.IGNORECASE):
        return False, "Security violation: 'data:text/html' URI schemes are forbidden in CSS patches."
    return True, None




def validate_css_syntax_balance(css_text: str) -> tuple[bool, Optional[str]]:
    """
    Validates structural CSS syntax integrity:
    1. Ensures curly braces '{' and '}' are strictly balanced and non-negative at all times.
    2. Ensures multi-line comment blocks '/*' have matching '*/' closures.
    """
    open_comments = css_text.count("/*")
    close_comments = css_text.count("*/")
    if open_comments != close_comments:
        return False, f"Syntax violation: Unbalanced CSS comments ({open_comments} open '/*', {close_comments} closed '*/')."

    # Strip comments before checking braces to avoid false positives inside comments
    clean_css = re.sub(r"/\*.*?\*/", "", css_text, flags=re.DOTALL)

    open_braces = 0
    for char in clean_css:
        if char == "{":
            open_braces += 1
        elif char == "}":
            open_braces -= 1
            if open_braces < 0:
                return False, "Syntax violation: Unmatched closing brace '}' without opening '{'."

    if open_braces != 0:
        return False, f"Syntax violation: Unbalanced CSS curly braces ({open_braces} unclosed '{{')."

    return True, None


def dry_run_patch(original_content: str, diff_text: str) -> tuple[bool, str, Optional[str]]:
    """
    Simulates applying a unified diff against an in-memory string buffer.
    Returns (success: bool, modified_content: str, error_message: Optional[str]).
    """
    if not diff_text or not diff_text.strip():
        return False, original_content, "Dry-run failed: Diff payload is empty."

    lines = original_content.splitlines()
    diff_lines = diff_text.replace("\r\n", "\n").splitlines()

    added_lines = [l[1:] for l in diff_lines if l.startswith("+") and not l.startswith("+++")]
    removed_lines = [l[1:] for l in diff_lines if l.startswith("-") and not l.startswith("---")]

    result_lines = []
    removed_set = set(removed_lines)
    for line in lines:
        if line in removed_set:
            removed_set.remove(line)
            continue
        result_lines.append(line)

    result_lines.extend(added_lines)
    modified = "\n".join(result_lines)
    return True, modified, None


def validate_patch(target_file: str, diff_content: str, file_content: Optional[str] = None) -> Dict[str, Any]:
    """
    Validates that a proposed patch strictly adheres to security boundaries:
    1. Rejects path traversal, null bytes, and absolute paths.
    2. Enforces allowed target files and approved extensions.
    3. Validates diff syntax and rejects empty or oversized diffs.
    4. Guards against script injection, shell payloads, and rogue execution in diff and file content.
    """
    if not target_file or not target_file.strip():
        return {
            "validation_status": False,
            "validator_errors": "Security violation: Target file path cannot be empty.",
            "target_file": target_file,
            "diff_sanitized": None
        }

    # Detect null bytes in target file, diff, or file content
    if "\x00" in target_file:
        return {
            "validation_status": False,
            "validator_errors": "Security violation: Null byte detected in target file path.",
            "target_file": target_file,
            "diff_sanitized": None
        }

    if diff_content and "\x00" in diff_content:
        return {
            "validation_status": False,
            "validator_errors": "Security violation: Null byte detected in patch diff payload.",
            "target_file": target_file,
            "diff_sanitized": None
        }

    if file_content and "\x00" in file_content:
        return {
            "validation_status": False,
            "validator_errors": "Security violation: Null byte detected in file content payload.",
            "target_file": target_file,
            "diff_sanitized": None
        }

    # URL-decode to prevent URL-encoded directory traversal (%2e%2e)
    decoded_path = unquote(target_file.strip())
    clean_path = decoded_path.replace("\\", "/")

    # Normalize benign leading relative prefix "./" and git diff prefixes "a/", "b/"
    while clean_path.startswith("./"):
        clean_path = clean_path[2:]
    if clean_path.startswith(("a/", "b/")):
        clean_path = clean_path[2:]

    # 1. Path traversal, UNC, & absolute path checks
    if clean_path.startswith("/") or clean_path.startswith("//") or re.match(r"^[a-zA-Z]:", clean_path):
        return {
            "validation_status": False,
            "validator_errors": "Security violation: Absolute file paths are rejected.",
            "target_file": clean_path,
            "diff_sanitized": None
        }

    path_segments = [seg for seg in clean_path.split("/") if seg]
    if any(seg == ".." or seg == "." for seg in path_segments):
        return {
            "validation_status": False,
            "validator_errors": "Security violation: Path traversal ('..') is strictly rejected.",
            "target_file": clean_path,
            "diff_sanitized": None
        }

    for seg in path_segments:
        stem = seg.split(".")[0].lower()
        if stem in WINDOWS_RESERVED_NAMES:
            return {
                "validation_status": False,
                "validator_errors": f"Security violation: Windows reserved device name '{seg}' detected in target path.",
                "target_file": clean_path,
                "diff_sanitized": None
            }

    # 2. Path allowlist check (Checked first so arbitrary directories are immediately rejected)
    if not settings.is_path_allowed(clean_path):
        return {
            "validation_status": False,
            "validator_errors": (
                f"Security violation: Target file '{clean_path}' is not in the approved allowlist. "
                f"Approved targets: {', '.join(settings.ALLOWED_PATCH_FILES)}."
            ),
            "target_file": clean_path,
            "diff_sanitized": None
        }


    # 3. File extension check
    _, ext = os.path.splitext(clean_path)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        return {
            "validation_status": False,
            "validator_errors": (
                f"Security violation: File extension '{ext}' is not permitted. "
                f"Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
            ),
            "target_file": clean_path,
            "diff_sanitized": None
        }

    # 4. Diff content validation
    if not diff_content or not diff_content.strip():
        return {
            "validation_status": False,
            "validator_errors": "Patch validation error: Provided patch diff is empty.",
            "target_file": clean_path,
            "diff_sanitized": None
        }

    normalized_diff = diff_content.replace("\r\n", "\n").replace("\r", "\n").strip()
    diff_lines = normalized_diff.splitlines()
    if len(diff_lines) > settings.MAX_DIFF_LINES:
        return {
            "validation_status": False,
            "validator_errors": (
                f"Patch validation error: Diff exceeds maximum allowed lines "
                f"({len(diff_lines)} > {settings.MAX_DIFF_LINES})."
            ),
            "target_file": clean_path,
            "diff_sanitized": None
        }

    diff_bytes = len(normalized_diff.encode("utf-8"))
    if diff_bytes > settings.MAX_DIFF_BYTES:
        return {
            "validation_status": False,
            "validator_errors": (
                f"Patch validation error: Diff exceeds maximum allowed payload size "
                f"({diff_bytes} > {settings.MAX_DIFF_BYTES} bytes)."
            ),
            "target_file": clean_path,
            "diff_sanitized": None
        }

    # 5. Injection and dangerous payload checks
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, normalized_diff, re.IGNORECASE):
            return {
                "validation_status": False,
                "validator_errors": (
                    f"Security violation: Potential script/code injection pattern detected: '{pattern}'"
                ),
                "target_file": clean_path,
                "diff_sanitized": None
            }
        if file_content and re.search(pattern, file_content, re.IGNORECASE):
            return {
                "validation_status": False,
                "validator_errors": (
                    f"Security violation: Malicious script injection pattern detected in file content: '{pattern}'"
                ),
                "target_file": clean_path,
                "diff_sanitized": None
            }

    # 6. Specific CSS guardrails
    if ext.lower() == ".css":
        css_valid, css_err = validate_css_safety(normalized_diff)
        if not css_valid:
            return {
                "validation_status": False,
                "validator_errors": css_err,
                "target_file": clean_path,
                "diff_sanitized": None
            }
        if file_content:
            css_valid, css_err = validate_css_safety(file_content)
            if not css_valid:
                return {
                    "validation_status": False,
                    "validator_errors": css_err,
                    "target_file": clean_path,
                    "diff_sanitized": None
                }

    # All security checks passed
    return {
        "validation_status": True,
        "validator_errors": None,
        "target_file": clean_path,
        "diff_sanitized": normalized_diff
    }


def assess_patch_risk(target_file: str, diff_content: str) -> Dict[str, Any]:
    """
    Assesses blast radius and risk score of an approved patch.
    Pure CSS style patches with small line footprints are eligible for auto-merge.
    JS/JSX patches or extensive diffs require mandatory human review.
    """
    clean_target = (target_file or "").replace("\\", "/").strip()
    _, ext = os.path.splitext(clean_target)
    lines = [l for l in (diff_content or "").splitlines() if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]
    line_count = len(lines)

    if ext.lower() == ".css" and line_count <= 40:
        risk_level = "low"
        auto_merge = True
        rationale = "Constrained CSS style modification with small blast radius."
    elif ext.lower() == ".css" and line_count <= 100:
        risk_level = "medium"
        auto_merge = False
        rationale = "CSS patch modifies significant number of layout rules; human QA recommended."
    else:
        risk_level = "high"
        auto_merge = False
        rationale = "Modifies executable application structure or contains large diff footprint."

    return {
        "risk_level": risk_level,
        "auto_merge_eligible": auto_merge,
        "modified_lines_count": line_count,
        "target_file": clean_target,
        "rationale": rationale
    }

