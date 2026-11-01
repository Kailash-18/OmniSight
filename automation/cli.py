"""
OmniSight Automation CLI Entrypoint.
Enables one-command execution of browser navigation, evidence collection, and visual audit.
"""

import sys
from automation.orchestrator import main

__all__ = ["main"]

if __name__ == "__main__":
    sys.exit(main())
