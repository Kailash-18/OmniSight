ALLOWED_FILES = [
    "app-under-test/src/App.css",
    "app-under-test/src/components/"
]

def validate_patch(target_file: str, diff_content: str) -> dict:
    if ".." in target_file or target_file.startswith("/"):
        return {
            "validation_status": False,
            "validator_errors": "Security violation: Path traversal or absolute path rejected."
        }

    is_allowed = any(target_file.startswith(allowed) for allowed in ALLOWED_FILES)
    if not is_allowed:
        return {
            "validation_status": False,
            "validator_errors": f"Error: File '{target_file}' is not in the approved allowlist."
        }

    if not diff_content or len(diff_content.strip()) == 0:
        return {
            "validation_status": False,
            "validator_errors": "Error: Provided patch diff is empty."
        }

    return {
        "validation_status": True,
        "validator_errors": None
    }