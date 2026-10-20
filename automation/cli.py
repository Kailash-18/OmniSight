"""
OmniSight Automation CLI Entrypoint.
Enables one-command execution of browser navigation, evidence collection, and visual audit.
"""

import sys
import json
import argparse
from typing import List
from automation.config import config
from automation.orchestrator import Orchestrator
from automation.vlm_adapter import MockVLMAdapter
from automation.vlm_client import LiveVLMAdapter


def main() -> int:
    parser = argparse.ArgumentParser(
        description="OmniSight Browser Automation & Visual QA Runner"
    )
    parser.add_argument(
        "--target",
        type=str,
        default=config.app_url,
        help="Target web app URL (default: http://localhost:5173)",
    )
    parser.add_argument(
        "--viewports",
        nargs="+",
        default=None,
        help="Specific viewports to run (e.g., desktop_1440x900 mobile_375x667)",
    )
    parser.add_argument(
        "--use-live-vlm",
        action="store_true",
        help="Call live multimodal VLM API instead of deterministic mock adapter",
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Print final output strictly in JSON format",
    )

    args = parser.parse_args()

    vlm = LiveVLMAdapter() if args.use_live_vlm else MockVLMAdapter()
    orchestrator = Orchestrator(vlm_adapter=vlm)

    if not args.json_output:
        print("=" * 60)
        print("  OmniSight Autonomous Visual QA & RPA Agent")
        print("=" * 60)
        print(f"Target URL: {args.target}")
        print(f"Engine:     Playwright Chromium (Headless: {config.headless})")
        print(f"VLM:        {'Live Multimodal API' if args.use_live_vlm else 'Deterministic Mock'}")
        print("-" * 60)
        print("Starting e-commerce journey and evidence capture...")

    result = orchestrator.run_full_remediation_loop(
        target_url=args.target,
        viewports=args.viewports,
    )

    if args.json_output:
        print(json.dumps(result, indent=2))
    else:
        status = result.get("status", "unknown")
        print("-" * 60)
        print(f"Run Completed: {result.get('run_id')}")
        print(f"Final Status:  {status.upper()}")
        print(f"Screenshots:   {result.get('screenshots_count', 0)} files saved")
        findings = result.get("findings", [])
        print(f"Defects Found: {len(findings)}")

        for idx, f in enumerate(findings, 1):
            print(f"  [{idx}] {f['category'].upper()} ({f['severity'].upper()}): {f['description']}")
            print(f"      Target: {f.get('target_element')} | Viewport: {f['viewport']}")
            print(f"      Fix:    {f['suggested_change']}")

        if result.get("artifacts_dir"):
            print(f"\nArtifacts stored in: {result['artifacts_dir']}")
        print("=" * 60)

    return 0 if result.get("status") in ("fixed", "audited") else 1


if __name__ == "__main__":
    sys.exit(main())
