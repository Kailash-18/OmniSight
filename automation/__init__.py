"""
Omnisight Automation Package.
Core browser automation, multi-viewport evidence capture, and VLM orchestration.
"""

__version__ = "0.1.0"

from automation.forensics import ForensicBundler, create_forensic_bundle

__all__ = ["ForensicBundler", "create_forensic_bundle"]
