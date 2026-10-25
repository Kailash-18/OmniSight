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


def validate_css_safety(css_text: str) -> tuple[bool, Optional[str]]:
    """
    Validates that CSS content does not contain dangerous directives:
    Rejects @import (external exfiltration), behavior:, -moz-binding,
    expression(), and malicious url() schemes (javascript:, data:text/html).
    """
    if re.search(r"@import\b", css_text, re.IGNORECASE):
        return False, "Security violation: '@import' directives are forbidden in visual QA patches."
    if re.search(r"behavior\s*:", css_text, re.IGNORECASE):
        return False, "Security violation: 'behavior' property is forbidden in CSS patches."
    if re.search(r"-moz-binding\s*:", css_text, re.IGNORECASE):
        return False, "Security violation: '-moz-binding' property is forbidden in CSS patches."
    if re.search(r"expression\s*\(", css_text, re.IGNORECASE):
        return False, "Security violation: CSS 'expression()' execution is forbidden in visual QA patches."
    if re.search(r"url\s*\(\s*['\"]?\s*javascript\s*:", css_text, re.IGNORECASE):
        return False, "Security violation: 'javascript:' URI schemes are forbidden in CSS patches."
    if re.search(r"url\s*\(\s*['\"]?\s*data:\s*text\/html", css_text, re.IGNORECASE):
        return False, "Security violation: 'data:text/html' URI schemes are forbidden in CSS patches."
    return True, None




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

    diff_lines = diff_content.strip().splitlines()
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

    diff_bytes = len(diff_content.encode("utf-8"))
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
        if re.search(pattern, diff_content, re.IGNORECASE):
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
        css_valid, css_err = validate_css_safety(diff_content)
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
        "diff_sanitized": diff_content.strip()
    }